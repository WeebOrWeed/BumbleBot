# backend_server.py
import os
from flask import Flask, request, jsonify, g
from flask_cors import CORS
import stripe
# import sqlite3
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError # Import for handling unique constraint errors
from sqlalchemy import func
import datetime

# --- Configuration (Centralized Backend) ---
# IMPORTANT: Never hardcode sensitive keys in production.
# Use environment variables for STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, etc.
# For local testing, you can put them here, but for App Engine, configure them
# in app.yaml or as environment variables.
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "pk_test_51RR6ziQYrsgIyvPmELFVZyFR1d8EJr37NZlCnmotzF8kDzXk6bJGkViqnVuCrW3DYqIqGMGtGtNrZ7EsbRJ29yI700hrqlYa8D")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "sk_test_51RR6ziQYrsgIyvPmGwjgq833pM7cc0dCEH758hw0juZR7ShHvhEXG89UTM5rVmwHwgdmhCJrd6AWTMeXQRCzEnPY005YxTuERR")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "whsec_5fPmmhyob86yXWRnjO8CFzijB9Njsacm") # From Stripe Dashboard webhook settings
STRIPE_PREMIUM_PRICE_ID = os.environ.get("STRIPE_PREMIUM_PRICE_ID", "price_1RR74UQYrsgIyvPmAshepzTl")
BASE_URL = 'https://bumblebot-460521.uc.r.appspot.com/'

stripe.api_key = STRIPE_SECRET_KEY

app = Flask(__name__)
CORS(app) # Enable CORS for all routes (important for your Tkinter app to communicate)
db = SQLAlchemy()

# Configuration for Cloud SQL
# On App Engine, this will use the Unix socket or TCP depending on connection type
# For local testing, you might use 'localhost' or a Cloud SQL Proxy.

# Connection string for App Engine Standard using Unix socket
# This is recommended for faster/more secure connections on GAE
db_user = os.environ.get("DB_USER")
db_password = os.environ.get("DB_PASSWORD")
db_name = os.environ.get("DB_NAME")
cloud_sql_connection_name = os.environ.get("CLOUD_SQL_CONNECTION_NAME") # e.g. 'your-project-id:your-region:your-instance-id'

if os.environ.get('GAE_APPLICATION'): # Check if running on App Engine
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f"postgresql+psycopg2://{db_user}:{db_password}@/{db_name}?"
        f"host=/cloudsql/{cloud_sql_connection_name}"
    )
else: # Local development
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f"postgresql+psycopg2://{db_user}:{db_password}@localhost:5432/{db_name}"
    )

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
with app.app_context():
    print("Attempting to create database tables...")
    try:
        db.create_all() # This creates all tables defined by your SQLAlchemy models
        print("Database tables checked/created SUCCESSFULLY.")
    except Exception as e:
        print(f"ERROR: Failed to create database tables: {e}")

    
# Define your User model
class User(db.Model):
    __tablename__ = 'users'
    google_user_id = db.Column(db.String(255), primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    is_subscribed = db.Column(db.Boolean, default=False)
    stripe_customer_id = db.Column(db.String(255))
    stripe_subscription_id = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=func.now(), nullable=False)
    
# --- API Endpoints for Tkinter App ---

@app.route('/')
def health_check():
    return "Backend is running!"

@app.route('/users/register_or_get_status', methods=['POST'])
def register_or_get_user_status():
    data = request.json
    google_user_id = data.get('google_user_id')
    email = data.get('user_email')

    if not google_user_id or not email:
        return jsonify({"error": "Missing user_id or email"}), 400

    user = User.query.filter_by(google_user_id=google_user_id).first()
    
    if user:
        # User exists, return their current status
        customer_id = user.stripe_customer_id
        current_db_time = db.session.query(func.now()).scalar()
        user_field_timestamp = user.created_at
        # Update the valid status if the data is too old from Stripe
        time_difference = current_db_time - user_field_timestamp
        # You can adjust this to any duration you need, currently the data stay fresh for 5 seconds
        expiration_threshold = datetime.timedelta(seconds=5)
        if time_difference > expiration_threshold:    
            # Double verify with Stripe that this person still has subscription valid
            is_subscribed_from_stripe = False
            active_subscription_id = None
            try:
                subscriptions = stripe.Subscription.list(customer=customer_id, status='active')
                if subscriptions.data: # If the list is not empty, means at least one active sub
                    active_sub = subscriptions.data[0] # Get the first active subscription
                    is_subscribed_from_stripe = True
                    active_subscription_id = active_sub.id
                # Update user's subscription status and ID in your database using SQLAlchemy
                user.is_subscribed = is_subscribed_from_stripe
                user.stripe_subscription_id = active_subscription_id # Set to None if not active
                user.created_at = func.now()
                db.session.commit() # Commit changes to the database
            except stripe.error.StripeError as e:
                print(f"Error retrieving customer: {e}")
                db.session.rollback() # Rollback any potential DB changes if Stripe call failed
                return jsonify({"error": "Failed to verify Stripe subscription status. Please try again later or contact support."}), 500
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                db.session.rollback()
                return jsonify({"error": "An internal server error occurred."}), 500
        return jsonify({
                "status": "success",
                "user_data": {
                    "google_user_id": user.google_user_id,
                    "email": user.email,
                    "is_subscribed": user.is_subscribed, # Use stored data
                    "stripe_customer_id": user.stripe_customer_id,
                    "stripe_subscription_id": user.stripe_subscription_id
                }
            }), 200
            
    else:
        # New user, register them
        try:
        # First, create a Stripe Customer for the new user
            stripe_customer = stripe.Customer.create(
                email=email,
                metadata={'google_user_id': google_user_id}
            )
            new_stripe_customer_id = stripe_customer.id

            # Create new user in your database using SQLAlchemy
            new_user = User(
                google_user_id=google_user_id,
                email=email,
                is_subscribed=False, # New users are not subscribed initially
                stripe_customer_id=new_stripe_customer_id,
                stripe_subscription_id=None,
                created_at = func.now()
            )
            db.session.add(new_user)
            db.session.commit() # Commit the new user

            return jsonify({
                "status": "success",
                "user_data": {
                    "google_user_id": new_user.google_user_id,
                    "email": new_user.email,
                    "is_subscribed": new_user.is_subscribed,
                    "stripe_customer_id": new_user.stripe_customer_id,
                    "stripe_subscription_id": new_user.stripe_subscription_id
                },
                "message": "User registered successfully."
            }), 201
        except IntegrityError: # Catches unique constraint violation (e.g., if email is not unique)
            db.session.rollback() # Rollback the failed database transaction
            # You might also want to delete the Stripe customer if DB insertion failed,
            # but usually, you'd handle the DB error first.
            return jsonify({"error": "A user with this Google ID or email already exists."}), 409
        except stripe.error.StripeError as e:
            db.session.rollback() # Rollback DB changes if Stripe customer creation failed
            print(f"Stripe API error creating customer: {e}")
            return jsonify({"error": f"Failed to register with Stripe: {str(e)}"}), 500
        except Exception as e:
            db.session.rollback()
            print(f"An unexpected error occurred during user registration: {e}")
            return jsonify({"error": "An internal server error occurred during registration."}), 500

# Checking out, create checkout url
@app.route('/stripe/create-checkout-session', methods=['POST'])
def create_checkout_session_backend():
    data = request.json
    google_user_id = data.get('google_user_id')
    user_email = data.get('user_email') # Ensure this matches client-side key 'email' or 'user_email'

    if not google_user_id or not user_email:
        return jsonify({"error": "Missing user information"}), 400

    # 1. Retrieve the user from the database using SQLAlchemy
    user = User.query.filter_by(google_user_id=google_user_id).first()

    if not user:
        # This case should ideally not happen if register_or_get_status is called first,
        # but it's good to handle it.
        return jsonify({"error": "User not found in database."}), 404

    customer_id = user.stripe_customer_id

    try:
        # 2. If the user doesn't have a Stripe customer_id yet, create one
        if not customer_id:
            stripe_customer = stripe.Customer.create(
                email=user_email,
                metadata={'google_user_id': google_user_id}
            )
            customer_id = stripe_customer.id
            
            # Update the user record in your database with the new customer_id
            user.stripe_customer_id = customer_id
            user.created_at = func.now()
            db.session.commit() # Commit the update
            
            print(f"Created new Stripe Customer: {customer_id} for Google user {google_user_id}")
        else:
            print(f"Using existing Stripe Customer: {customer_id} for Google user {google_user_id}")

        # 4. Create the Stripe Checkout Session
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            line_items=[
                {
                    'price': STRIPE_PREMIUM_PRICE_ID,
                    'quantity': 1,
                },
            ],
            mode='subscription',
            # success_url and cancel_url must point to your *backend's* public URL
            success_url=f'{BASE_URL}stripe-success?session_id={{CHECKOUT_SESSION_ID}}&google_user_id={google_user_id}',
            cancel_url=f'{BASE_URL}stripe-cancel?google_user_id={google_user_id}',
            metadata={'google_user_id': google_user_id} # Important for webhooks
        )
        return jsonify({'id': checkout_session.id, 'url': checkout_session.url})

    except stripe.error.StripeError as e:
        # Rollback any DB changes if Stripe API call failed (e.g., customer creation failed)
        db.session.rollback() 
        print(f"Stripe API error creating checkout session: {e}")
        return jsonify(error=str(e)), 403 # 403 Forbidden or 400 Bad Request might be appropriate
    except Exception as e:
        db.session.rollback() # Rollback for any other unexpected errors
        print(f"An unexpected error occurred creating checkout session: {e}")
        return jsonify(error="An internal server error occurred: " + str(e)), 500

@app.route('/stripe-success')
def stripe_success_page():
    # This page is shown to the user in their browser after successful payment.
    # It just gives them confirmation and tells them to return to the app.
    # The actual database update for subscription status happens via webhook!
    return "<h1 style='color: green;'>Subscription Successful!</h1><p>Your payment was confirmed. You can now close this window and return to the application.</p>"

@app.route('/stripe-cancel')
def stripe_cancel_page():
    # This page is shown to the user in their browser if they cancel payment.
    return "<h1 style='color: orange;'>Subscription Canceled.</h1><p>You have canceled the subscription process. You can close this window and return to the application.</p>"

# Listen to checkout page response
# Called by Stripe, handles significant user events
@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get('stripe-signature')
    event = None
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        print(f"Webhook Error: Invalid payload: {e}")
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        print(f"Webhook Error: Invalid signature: {e}")
        return 'Invalid signature', 400

    # --- Start of Database Interaction (using SQLAlchemy) ---
    try:
        # Handle the event
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            google_user_id = session.get('metadata', {}).get('google_user_id')
            subscription_id = session.get('subscription') 
            if google_user_id and session.payment_status == 'paid' and subscription_id:
                # Find the user by google_user_id
                user = User.query.filter_by(google_user_id=google_user_id).first()
                if user:
                    user.is_subscribed = True
                    user.stripe_subscription_id = subscription_id
                    user.created_at = func.now()
                    db.session.commit() # Commit changes to the database
                    print(f"Webhook: User {google_user_id} subscribed (checkout.session.completed). Session: {session.id}")
                else:
                    print(f"Webhook: User {google_user_id} not found for checkout session {session.id}. (Already handled by register_or_get_status?)")
            else:
                print(f"Webhook: Checkout session completed but not paid or missing google_user_id/subscription_id: {session.id}")

        elif event['type'] == 'customer.subscription.deleted':
            subscription = event['data']['object']
            customer_id = subscription.customer

            user = User.query.filter_by(stripe_customer_id=customer_id).first()

            if user:
                user.is_subscribed = False
                user.stripe_subscription_id = None
                user.created_at = func.now()
                try:
                    db.session.commit()
                    # Force refresh the object from the DB after commit
                    db.session.refresh(user)
                    print(f"Webhook: User {user.google_user_id} subscription canceled'")
                except Exception as e:
                    db.session.rollback() # Rollback in case of error
                    print(f"ERROR: Failed to commit subscription cancellation for user {user.google_user_id}: {e}")
            else:
                print(f"Webhook: Subscription deleted for unknown customer {customer_id}")
            return jsonify({"status": "success"}), 200

        elif event['type'] == 'invoice.payment_succeeded':
            invoice = event['data']['object']
            customer_id = invoice.customer

            # Find the user by stripe_customer_id
            user = User.query.filter_by(stripe_customer_id=customer_id).first()
            if user:
                user.is_subscribed = True # Set to True on successful payment
                # If you get subscription_id from invoice, update it too
                # user.stripe_subscription_id = invoice.subscription
                user.created_at = func.now()
                db.session.commit() # Commit changes
                print(f"Webhook: Invoice payment succeeded for user {user.google_user_id}")

        elif event['type'] == 'invoice.payment_failed':
            invoice = event['data']['object']
            customer_id = invoice.customer
            
            # Find the user by stripe_customer_id
            user = User.query.filter_by(stripe_customer_id=customer_id).first()
            if user:
                user.is_subscribed = False # Set to False on failed payment
                user.created_at = func.now()
                db.session.commit() # Commit changes
                print(f"Webhook: Invoice payment failed for user {user.google_user_id}")

        # Add more webhook events as needed (e.g., customer.subscription.deleted)

    except Exception as e:
        # Crucial: Rollback the database session if any error occurs during processing
        db.session.rollback()
        print(f"Error handling webhook event {event.get('type')}: {e}")
        # Log the full traceback for debugging in a production environment
        import traceback
        traceback.print_exc()
        return 'Webhook handler failed', 500
    # No finally block for db.session.close() needed with Flask-SQLAlchemy;
    # it handles session cleanup automatically at the end of the request.

    return 'Success', 200

@app.route('/stripe-portal-return')
def stripe_portal_return_page():
    # This page is shown to the user in their browser after returning from the Customer Portal.
    # The actual database update for subscription status (cancellation, update, etc.)
    # would have happened via webhooks (e.g., customer.subscription.updated) already.
    return """
    <h1 style='color: blue;'>Subscription Management Complete!</h1>
    <p>You have returned from the Stripe Customer Portal. Any changes you made will be reflected in the application shortly.</p>
    <p>You can now close this window and return to the application.</p>
    """

@app.route('/stripe/create-customer-portal-session', methods=['POST'])
def create_customer_portal_session_backend():
    data = request.json
    google_user_id = data.get('google_user_id')

    if not google_user_id:
        return jsonify({"error": "Missing google_user_id"}), 400

    # 1. Retrieve the user from the database using SQLAlchemy
    user = User.query.filter_by(google_user_id=google_user_id).first()

    # 2. Check if user and their Stripe customer ID exist
    if not user or not user.stripe_customer_id:
        return jsonify({"error": "Stripe customer not found for this user."}), 404

    customer_id = user.stripe_customer_id

    try:
        # 4. Create the Stripe Billing Portal Session
        portalSession = stripe.billing_portal.Session.create(
            customer=customer_id,
            # return_url must point to your *backend's* public URL
            return_url=f'{BASE_URL}stripe-portal-return?google_user_id={google_user_id}'
        )
        return jsonify({'url': portalSession.url})

    except stripe.error.StripeError as e:
        # No db.session.rollback() needed here as no DB write operations are performed
        print(f"Stripe API error creating customer portal session: {e}")
        return jsonify(error=str(e)), 403 # 403 Forbidden or 500 Internal Server Error
    except Exception as e:
        print(f"An unexpected error occurred creating customer portal session: {e}")
        return jsonify(error="An internal server error occurred: " + str(e)), 500

# if __name__ == '__main__':
#     with app.app_context():
#         db.create_all() # This creates all tables defined by your SQLAlchemy models
#         print("Database tables checked/created.")
#     app.run(host='0.0.0.0', port=8080, debug=True)