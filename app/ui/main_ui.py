import tkinter as tk
from tkinter import simpledialog
from tkinter import messagebox
import os
import json
from tkinter import ttk
import requests
from ui.trainPanel import TrainPanel
from automation import makePredictions as MP
from utils import utilities as UM
from ui.reviewPanel import ReviewPanel
import shutil
from ui.profile_selection import ProfileSelectionPage
from ui.profile_info import ProfileInfoPage
from ui.swipe_composite import SwipeCompositePage

BASE_URL = 'https://bumblebot-460521.uc.r.appspot.com'

class MainUI(tk.Toplevel):
    def __init__(self, parent, onDestroy):
        super().__init__(parent)
        self.title("BumbleBot")
        self.geometry("950x750")
        self.resizable(False, False)
        self.iconbitmap(UM.resource_path("BumbleBotLogo.ico"))
        self.focus_set()

        self.configure(bg="#a259c6")  # Match AuthUI theme

        print(f"[DEBUG] MainUI initialized")

        self.selected_button = None
        self.selected_profile_path = None
        self.image_index = 0

        self.settings = UM.load_settings()
        self.modelpath = os.path.normpath(self.settings.get("MODELPATH", ""))
        self.weightfolder = os.path.join(self.settings["BASE_DIR"], "weights")

        self.profile_buttons = {}
        self.get_back_to_auth = False
        self.bind("<Destroy>", onDestroy)
        self.after(3600000, self.periodic_subscription_check)

        self.current_page = None
        if not self.selected_profile_path or not os.path.exists(self.selected_profile_path):
            self.show_profile_prompt()
        else:
            self.show_profile_info_page(self.selected_profile_path)

    def periodic_subscription_check(self):
        if not self.winfo_exists(): # If our window is already destroyed we don't need to check anymore
            return
        # No Google user profile logic here
        self.after(3600000, self.periodic_subscription_check) # Schedule next check

    def show_profile_prompt(self):
        if self.current_page:
            self.current_page.destroy()
        self.current_page = ProfileSelectionPage(self, self.weightfolder, self.modelpath, self.on_profile_selected)
        self.current_page.pack(fill=tk.BOTH, expand=True)

    def save_settings(self):
        """Save the current settings to settings.json"""
        with open(os.path.join(self.settings["BASE_DIR"], "configs", "settings.json"), "w") as f:
            json.dump(self.settings, f, indent=4)

    def show_profile_info_page(self, profile_path):
        # Update PROFILEPATH, MODELPATH, and DATA_INDEX in settings to the selected profile's relative path
        rel_profile_path = os.path.relpath(profile_path, self.settings["BASE_DIR"])
        profile_name = os.path.basename(profile_path)
        self.settings["PROFILEPATH"] = rel_profile_path
        self.settings["MODELPATH"] = os.path.join(rel_profile_path, f"{profile_name}.h5")
        self.settings["DATA_INDEX"] = os.path.join(rel_profile_path, f"{profile_name}.csv")
        self.save_settings()
        if self.current_page:
            self.current_page.destroy()
        self.current_page = ProfileInfoPage(self, profile_path, self.show_profile_prompt)
        self.current_page.pack(fill=tk.BOTH, expand=True)

    def on_profile_selected(self, profile_path):
        self.selected_profile_path = profile_path
        self.show_profile_info_page(profile_path)

    def open_review_panel(self):
        if self.current_page:
            self.current_page.destroy()
        def back_to_profile_info():
            self.show_profile_info_page(self.selected_profile_path)
        self.current_page = ReviewPanel(self, on_back=back_to_profile_info)
        self.current_page.pack(fill=tk.BOTH, expand=True)
    
    def run_swipe(self):
        """Start the swiping process"""
        self.show_swipe_status_page()

    def show_swipe_status_page(self):
        """Show the swipe status page with embedded browser and maximize window"""
        if self.current_page:
            self.current_page.destroy()
        self.original_geometry = self.geometry()
        # self.state('zoomed')  # Maximize window (Windows)
        self.current_page = SwipeCompositePage(self, self._on_return_to_profile_info)
        self.current_page.pack(side=tk.LEFT, anchor='n', fill=tk.BOTH, expand=False)

    def _on_return_to_profile_info(self):
        # Restore window size and go back to profile info
        if hasattr(self, 'original_geometry'):
            self.geometry(self.original_geometry)
        if self.selected_profile_path:
            self.show_profile_info_page(self.selected_profile_path)

    def _on_swipe_continue(self):
        if hasattr(self, '_swipe_continue_callback'):
            self._swipe_continue_callback()

    def _on_swipe_stop(self):
        if hasattr(self, '_swipe_stop_callback'):
            self._swipe_stop_callback()
        # Optionally, return to profile info page
        if self.selected_profile_path:
            self.show_profile_info_page(self.selected_profile_path)

    def _start_swipe_process(self):
        import threading
        from automation import makePredictions as MP
        # This function will be called from the swiping backend to update status
        def set_status(text):
            self.swipe_status_page.set_status(text)
        def show_continue():
            self.swipe_status_page.show_continue()
        def show_stop():
            self.swipe_status_page.show_stop()
        # These will be called by the backend
        self._swipe_continue_callback = None
        self._swipe_stop_callback = None
        def swipe_thread():
            MP.make_predictions(
                set_status=set_status,
                show_continue=show_continue,
                show_stop=show_stop,
                set_continue_callback=lambda cb: setattr(self, '_swipe_continue_callback', cb),
                set_stop_callback=lambda cb: setattr(self, '_swipe_stop_callback', cb),
            )
        threading.Thread(target=swipe_thread, daemon=True).start()

    def open_trainer_window(self):
        TrainPanel(self)  # Pass the main window as parent

    def click_delete(self):
        profile_name = os.path.basename(self.settings["PROFILEPATH"])
        delete_confirm_page = tk.Toplevel(self)
        delete_confirm_page.title(f"Delete {profile_name}?")
        delete_confirm_page.geometry("300x100")
        delete_confirm_page.iconbitmap(UM.resource_path("BumbleBotLogo.ico"))
        delete_confirm_page.resizable(False, False)
        delete_confirm_page.focus_set()
        delete_confirm_page.grab_set()

        button_frame = ttk.Frame(delete_confirm_page)
        button_frame.pack(side=tk.TOP, pady=30)
        tk.Button(button_frame, text="Yes", width=10, command=self.delete_profile, bg='red').pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="No", width=10, command=delete_confirm_page.destroy).pack(side=tk.LEFT, padx=5)

    def delete_profile(self):
        profile_name = os.path.basename(self.settings["PROFILEPATH"])
        del self.profile_buttons[profile_name]
        self.selected_button.destroy()
        shutil.rmtree(os.path.join(self.settings["BASE_DIR"],self.settings["PROFILEPATH"]))
        self.settings["MODELPATH"] = ""
        self.settings["DATA_INDEX"] = ""
        self.settings["PROFILEPATH"] = ""
        self.save_settings()
        self.refresh_profile_buttons()

    def show_train_panel(self, profile_path):
        # Update PROFILEPATH, MODELPATH, and DATA_INDEX in settings to the selected profile's relative path
        rel_profile_path = os.path.relpath(profile_path, self.settings["BASE_DIR"])
        profile_name = os.path.basename(profile_path)
        self.settings["PROFILEPATH"] = rel_profile_path
        self.settings["MODELPATH"] = os.path.join(rel_profile_path, f"{profile_name}.h5")
        self.settings["DATA_INDEX"] = os.path.join(rel_profile_path, f"{profile_name}.csv")
        self.save_settings()
        if self.current_page:
            self.current_page.destroy()
        def back_to_profile_info():
            self.show_profile_info_page(profile_path)
        self.current_page = TrainPanel(self, on_back=back_to_profile_info)
        self.current_page.pack(fill=tk.BOTH, expand=True)

    def clear_right_panel(self):
        if hasattr(self, 'right_panel') and self.right_panel is not None:
            try:
                self.right_panel.destroy()
            except Exception:
                pass
            self.right_panel = None

def count_pngs(folder_path):
    return len([f for f in os.listdir(folder_path) if f.lower().endswith('.png')])