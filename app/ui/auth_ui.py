import tkinter as tk
from tkinter import ttk, messagebox
import os
import webbrowser
import threading
import time # For simulating checks

# Google OAuth imports (from previous example)
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Stripe imports
import stripe
from flask import Flask, request, jsonify, redirect, url_for
from flask_cors import CORS # To handle CORS issues if your Tkinter app makes requests to localhost

# --- Configuration ---
CLIENT_SECRETS_FILE = '..\\configs\\client_secret.json'
GOOGLE_SCOPES = ['https://www.googleapis.com/auth/userinfo.profile',
                 'https://www.googleapis.com/auth/userinfo.email', 'openid']

# Stripe Configuration
STRIPE_PUBLISHABLE_KEY = "YOUR_STRIPE_PUBLISHABLE_KEY" # pk_test_...
STRIPE_SECRET_KEY = "YOUR_STRIPE_SECRET_KEY"         # sk_test_...
STRIPE_WEBHOOK_SECRET = "YOUR_STRIPE_WEBHOOK_SECRET"  # Found in webhook settings on Stripe Dashboard
STRIPE_PREMIUM_PRICE_ID = "price_123ABCDEF..."        # Get this from your Stripe Product Catalog

stripe.api_key = STRIPE_SECRET_KEY

# --- Local Web Server for Stripe (Flask) ---
app = Flask(__name__)
CORS(app) # Enable CORS for all routes

# A simple in-memory store for user data. In a real app, use a database (e.g., SQLite).
# Key: Google User ID, Value: {'email': '...', 'stripe_customer_id': '...', 'is_subscribed': True/False}
user_data_store = {}
USER_DATA_FILE = 'user_data.json'

def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        try:
            import json
            with open(USER_DATA_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_user_data():
    import json
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(user_data_store, f, indent=4)

user_data_store = load_user_data()

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    data = request.json
    google_user_id = data.get('google_user_id')
    user_email = data.get('user_email')

    if not google_user_id or not user_email:
        return jsonify({"error": "Missing user information"}), 400

    customer_id = user_data_store.get(google_user_id, {}).get('stripe_customer_id')

    try:
        if not customer_id:
            # Create a new Stripe Customer if one doesn't exist for this Google user
            customer = stripe.Customer.create(
                email=user_email,
                metadata={'google_user_id': google_user_id}
            )
            customer_id = customer.id
            user_data_store.setdefault(google_user_id, {})['stripe_customer_id'] = customer_id
            save_user_data()
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
            success_url=f'http://localhost:8080/stripe-success?session_id={{CHECKOUT_SESSION_ID}}&google_user_id={google_user_id}',
            cancel_url='http://localhost:8080/stripe-cancel',
            metadata={'google_user_id': google_user_id}
        )
        return jsonify({'id': checkout_session.id, 'url': checkout_session.url})
    except Exception as e:
        print(f"Error creating checkout session: {e}")
        return jsonify(error=str(e)), 403

@app.route('/stripe-success')
def stripe_success():
    session_id = request.args.get('session_id')
    google_user_id = request.args.get('google_user_id')

    if not session_id or not google_user_id:
        return "Error: Missing session ID or Google User ID. Please close this window and try again.", 400

    try:
        # Retrieve the session to get payment status and subscription ID
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        
        if checkout_session.payment_status == 'paid' and checkout_session.status == 'complete':
            # This is a good place to update your user's subscription status
            user_data_store.setdefault(google_user_id, {})['is_subscribed'] = True
            user_data_store[google_user_id]['stripe_subscription_id'] = checkout_session.subscription
            save_user_data()
            print(f"Stripe success: User {google_user_id} is now subscribed. Session: {session_id}")
            # This HTML will be shown in the browser. A more robust solution might
            # use JavaScript to communicate back to the Tkinter app.
            return "<h1 style='color: green;'>Subscription Successful!</h1><p>You can now close this window and return to the application.</p>"
        else:
            print(f"Stripe success but not paid/complete: Session {session_id}, Status: {checkout_session.status}, Payment Status: {checkout_session.payment_status}")
            return "<h1 style='color: orange;'>Payment Processing/Incomplete.</h1><p>Your payment is being processed or requires further action. Please check the application for status updates.</p>"
    except Exception as e:
        print(f"Error processing Stripe success: {e}")
        return f"<h1 style='color: red;'>Error processing payment success: {e}</h1><p>Please contact support if the issue persists.</p>", 500

@app.route('/stripe-cancel')
def stripe_cancel():
    return "<h1 style='color: orange;'>Subscription Canceled.</h1><p>You have canceled the subscription process. You can close this window and return to the application.</p>"

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
        # Invalid payload
        print(f"Webhook Error: Invalid payload: {e}")
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print(f"Webhook Error: Invalid signature: {e}")
        return 'Invalid signature', 400

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        google_user_id = session.get('metadata', {}).get('google_user_id')
        if google_user_id and session.payment_status == 'paid':
            user_data_store.setdefault(google_user_id, {})['is_subscribed'] = True
            user_data_store[google_user_id]['stripe_subscription_id'] = session.subscription
            save_user_data()
            print(f"Webhook: User {google_user_id} subscribed (checkout.session.completed). Session: {session.id}")
            # Potentially notify Tkinter app here if it's polling or using a more advanced IPC
        else:
            print(f"Webhook: Checkout session completed but not paid or missing google_user_id: {session.id}")

    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        customer_id = subscription.customer
        # Find Google User ID associated with this Stripe Customer ID
        google_user_id = None
        for g_uid, data in user_data_store.items():
            if data.get('stripe_customer_id') == customer_id:
                google_user_id = g_uid
                break

        if google_user_id:
            # Update subscription status based on Stripe's current status
            if subscription.status == 'active':
                user_data_store[google_user_id]['is_subscribed'] = True
            else: # E.g., 'canceled', 'unpaid', 'past_due', 'incomplete'
                user_data_store[google_user_id]['is_subscribed'] = False
            user_data_store[google_user_id]['stripe_subscription_id'] = subscription.id
            save_user_data()
            print(f"Webhook: User {google_user_id} subscription updated to '{subscription.status}'")
        else:
            print(f"Webhook: Subscription updated for unknown customer {customer_id}")

    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        customer_id = invoice.customer
        # Similar logic to customer.subscription.updated to find google_user_id
        google_user_id = None
        for g_uid, data in user_data_store.items():
            if data.get('stripe_customer_id') == customer_id:
                google_user_id = g_uid
                break
        if google_user_id:
            user_data_store[google_user_id]['is_subscribed'] = True
            save_user_data()
            print(f"Webhook: Invoice payment succeeded for user {google_user_id}")

    elif event['type'] == 'invoice.payment_failed':
        invoice = event['data']['object']
        customer_id = invoice.customer
        google_user_id = None
        for g_uid, data in user_data_store.items():
            if data.get('stripe_customer_id') == customer_id:
                google_user_id = g_uid
                break
        if google_user_id:
            user_data_store[google_user_id]['is_subscribed'] = False
            save_user_data()
            print(f"Webhook: Invoice payment failed for user {google_user_id}")

    # Return a 200 response to acknowledge receipt of the event
    return 'Success', 200

def run_flask_server():
    # Use a specific port, e.g., 8080, and ensure it's free.
    # In a real application, you might want to bind to '127.0.0.1' only
    # for security, but '0.0.0.0' makes it accessible if needed for testing.
    app.run(port=8080, debug=False) # Set debug=False for production

# Start Flask server in a separate thread
flask_thread = threading.Thread(target=run_flask_server, daemon=True)
flask_thread.start()

# --- Google OAuth Functions ---
def get_google_credentials():
    credentials = None
    token_file = 'token.json'

    if os.path.exists(token_file):
        credentials = Credentials.from_authorized_user_file(token_file, GOOGLE_SCOPES)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
            except Exception as e:
                print(f"Error refreshing Google token: {e}")
                credentials = None
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, GOOGLE_SCOPES)
            try:
                credentials = flow.run_local_server(port=0)
            except Exception as e:
                messagebox.showerror("Authentication Error", f"Failed to authenticate with Google: {e}")
                return None

        with open(token_file, 'w') as token:
            token.write(credentials.to_json())
            print(f"Google token saved to {token_file}")
    
    return credentials

# --- Tkinter Application ---
class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tkinter Google OAuth + Stripe App")
        self.geometry("800x600")

        self.credentials = None
        self.user_profile = None
        self.current_google_user_id = None # Store the current logged-in Google ID

        self.check_login_status()

        # Periodically check subscription status (e.g., every 5 minutes)
        # This is a fallback; webhooks are more immediate
        self.after(300000, self.periodic_subscription_check)

    def check_login_status(self):
        if not self.credentials:
            self.show_login_page()
        else:
            self.fetch_user_profile_and_proceed()

    def show_login_page(self):
        for widget in self.winfo_children():
            widget.destroy()

        self.login_frame = ttk.Frame(self, padding="20")
        self.login_frame.pack(expand=True, fill="both")

        ttk.Label(self.login_frame, text="Welcome! Please log in with Google.", font=("Arial", 16)).pack(pady=20)
        
        google_login_button = ttk.Button(self.login_frame, text="Login with Google", command=self.handle_google_login)
        google_login_button.pack(pady=10)

    def handle_google_login(self):
        self.credentials = get_google_credentials()

        if self.credentials:
            self.fetch_user_profile_and_proceed()
        else:
            messagebox.showerror("Login Failed", "Google authentication was not successful.")
            self.show_login_page()

    def fetch_user_profile_and_proceed(self):
        try:
            service = build('oauth2', 'v2', credentials=self.credentials)
            user_info = service.userinfo().get().execute()
            self.user_profile = user_info
            self.current_google_user_id = self.user_profile.get('id')
            print(f"User Profile: {self.user_profile}")

            # Ensure user data exists for this Google ID
            if self.current_google_user_id not in user_data_store:
                user_data_store[self.current_google_user_id] = {
                    'email': self.user_profile.get('email'),
                    'is_subscribed': False,
                    'stripe_customer_id': None,
                    'stripe_subscription_id': None
                }
                save_user_data()

            self.check_subscription_status()

        except Exception as e:
            messagebox.showerror("API Error", f"Could not fetch user profile: {e}")
            self.user_profile = None
            self.current_google_user_id = None
            self.show_login_page() # Go back to login if profile fetch fails

    def check_subscription_status(self):
        if not self.current_google_user_id:
            self.show_login_page() # Should not happen if Google login was successful
            return

        user_info = user_data_store.get(self.current_google_user_id, {})
        is_subscribed = user_info.get('is_subscribed', False)

        if is_subscribed:
            self.show_main_page()
        else:
            self.show_subscribe_page()

    def show_subscribe_page(self):
        for widget in self.winfo_children():
            widget.destroy()

        self.subscribe_frame = ttk.Frame(self, padding="20")
        self.subscribe_frame.pack(expand=True, fill="both")

        ttk.Label(self.subscribe_frame, text="You are not subscribed.", font=("Arial", 16, "bold")).pack(pady=20)
        ttk.Label(self.subscribe_frame, text="Please subscribe to access the main features.").pack(pady=10)

        subscribe_button = ttk.Button(self.subscribe_frame, text="Subscribe Now", command=self.open_stripe_checkout)
        subscribe_button.pack(pady=20)
        
        # Optionally, a button to re-check status if they paid externally or on another device
        check_status_button = ttk.Button(self.subscribe_frame, text="Refresh Subscription Status", command=self.check_subscription_status)
        check_status_button.pack(pady=10)

        logout_button = ttk.Button(self.subscribe_frame, text="Logout", command=self.logout)
        logout_button.pack(pady=20)

    def open_stripe_checkout(self):
        if not self.current_google_user_id or not self.user_profile:
            messagebox.showerror("Error", "User not logged in or profile not found.")
            return

        try:
            # Make a request to your local Flask server to create a Checkout Session
            import requests
            response = requests.post('http://localhost:8080/create-checkout-session', json={
                'google_user_id': self.current_google_user_id,
                'user_email': self.user_profile.get('email')
            })
            response.raise_for_status() # Raise an exception for HTTP errors
            session_data = response.json()
            checkout_url = session_data.get('url')

            if checkout_url:
                webbrowser.open_new(checkout_url)
                messagebox.showinfo("Redirecting to Stripe", "A new browser window will open for payment. Please complete the subscription there.")
                # You might want to disable UI elements or show a "waiting" message here
                # and then poll for subscription status or rely on webhooks.
                self.after(5000, self.check_subscription_status) # Re-check status after 5 seconds as a fallback
            else:
                messagebox.showerror("Stripe Error", "Could not get Stripe Checkout URL.")
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Network Error", f"Could not connect to local server: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")

    def show_main_page(self):
        for widget in self.winfo_children():
            widget.destroy()

        self.main_frame = ttk.Frame(self, padding="20")
        self.main_frame.pack(expand=True, fill="both")

        user_info = user_data_store.get(self.current_google_user_id, {})
        ttk.Label(self.main_frame, text=f"Welcome, {self.user_profile.get('name', 'User')}!", font=("Arial", 18, "bold")).pack(pady=20)
        ttk.Label(self.main_frame, text=f"Email: {self.user_profile.get('email', 'N/A')}").pack(pady=5)
        ttk.Label(self.main_frame, text=f"Google ID: {self.user_profile.get('id', 'N/A')}").pack(pady=5)
        ttk.Label(self.main_frame, text=f"Subscription Status: {'Active' if user_info.get('is_subscribed') else 'Inactive'}", font=("Arial", 12)).pack(pady=10)
        
        ttk.Label(self.main_frame, text="\nThis is your secure main application content, only for subscribers!").pack(pady=20)

        # Link to Stripe Customer Portal (optional but highly recommended)
        manage_subscription_button = ttk.Button(self.main_frame, text="Manage Subscription (Stripe Portal)", command=self.open_customer_portal)
        manage_subscription_button.pack(pady=10)

        logout_button = ttk.Button(self.main_frame, text="Logout", command=self.logout)
        logout_button.pack(pady=20)

    def open_customer_portal(self):
        if not self.current_google_user_id:
            messagebox.showerror("Error", "User not logged in.")
            return

        user_info = user_data_store.get(self.current_google_user_id)
        customer_id = user_info.get('stripe_customer_id')

        if not customer_id:
            messagebox.showinfo("Info", "You don't have a Stripe customer record yet. Please subscribe first.")
            return

        try:
            # Create a Customer Portal session
            portalSession = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url='http://localhost:8080/stripe-success' # Return to a local URL
            )
            webbrowser.open_new(portalSession.url)
            messagebox.showinfo("Stripe Customer Portal", "A new browser window will open to manage your subscription.")
        except Exception as e:
            messagebox.showerror("Stripe Portal Error", f"Could not open customer portal: {e}")

    def logout(self):
        # Invalidate local Google token if it exists
        if os.path.exists('token.json'):
            os.remove('token.json')
        
        # Clear user data for current session
        self.credentials = None
        self.user_profile = None
        self.current_google_user_id = None
        
        messagebox.showinfo("Logout", "Logged out successfully.")
        self.show_login_page()

    def periodic_subscription_check(self):
        if self.current_google_user_id:
            # This is a fallback. Webhooks are more reliable.
            # You'd ideally make an API call to Stripe to get the actual subscription status
            # based on self.current_google_user_id's stripe_customer_id and stripe_subscription_id.
            # For simplicity, we'll just re-evaluate based on the local `user_data_store`.
            print("Performing periodic subscription check...")
            self.check_subscription_status()
        self.after(300000, self.periodic_subscription_check) # Schedule next check


if __name__ == "__main__":
    app_instance = Application()
    app_instance.mainloop()