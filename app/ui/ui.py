import tkinter as tk
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

    def on_open_main_ui(self):
        if self.auth_window:
            self.auth_window.destroy()
            self.auth_window = None
        self.create_or_display_main_ui()

    def on_auth_window_closed(self):
        if self.auth_window:
            self.auth_window.destroy()
            self.auth_window = None
        if self.main_ui_window is None:
            self.quit()

    def create_or_display_auth_window(self):
        if self.auth_window is None or not self.auth_window.winfo_exists():
            self.auth_window = AuthUI(self, on_open_main_ui=self.on_open_main_ui)
            self.auth_window.protocol("WM_DELETE_WINDOW", self.on_auth_window_closed)
        self.auth_window.deiconify()
        self.auth_window.lift()

    def on_main_ui_window_destroy(self, event=None):
        if self.main_ui_window:
            self.main_ui_window = None
        if self.main_ui_window and self.main_ui_window.get_back_to_auth:
            self.create_or_display_auth_window()

    def on_main_ui_window_closed(self):
        if self.main_ui_window:
            self.main_ui_window.destroy()
            self.main_ui_window = None
        if self.auth_window is None:
            self.quit()

    def create_or_display_main_ui(self):
        print("[DEBUG] create_or_display_main_ui called")
        # Create the main UI window if it doesn't exist
        if self.main_ui_window is None or not self.main_ui_window.winfo_exists():
            print("[DEBUG] Creating MainUI window")
            self.main_ui_window = MainUI(self, onDestroy=self.on_main_ui_window_destroy)
            self.main_ui_window.protocol("WM_DELETE_WINDOW", self.on_main_ui_window_closed)
        self.main_ui_window.deiconify() # Show the main UI window
        self.main_ui_window.lift() # Bring to front
        