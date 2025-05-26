import tkinter as tk
from tkinter import ttk, messagebox
from ui.main_ui import MainUI
from ui.auth_ui import AuthUI

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Main Application Orchestrator")
        # Start hidden, as AuthToplevel will be the first visible window
        self.withdraw()

        self.auth_window = None
        self.main_ui_window = None

        # Create and show the authentication window first
        self.create_or_display_auth_window()

    def on_auth_window_destroy(self, event=None):
        # Check if we are going to BumbleBot Main Page
        if self.auth_window.open_bumble_bot:
            self.create_or_display_main_ui()

    def on_auth_window_closed(self):
        if self.auth_window:
            self.auth_window.destroy() # Still destroy the window
        self.quit()

    def create_or_display_auth_window(self):
        # Only create if it doesn't exist or was destroyed
        if self.auth_window is None or not self.auth_window.winfo_exists():
            self.auth_window = AuthUI(self, onDestroy=self.on_auth_window_destroy)
            self.auth_window.protocol("WM_DELETE_WINDOW", self.on_auth_window_closed)
        self.auth_window.deiconify() # Ensure it's visible
        self.auth_window.lift() # Bring to front

    def on_main_ui_window_destroy(self, event=None):
        if self.main_ui_window.get_back_to_auth:
            self.create_or_display_auth_window()

    def on_main_ui_window_closed(self):
        if self.auth_window:
            self.auth_window.destroy() # Still destroy the window
        self.quit()

    def create_or_display_main_ui(self):
        # Create the main UI window if it doesn't exist
        if self.main_ui_window is None or not self.main_ui_window.winfo_exists():
            self.main_ui_window = MainUI(self, userProfile=self.auth_window.user_profile, onDestroy=self.on_main_ui_window_destroy)
            self.main_ui_window.protocol("WM_DELETE_WINDOW", self.on_main_ui_window_closed)
        else:
            self.main_ui_window.user_profile = self.auth_window.user_profile
        self.main_ui_window.deiconify() # Show the main UI window
        self.main_ui_window.lift() # Bring to front
        