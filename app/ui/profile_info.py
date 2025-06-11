import tkinter as tk
import os
import shutil
from ui.trainPanel import TrainPanel
from ui.reviewPanel import ReviewPanel
from automation import makePredictions as MP
import json
from utils import utilities as UM
from utils.utilities import center_window

class ProfileInfoPage(tk.Frame):
    def __init__(self, parent, profile_path, on_back):
        super().__init__(parent, bg="#a259c6")  # Match AuthUI theme
        self.profile_path = profile_path
        self.on_back = on_back
        card = tk.Frame(self, bg="white", bd=0, highlightthickness=0)
        card.place(relx=0.5, rely=0.5, anchor="center", width=420, height=600)
        # Modern circular user icon
        icon_canvas = tk.Canvas(card, width=90, height=90, bg="white", highlightthickness=0)
        icon_canvas.place(relx=0.5, rely=0.0, anchor="n", y=18)
        icon_canvas.create_oval(5, 5, 85, 85, fill="#a259c6", outline="")
        icon_canvas.create_text(45, 45, text="👤", font=("Arial", 44, "bold"), fill="white")
        # Back button
        back_btn = tk.Button(card, text="← Back", font=("Arial", 12), bg="#e9eef6", relief="flat", command=self.on_back, cursor="hand2")
        back_btn.place(relx=0.02, rely=0.01, anchor="nw")
        self.right_frame = card  # For compatibility with update_right_panel
        self.update_right_panel(profile_path)

    def update_right_panel(self, path):
        for widget in self.right_frame.winfo_children():
            if isinstance(widget, tk.Button) and widget.cget('text').startswith('← Back'):
                continue  # Don't destroy the back button
            if isinstance(widget, tk.Canvas):
                continue  # Don't destroy the icon
            widget.destroy()
        if not path or not os.path.exists(path):
            return
        profile_name = os.path.splitext(os.path.basename(path))[0]
        btn_config = {"font": ("Arial", 14, "bold"), "width": 16, "height": 2, "bg": "#4CAF50", "fg": "white", "relief": "flat", "bd": 0, "cursor": "hand2"}
        delete_btn_config = {"font": ("Arial", 14, "bold"), "width": 16, "height": 2, "bg": "#AF4C4C", "fg": "white", "relief": "flat", "bd": 0, "cursor": "hand2"}
        if os.path.getsize(os.path.join(path, f"{profile_name}.h5")) == 0:
            # Modern title and subtitle
            tk.Label(self.right_frame, text=f"New profile", bg="white", font=("Arial", 20, "bold"), fg="#222").place(relx=0.5, rely=0.36, anchor="center")
            tk.Label(self.right_frame, text=f"Start by building your preferences", bg="white", font=("Arial", 12), fg="#888").place(relx=0.5, rely=0.44, anchor="center")
            # Modern buttons
            train_button = tk.Button(self.right_frame, text="AI Learn", **btn_config, command=self.open_trainer_window)
            train_button.place(relx=0.5, rely=0.58, anchor="center")
            tk.Button(self.right_frame, text="Delete Profile", **delete_btn_config, command=self.click_delete).place(relx=0.5, rely=0.74, anchor="center")
        else:
            center_wrapper = tk.Frame(self.right_frame, bg="white")
            center_wrapper.place(relx=0.5, rely=0.5, anchor="center")
            tk.Label(center_wrapper, text=f"Hello {profile_name}", bg="white", font=("Arial", 20, "bold"), fg="#222").pack(pady=(0, 6), anchor="center")
            tk.Label(center_wrapper, text="Manage your profile and preferences", bg="white", font=("Arial", 12), fg="#888").pack(pady=(0, 18), anchor="center")
            tk.Button(center_wrapper, text="AI Learn", **btn_config, command=self.open_trainer_window).pack(pady=6, anchor="center")
            tk.Button(center_wrapper, text="Auto Swipe", **btn_config, command=self.run_swipe).pack(pady=6, anchor="center")
            tk.Button(center_wrapper, text="Results Review", **btn_config, command=self.open_review_panel).pack(pady=6, anchor="center")
            tk.Button(center_wrapper, text="Delete Profile", **delete_btn_config, command=self.click_delete).pack(pady=16, anchor="center")

    def open_review_panel(self):
        self.master.open_review_panel()
    def run_swipe(self):
        self.master.run_swipe()
    def open_trainer_window(self):
        self.master.show_train_panel(self.profile_path)
    def click_delete(self):
        confirm = tk.Toplevel(self)
        confirm.title("Delete Profile?")
        confirm.geometry("340x180")
        confirm.transient(self)
        confirm.grab_set()
        confirm.resizable(False, False)
        confirm.configure(bg="#faf9fb")
        # Set the icon for the popup
        confirm.iconbitmap(UM.resource_path("BumbleBotLogo.ico"))
        center_window(confirm, self, width=340, height=180)
        # Card frame for rounded look
        card = tk.Frame(confirm, bg="white", bd=0, highlightthickness=0)
        card.place(relx=0.5, rely=0.5, anchor="center", width=320, height=140)
        # Title
        tk.Label(card, text="Delete Profile?", font=("Arial", 16, "bold"), bg="white", fg="#AF4C4C").pack(pady=(18, 6))
        # Subtitle
        tk.Label(card, text="Are you sure you want to delete this profile?", font=("Arial", 12), bg="white", fg="#444").pack(pady=(0, 16))
        # Modern buttons
        btn_frame = tk.Frame(card, bg="white")
        btn_frame.pack(pady=0)
        def do_delete():
            # Only delete the profile folder, never the weights root
            weights_dir = os.path.abspath(os.path.join(self.profile_path, "..", ".."))
            profile_folder = os.path.abspath(self.profile_path)
            print(f"[DEBUG] Deleting profile folder {profile_folder}")
            shutil.rmtree(profile_folder)
            confirm.destroy()
            self.on_back()
        yes_btn = tk.Button(btn_frame, text="Delete", width=10, font=("Arial", 12, "bold"), command=do_delete, bg="#AF4C4C", fg="white", relief="flat", bd=0, cursor="hand2", activebackground="#d9534f")
        yes_btn.pack(side=tk.LEFT, padx=10, ipadx=6, ipady=4)
        no_btn = tk.Button(btn_frame, text="Cancel", width=10, font=("Arial", 12, "bold"), command=confirm.destroy, bg="#e9eef6", fg="#222", relief="flat", bd=0, cursor="hand2", activebackground="#d1d5db")
        no_btn.pack(side=tk.LEFT, padx=10, ipadx=6, ipady=4) 