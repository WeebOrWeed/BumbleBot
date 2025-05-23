# backend_server.py
import os
from flask import Flask, request, jsonify, redirect, url_for
from flask_cors import CORS
import stripe
import sqlite3
import json # For storing metadata if needed

# --- Configuration (Centralized Backend) ---
# IMPORTANT: Never hardcode sensitive keys in production.
# Use environment variables for STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, etc.
# For local testing, you can put them here, but for App Engine, configure them
# in app.yaml or as environment variables.
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "pk_test_51RR6ziQYrsgIyvPmELFVZyFR1d8EJr37NZlCnmotzF8kDzXk6bJGkViqnVuCrW3DYqIqGMGtGtNrZ7EsbRJ29yI700hrqlYa8D")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "sk_test_51RR6ziQYrsgIyvPmGwjgq833pM7cc0dCEH758hw0juZR7ShHvhEXG89UTM5rVmwHwgdmhCJrd6AWTMeXQRCzEnPY005YxTuERR")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "whsec_c09fecb2e00cca4ebad5185559b00431ca029269d0aa0530978b68d0927f2002") # From Stripe Dashboard webhook settings
STRIPE_PREMIUM_PRICE_ID = os.environ.get("STRIPE_PREMIUM_PRICE_ID", "price_1RR74UQYrsgIyvPmAshepzTl")

stripe.api_key = STRIPE_SECRET_KEY

app = Flask(__name__)
CORS(app) # Enable CORS for all routes (important for your Tkinter app to communicate)

# --- Database Setup (SQLite for simplicity, use Cloud SQL/Firestore in production) ---
DATABASE = 'users.db'

def init_db():
    with app.app_context():
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                google_user_id TEXT PRIMARY KEY,
                email TEXT,
                is_subscribed BOOLEAN,
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT
            )
        ''')
        conn.commit()
        conn.close()

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row # This allows access to columns by name
    return conn

# --- API Endpoints for Tkinter App ---

@app.route('/')
def health_check():
    return "Backend is running!"

@app.route('/users/register_or_get_status', methods=['POST'])
def register_or_get_user_status():
    data = request.json
    google_user_id = data.get('google_user_id')
    email = data.get('email')

    if not google_user_id or not email:
        return jsonify({"error": "Missing user_id or email"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    
    user = cursor.execute("SELECT * FROM users WHERE google_user_id = ?", (google_user_id,)).fetchone()

    if user:
        # User exists, return their current status
        user_dict = dict(user) # Convert Row object to dict
        conn.close()
        return jsonify({
            "status": "success",
            "user_data": {
                "google_user_id": user_dict['google_user_id'],
                "email": user_dict['email'],
                "is_subscribed": bool(user_dict['is_subscribed']), # Convert int to bool
                "stripe_customer_id": user_dict['stripe_customer_id'],
                "stripe_subscription_id": user_dict['stripe_subscription_id']
            }
        }), 200
    else:
        # New user, register them
        try:
            cursor.execute(
                "INSERT INTO users (google_user_id, email, is_subscribed, stripe_customer_id, stripe_subscription_id) VALUES (?, ?, ?, ?, ?)",
                (google_user_id, email, False, None, None)
            )
            conn.commit()
            conn.close()
            return jsonify({
                "status": "success",
                "user_data": {
                    "google_user_id": google_user_id,
                    "email": email,
                    "is_subscribed": False,
                    "stripe_customer_id": None,
                    "stripe_subscription_id": None
                },
                "message": "User registered successfully."
            }), 201
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({"error": "User with this Google ID already exists (race condition?)"}), 409


@app.route('/stripe/create-checkout-session', methods=['POST'])
def create_checkout_session_backend():
    data = request.json
    google_user_id = data.get('google_user_id')
    user_email = data.get('user_email')

    if not google_user_id or not user_email:
        return jsonify({"error": "Missing user information"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    user_record = cursor.execute("SELECT stripe_customer_id FROM users WHERE google_user_id = ?", (google_user_id,)).fetchone()
    conn.close()

    customer_id = user_record['stripe_customer_id'] if user_record else None

    try:
        if not customer_id:
            customer = stripe.Customer.create(
                email=user_email,
                metadata={'google_user_id': google_user_id}
            )
            customer_id = customer.id
            # Update the database with the new customer_id
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET stripe_customer_id = ? WHERE google_user_id = ?", (customer_id, google_user_id))
            conn.commit()
            conn.close()
            print(f"Created new Stripe Customer: {customer_id} for Google user {google_user_id}")
        else:
            print(f"Using existing Stripe Customer: {customer_id} for Google user {google_user_id}")

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
            # The Tkinter app will open this URL for the user.
            success_url=f'https://{os.environ.get("GAE_APPLICATION", "localhost:8080")}/stripe-success?session_id={{CHECKOUT_SESSION_ID}}&google_user_id={google_user_id}',
            cancel_url=f'https://{os.environ.get("GAE_APPLICATION", "localhost:8080")}/stripe-cancel',
            metadata={'google_user_id': google_user_id} # Important for webhooks
        )
        return jsonify({'id': checkout_session.id, 'url': checkout_session.url})
    except Exception as e:
        print(f"Error creating checkout session: {e}")
        return jsonify(error=str(e)), 403

@app.route('/stripe-success')
def stripe_success_page():
    session_id = request.args.get('session_id')
    google_user_id = request.args.get('google_user_id')

    # This page is shown to the user in their browser after successful payment.
    # It just gives them confirmation and tells them to return to the app.
    # The actual database update for subscription status happens via webhook!
    return "<h1 style='color: green;'>Subscription Successful!</h1><p>Your payment was confirmed. You can now close this window and return to the application.</p>"

@app.route('/stripe-cancel')
def stripe_cancel_page():
    # This page is shown to the user in their browser if they cancel payment.
    return "<h1 style='color: orange;'>Subscription Canceled.</h1><p>You have canceled the subscription process. You can close this window and return to the application.</p>"

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

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Handle the event
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            google_user_id = session.get('metadata', {}).get('google_user_id')
            subscription_id = session.get('subscription') # Get subscription ID from checkout session
            
            if google_user_id and session.payment_status == 'paid' and subscription_id:
                cursor.execute(
                    "UPDATE users SET is_subscribed = ?, stripe_subscription_id = ? WHERE google_user_id = ?",
                    (True, subscription_id, google_user_id)
                )
                conn.commit()
                print(f"Webhook: User {google_user_id} subscribed (checkout.session.completed). Session: {session.id}")
            else:
                print(f"Webhook: Checkout session completed but not paid or missing google_user_id/subscription_id: {session.id}")

        elif event['type'] == 'customer.subscription.updated':
            subscription = event['data']['object']
            customer_id = subscription.customer
            
            user_record = cursor.execute("SELECT google_user_id FROM users WHERE stripe_customer_id = ?", (customer_id,)).fetchone()
            if user_record:
                google_user_id = user_record['google_user_id']
                is_active = (subscription.status == 'active' or subscription.status == 'trialing')
                
                cursor.execute(
                    "UPDATE users SET is_subscribed = ?, stripe_subscription_id = ? WHERE google_user_id = ?",
                    (is_active, subscription.id, google_user_id)
                )
                conn.commit()
                print(f"Webhook: User {google_user_id} subscription updated to '{subscription.status}'")
            else:
                print(f"Webhook: Subscription updated for unknown customer {customer_id}")

        elif event['type'] == 'invoice.payment_succeeded':
            invoice = event['data']['object']
            customer_id = invoice.customer
            user_record = cursor.execute("SELECT google_user_id FROM users WHERE stripe_customer_id = ?", (customer_id,)).fetchone()
            if user_record:
                google_user_id = user_record['google_user_id']
                cursor.execute("UPDATE users SET is_subscribed = ? WHERE google_user_id = ?", (True, google_user_id))
                conn.commit()
                print(f"Webhook: Invoice payment succeeded for user {google_user_id}")

        elif event['type'] == 'invoice.payment_failed':
            invoice = event['data']['object']
            customer_id = invoice.customer
            user_record = cursor.execute("SELECT google_user_id FROM users WHERE stripe_customer_id = ?", (customer_id,)).fetchone()
            if user_record:
                google_user_id = user_record['google_user_id']
                cursor.execute("UPDATE users SET is_subscribed = ? WHERE google_user_id = ?", (False, google_user_id))
                conn.commit()
                print(f"Webhook: Invoice payment failed for user {google_user_id}")

        # Add more webhook events as needed (e.g., customer.subscription.deleted)

    except Exception as e:
        print(f"Error handling webhook event {event.get('type')}: {e}")
        # Consider logging the full traceback here for debugging
        return 'Webhook handler failed', 500
    finally:
        conn.close()

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

    conn = get_db_connection()
    cursor = conn.cursor()
    user_record = cursor.execute("SELECT stripe_customer_id FROM users WHERE google_user_id = ?", (google_user_id,)).fetchone()
    conn.close()

    customer_id = user_record['stripe_customer_id'] if user_record else None

    if not customer_id:
        return jsonify({"error": "Stripe customer not found for this user."}), 404

    try:
        portalSession = stripe.billing_portal.Session.create(
            customer=customer_id,
            # return_url must point to your *backend's* public URL
            return_url=f'https://{os.environ.get("GAE_APPLICATION", "localhost:8080")}/stripe-portal-return'
        )
        return jsonify({'url': portalSession.url})
    except Exception as e:
        print(f"Error creating customer portal session: {e}")
        return jsonify(error=str(e)), 500

if __name__ == '__main__':
    init_db() # Initialize the database when the backend starts
    app.run(host='0.0.0.0', port=8080, debug=True) # debug=True for local development