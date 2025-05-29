import tkinter as tk
from tkinter import ttk, messagebox
import os
import webbrowser
import threading
import time # For simulating checks
import requests
from utils import utilities as UM
from pathlib import Path
import sys

# Google OAuth imports (from previous example)
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow

# --- Configuration ---
CLIENT_SECRETS_FILE = os.path.join('configs','client_secret.json')
GOOGLE_SCOPES = ['https://www.googleapis.com/auth/userinfo.profile',
                 'https://www.googleapis.com/auth/userinfo.email', 'openid']
BASE_URL = 'https://bumblebot-460521.uc.r.appspot.com/'

def get_executable_dir_path(relative_path=""):
    """
    Get the absolute path to a file or folder located relative to the executable.
    Works for both development and compiled PyInstaller executables.
    """
    if getattr(sys, 'frozen', False):
        # We are running in a bundle (PyInstaller)
        # sys.executable is the path to the .exe itself (e.g., D:\BumbleBot\app\dist\BumbleBot.exe)
        executable_dir = Path(sys.executable).parent # This gives you D:\BumbleBot\app\dist\
    else:
        # We are running in a normal Python environment (development)
        # __file__ is the path to the script (e.g., C:\YourProject\main.py)
        executable_dir = Path(__file__).resolve().parent.parent # This gives you C:\YourProject\
        # You might need to adjust this for development if your 'configs', 'images', 'weights'
        # folders are relative to a different part of your project structure than main.py
        # For example, if main.py is in 'app/', and these folders are in the project root:
        # executable_dir = Path(__file__).resolve().parents[1] # Go up two levels from main.py

    return (executable_dir / relative_path).resolve()

# BASE_DIR now refers to the directory containing the executable
BASE_DIR_EXE = get_executable_dir_path()
TOKEN_PATH = BASE_DIR_EXE / "configs" / "token.json"
class AuthUI(tk.Toplevel):
    def __init__(self, parent, onDestroy):
        super().__init__(parent)
        self.settings = UM.load_settings()
        self.title("BumbleBot Login")
        self.geometry("800x600")
        self.iconbitmap(UM.resource_path("BumbleBotLogo.ico"))
        self.focus_set()
        
        self.credentials = None
        self.user_profile = None
        self.current_google_user_id = None # Store the current logged-in Google ID
        self.polling_thread = None
        self.polling_active = False
        self.open_bumble_bot = False
        self.check_login_status()
        # Bind to the <Destroy> event
        # This handler will be called *just before* the widget is fully destroyed
        self.bind("<Destroy>", onDestroy)

        # Periodically check subscription status (e.g., every 5 minutes)
        # This is a fallback; webhooks are more immediate
        self.after(300000, self.periodic_subscription_check)

    # --- Google OAuth Functions ---
    def get_google_credentials(self):
        credentials = None

        if os.path.exists(TOKEN_PATH):
            credentials = Credentials.from_authorized_user_file(TOKEN_PATH, GOOGLE_SCOPES)

        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                try:
                    credentials.refresh(Request())
                except Exception as e:
                    # print(f"Error refreshing Google token: {e}")
                    credentials = None
            else:
                flow = InstalledAppFlow.from_client_secrets_file(os.path.join(self.settings['BASE_DIR'], CLIENT_SECRETS_FILE), GOOGLE_SCOPES)
                try:
                    credentials = flow.run_local_server(port=0)
                except Exception as e:
                    messagebox.showerror("Authentication Error", f"Failed to authenticate with Google: {e}")
                    return None

            with open(TOKEN_PATH, 'w') as token:
                token.write(credentials.to_json())
                # print(f"Google token saved to {token_file}")

        return credentials

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
        self.credentials = self.get_google_credentials()

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
            # print(f"User Profile: {self.user_profile}")

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

        # Make a request to your Flask server to get customer information
        response = requests.post(f'{BASE_URL}/users/register_or_get_status', json={
            'google_user_id': self.current_google_user_id,
            'user_email': self.user_profile.get('email')
        })
        response.raise_for_status() # Raise an exception for HTTP errors
        self.user_stripe_data = response.json()
        self.is_subscribed = self.user_stripe_data.get('user_data',{}).get("is_subscribed", False)

        self.show_main_page()

    def open_stripe_checkout(self):
        if not self.current_google_user_id or not self.user_profile:
            messagebox.showerror("Error", "User not logged in or profile not found.")
            return

        try:
            # Make a request to your Flask server to create a Checkout Session
            response = requests.post(f'{BASE_URL}/stripe/create-checkout-session', json={
                'google_user_id': self.current_google_user_id,
                'user_email': self.user_profile.get('email')
            })
            response.raise_for_status() # Raise an exception for HTTP errors
            session_data = response.json()
            checkout_url = session_data.get('url')

            if checkout_url:
                webbrowser.open_new(checkout_url)
                # Start aggressive polling in a background thread
                self.show_waiting_for_subscription_page() # Show a waiting UI
                self.polling_active = True
                self.polling_thread = threading.Thread(target=self._poll_for_subscription_status, kwargs={'lookingForStatus': True}, daemon=True)
                self.polling_thread.start()
            else:
                messagebox.showerror("Stripe Error", "Could not get Stripe Checkout URL.")
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Network Error", f"Could not connect to local server: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")

    def show_waiting_for_subscription_page(self):
        for widget in self.winfo_children():
            widget.destroy()

        self.waiting_frame = ttk.Frame(self, padding="20")
        self.waiting_frame.pack(expand=True, fill="both")

        ttk.Label(self.waiting_frame, text="Waiting for Subscription Confirmation...", font=("Arial", 16, "bold")).pack(pady=20)
        ttk.Label(self.waiting_frame, text="Please complete your payment in the browser, then return to this application.").pack(pady=10)
        ttk.Label(self.waiting_frame, text="This window will update automatically once confirmed.").pack(pady=10)

        # Add a cancel button to stop polling and go back
        cancel_button = ttk.Button(self.waiting_frame, text="Cancel Waiting", command=self.cancel_subscription_wait)
        cancel_button.pack(pady=20)

    def cancel_subscription_wait(self):
        self.polling_active = False # Signal the polling thread to stop
        if self.polling_thread and self.polling_thread.is_alive():
            print("Stopping polling thread...")
            # No direct way to stop a thread, but setting polling_active to False
            # will cause it to exit on its next loop iteration.
        self.check_subscription_status() # Re-evaluate status immediately

    def _poll_for_subscription_status(self, lookingForStatus):
        # This runs in a separate thread
        max_attempts = 60 # Poll for up to 60 seconds (1 second interval)
        attempt = 0
        while self.polling_active and attempt < max_attempts:
            try:
                response = requests.post(
                    f"{BASE_URL}/users/register_or_get_status",
                    json={
                        "google_user_id": self.current_google_user_id,
                        "user_email": self.user_profile.get('email')
                    }
                )
                response.raise_for_status()
                self.user_stripe_data = response.json()
                user_backend_data = self.user_stripe_data.get("user_data", {})
                current_is_subscribed = user_backend_data.get('is_subscribed', False)
    
                if current_is_subscribed == lookingForStatus:
                    # Subscription confirmed! Update UI on the main Tkinter thread
                    self.after(0, lambda: self._handle_polling_success(current_is_subscribed))
                    self.polling_active = False # Stop polling
                    return
    
                # print(f"Polling attempt {attempt+1}: Not subscribed yet.")
                time.sleep(1) # Wait for 1 second before next poll
                attempt += 1
    
            except requests.exceptions.RequestException as e:
                # print(f"Polling network error: {e}")
                # Don't stop polling immediately on network error, might be temporary
                time.sleep(5) # Wait longer on error
                attempt += 1 # Still count attempts
            except Exception as e:
                # print(f"Polling unexpected error: {e}")
                self.polling_active = False # Stop polling on unexpected error
                self.after(0, lambda: messagebox.showerror("Polling Error", f"An error occurred during subscription check: {e}"))
                return
    
        # If polling finishes without subscription, update UI on main thread
        if self.polling_active: # If it wasn't stopped by success, it timed out
            self.after(0, lambda: self._handle_polling_timeout())
        self.polling_active = False # Ensure it's marked inactive

    def _handle_polling_success(self, is_subscribed_status):
        # This runs on the main Tkinter thread
        self.is_subscribed = is_subscribed_status
        self.show_main_page() # Transition to main page

    def _handle_polling_timeout(self):
        # This runs on the main Tkinter thread
        messagebox.showinfo("Subscription Status", "Subscription not confirmed within expected time. Please check your Stripe account or try again.")
        self.show_subscribe_page() # Go back to subscribe page

    def show_main_page(self):
        for widget in self.winfo_children():
            widget.destroy()

        self.main_frame = ttk.Frame(self, padding="20")
        self.main_frame.pack(expand=True, fill="both")

        ttk.Label(self.main_frame, text=f"Welcome, {self.user_profile.get('name', 'User')}!", font=("Arial", 18, "bold")).pack(pady=20)
        # ttk.Label(self.main_frame, text=f"Email: {self.user_profile.get('email', 'N/A')}").pack(pady=5)
        # ttk.Label(self.main_frame, text=f"Google ID: {self.user_profile.get('id', 'N/A')}").pack(pady=5)
        ttk.Label(self.main_frame, text=f"Subscription Status: {'Active' if self.is_subscribed else 'Inactive'}", font=("Arial", 12)).pack(pady=10)
        
        if not self.is_subscribed:
            ttk.Label(self.main_frame, text="Please subscribe to access the main features.").pack(pady=10)

            subscribe_button = ttk.Button(self.main_frame, text="Subscribe Now", command=self.open_stripe_checkout)
            subscribe_button.pack(pady=20)
        
        # Optionally, a button to re-check status if they paid externally or on another device
        check_status_button = ttk.Button(self.main_frame, text="Refresh Subscription Status", command=self.check_subscription_status)
        check_status_button.pack(pady=10)
        
        if self.is_subscribed: # Link to Stripe Customer Portal (optional but highly recommended)
            manage_subscription_button = ttk.Button(self.main_frame, text="Cancel Subscription (Stripe Portal)", command=self.open_customer_portal)
            manage_subscription_button.pack(pady=10)
            # Button to close the Login app and open the BumbleBot app
            open_bumblebot_button = ttk.Button(self.main_frame, text="Open BumbleBot", command=self.open_bumble_bot_page)
            open_bumblebot_button.pack(pady=10)

        logout_button = ttk.Button(self.main_frame, text="Logout", command=self.logout)
        logout_button.pack(pady=20)

    def open_bumble_bot_page(self):
        self.open_bumble_bot = True
        self.destroy()

    def open_customer_portal(self):
        if not self.current_google_user_id:
            messagebox.showerror("Error", "User not logged in.")
            return

        customer_id = self.user_stripe_data.get("user_data", {}).get('stripe_customer_id')

        if not customer_id:
            messagebox.showinfo("Info", "You don't have a Stripe customer record yet. Please subscribe first.")
            return

        self.show_waiting_for_subscription_page()
        try:
            response = requests.post(f'{BASE_URL}/stripe/create-customer-portal-session', json={
                'google_user_id': self.current_google_user_id,
                'user_email': self.user_profile.get('email')
            })
            response.raise_for_status() # Raise an exception for HTTP errors
            session_data = response.json()
            portalSessionUrl = session_data.get('url')
            if portalSessionUrl:
                 # Create a Customer Portal session
                webbrowser.open_new(portalSessionUrl)
                # Start aggressive polling in a background thread
                self.show_waiting_for_subscription_page() # Show a waiting UI
                self.polling_active = True
                self.polling_thread = threading.Thread(target=self._poll_for_subscription_status, kwargs={'lookingForStatus': False}, daemon=True)
                self.polling_thread.start()
            else:
                messagebox.showerror("Stripe Error", "Could not get Stripe Portal Session URL.")
        except Exception as e:
            messagebox.showerror("Stripe Portal Error", f"Could not open customer portal: {e}")

    def logout(self):
        # Invalidate local Google token if it exists
        if os.path.exists(TOKEN_PATH):
            os.remove(TOKEN_PATH)
        
        # Clear user data for current session
        self.credentials = None
        self.user_profile = None
        self.current_google_user_id = None
        
        messagebox.showinfo("Logout", "Logged out successfully.")
        self.show_login_page()

    def periodic_subscription_check(self):
        if not self.winfo_exists(): # If our window is already destroyed we don't need to check anymore
            return
        if self.current_google_user_id:
            # This is a fallback. Webhooks are more reliable.
            # You'd ideally make an API call to Stripe to get the actual subscription status
            # based on self.current_google_user_id's stripe_customer_id and stripe_subscription_id.
            # print("Performing periodic subscription check...")
            self.check_subscription_status()
        self.after(300000, self.periodic_subscription_check) # Schedule next check


if __name__ == "__main__":
    app_instance = AuthUI()
    app_instance.mainloop()