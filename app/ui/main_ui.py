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

BASE_URL = 'https://bumblebot-460521.uc.r.appspot.com/'

class MainUI(tk.Toplevel):
    def __init__(self, parent, onDestroy, userProfile):
        super().__init__(parent)
        self.title("BumbleBot")
        self.geometry("1920x1080")
        self.iconbitmap(UM.resource_path("BumbleBotLogo.ico"))
        self.focus_set()
        
        self.selected_button = None
        self.selected_profile_path = None
        self.image_index = 0
        self.user_profile = userProfile

        self.settings = UM.load_settings()
        self.modelpath = os.path.normpath(self.settings.get("MODELPATH", ""))
        self.weightfolder = os.path.join(self.settings["BASE_DIR"], "weights")

        self.left_frame = tk.Frame(self, width=300)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y)

        self.right_frame = tk.Frame(self, bg="white")
        self.right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Fixed list without scrolling
        self.list_frame = tk.Frame(self.left_frame)
        self.list_frame.pack(fill=tk.BOTH, expand=True)

        self.create_button = tk.Button(self.list_frame, text="+ Create New Profile", command=self.create_new_profile, bg="lightblue")
        self.create_button.pack(fill=tk.X)

        self.profile_buttons = {}
        self.refresh_profile_buttons()
        self.get_back_to_auth = False
        # Bind to the <Destroy> event
        # This handler will be called *just before* the widget is fully destroyed
        self.bind("<Destroy>", onDestroy)
        # Periodically check subscription status (e.g., every 1 hour)
        # This is a fallback; webhooks are more immediate
        self.after(3600000, self.periodic_subscription_check)

    def periodic_subscription_check(self):
        if not self.winfo_exists(): # If our window is already destroyed we don't need to check anymore
            return
        if self.user_profile.get('id') and self.user_profile.get('email'):
            try:
                # Make a request to your Flask server to get customer information
                response = requests.post(f'{BASE_URL}/users/register_or_get_status', json={
                    'google_user_id': self.user_profile.get('id'),
                    'user_email': self.user_profile.get('email')
                })
                response.raise_for_status() # Raise an exception for HTTP errors
                user_stripe_data = response.json()
                is_subscribed = user_stripe_data.get('user_data',{}).get("is_subscribed", False)
                if not is_subscribed:
                    # Subscription expired, return to the auth page
                    self.get_back_to_auth = True
                    self.destroy()
            except Exception as e:
                messagebox.showerror("API Error", f"Could not fetch user profile: {e}")
        self.after(3600000, self.periodic_subscription_check) # Schedule next check

    def refresh_profile_buttons(self):
        self.selected_button = None
    
        for widget in self.list_frame.winfo_children():
            if isinstance(widget, tk.Button) and widget["text"] != "+ Create New Profile":
                widget.destroy()
        
        selected_name = os.path.splitext(os.path.basename(self.modelpath))[0]
    
        for fname in sorted(os.listdir(self.weightfolder)):
            if os.path.isdir(os.path.join(self.weightfolder, fname)):
                profile_name = fname
                full_path = os.path.join(self.weightfolder, fname, f"{fname}.h5")
                b = tk.Button(self.list_frame, text=profile_name, anchor="w",
                              command=lambda f=full_path, b=profile_name: self.select_profile(f, b))
                b.pack(fill=tk.X)
                self.profile_buttons[profile_name] = b
    
                if profile_name == selected_name:
                    self.select_profile(full_path, profile_name, init=True)

    def clear_right_panel(self):
        for widget in self.right_frame.winfo_children():
            widget.destroy()

    def update_right_panel(self, path):
        self.clear_right_panel()

        if not path or not os.path.exists(path):
            return

        profile_name = os.path.splitext(os.path.basename(self.selected_profile_path))[0]
        btn_config = {"font": ("Arial", 14), "width": 12, "height": 2, "bg": "#4CAF50", "fg": "white"}
        delete_btn_config = {"font": ("Arial", 14), "width": 12, "height": 2, "bg": "#AF4C4C", "fg": "white"}
        if os.path.getsize(path) == 0:
            msg = tk.Label(self.right_frame, text=f"New profile {profile_name}, start by building your preferences", bg="white", font=("Arial", 18))
            msg.place(relx=0.5, rely=0.4, anchor="center")
            train_button = tk.Button(self.right_frame, text="Train", **btn_config, command=self.open_trainer_window)
            train_button.place(relx=0.5, rely=0.5, anchor="center")
            tk.Button(self.right_frame, text="Delete Profile", **delete_btn_config, command=self.click_delete).place(relx=0.5, rely=0.6, anchor="center")
        else:
            center_wrapper = tk.Frame(self.right_frame, bg="white")
            center_wrapper.pack(expand=True)
            msg = tk.Label(center_wrapper, text=f"Hello {profile_name}", bg="white", font=("Arial", 18)).pack(pady=10, anchor="center")
            
            tk.Button(center_wrapper, text="Train", **btn_config, command=self.open_trainer_window).pack(pady=10, anchor="center")
            tk.Button(center_wrapper, text="Swipe", **btn_config, command=self.run_swipe).pack(pady=10, anchor="center")
            tk.Button(center_wrapper, text="Review", **btn_config, command=self.open_review_panel).pack(pady=10, anchor="center")
            tk.Button(center_wrapper, text="Delete Profile", **delete_btn_config, command=self.click_delete).pack(pady=20, anchor="center")

    def open_review_panel(self):
        ReviewPanel(self)  # Pass the main window as parent
    
    def run_swipe(self):
        print("Running swipe...")
        MP.make_predictions()

    def open_trainer_window(self):
        TrainPanel(self)  # Pass the main window as parent

    def select_profile(self, full_path, profile_name, init=False):
        full_path = os.path.normpath(full_path)
        if self.selected_button:
            self.selected_button.config(bg="SystemButtonFace")

        button = self.profile_buttons.get(profile_name)
        if button:
            button.config(bg="lightgreen")
            self.selected_button = button

        self.selected_profile_path = full_path
        self.settings["MODELPATH"] = full_path[len(self.settings["BASE_DIR"])+1:]
        self.settings["DATA_INDEX"] = os.path.splitext(self.settings["MODELPATH"])[0] + ".csv"
        self.settings["PROFILEPATH"] = os.path.dirname(full_path)[len(self.settings["BASE_DIR"])+1:]
        with open(os.path.join(self.settings["BASE_DIR"], "configs", "settings.json"), "w") as f:
            json.dump(self.settings, f, indent=4)

        self.update_right_panel(full_path)
        if not init:
            print(f"Selected model path: {full_path}")

    def create_new_profile(self):
        name = simpledialog.askstring("New Profile", "Enter profile name:")
        if name:
            full_name = name + ".h5"
            full_path = os.path.normpath(os.path.join(self.weightfolder, name, full_name))
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            open(full_path, "a").close()
            self.refresh_profile_buttons()
            self.select_profile(full_path, name)
    
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
        with open(os.path.join(self.settings["BASE_DIR"], "configs", "settings.json"), "w") as f:
            json.dump(self.settings, f, indent=4)

        self.clear_right_panel()
        self.refresh_profile_buttons()

def count_pngs(folder_path):
    return len([f for f in os.listdir(folder_path) if f.lower().endswith('.png')])