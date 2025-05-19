import tkinter as tk
from tkinter import simpledialog
from tkinter.ttk import Progressbar
from tkinter import filedialog
from tkinter import Scale
import os
import io
import sys
import json
import csv
from automation import makePredictions as MP
from model import machineLearning as ML
from utils import utilities as UM
import threading
from tkinter.scrolledtext import ScrolledText
from PIL import Image, ImageTk
import pandas as pd
from pathlib import Path
from ui.reviewPanel import ReviewPanel

BASE_DIR = Path(__file__).resolve().parent.parent

SETTINGS_PATH = (BASE_DIR / "config" / "settings.json").resolve()
WEIGHT_FOLDER = (BASE_DIR / "weights").resolve()

class MainUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Weight Profile Selector")
        self.geometry("1920x1080")

        self.selected_button = None
        self.selected_profile_path = None
        self.image_index = 0

        with open(SETTINGS_PATH, "r") as f:
            self.settings = json.load(f)
        self.modelpath = os.path.normpath(self.settings.get("MODELPATH", ""))
        self.ground_truth = pd.read_csv(os.path.join(self.settings.get("INIT_DATA_PATH", ""), "init_data.csv"))

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


    def refresh_profile_buttons(self):
        self.selected_button = None
    
        for widget in self.list_frame.winfo_children():
            if isinstance(widget, tk.Button) and widget["text"] != "+ Create New Profile":
                widget.destroy()
        
        selected_name = os.path.splitext(os.path.basename(self.modelpath))[0]
    
        for fname in sorted(os.listdir(WEIGHT_FOLDER)):
            if os.path.isdir((WEIGHT_FOLDER / fname).resolve()):
                profile_name = fname
                full_path = (WEIGHT_FOLDER / fname / f"{fname}.h5").resolve()
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
        if os.path.getsize(path) == 0:
            msg = tk.Label(self.right_frame, text=f"New profile {profile_name}, start by building your preferences", bg="white", font=("Arial", 18))
            msg.place(relx=0.5, rely=0.4, anchor="center")
            train_button = tk.Button(self.right_frame, text="Train", font=("Arial", 14), width=12, height=2, bg="#4CAF50", fg="white", command=self.open_trainer_window)
            train_button.place(relx=0.5, rely=0.5, anchor="center")
        else:
            center_wrapper = tk.Frame(self.right_frame, bg="white")
            center_wrapper.pack(expand=True)
            msg = tk.Label(center_wrapper, text=f"Hello {profile_name}", bg="white", font=("Arial", 18)).pack(pady=10, anchor="center")
            btn_config = {"font": ("Arial", 14), "width": 12, "height": 2, "bg": "#4CAF50", "fg": "white"}
            tk.Button(center_wrapper, text="Train", **btn_config, command=self.open_trainer_window).pack(pady=10, anchor="center")
            tk.Button(center_wrapper, text="Swipe", **btn_config, command=self.run_swipe).pack(pady=10, anchor="center")
            tk.Button(center_wrapper, text="Review", **btn_config, command=self.open_review_panel).pack(pady=10, anchor="center")

    def open_review_panel(self):
        ReviewPanel(self)  # Pass the main window as parent
    
    def run_swipe(self):
        print("Running swipe...")
        MP.make_predictions()

    def load_image_to_label(self, label_widget, image_path, fixed_height=300):
        try:
            image = Image.open(image_path).convert("RGB")
    
            # Calculate new width while maintaining aspect ratio
            width, height = image.size
            aspect_ratio = width / height
            new_height = fixed_height
            new_width = int(aspect_ratio * new_height)
    
            resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            tk_image = ImageTk.PhotoImage(resized_image)
    
            # Store a reference to avoid garbage collection
            label_widget.image = tk_image
            label_widget.config(image=tk_image)
        except Exception as e:
            print(f"[ERROR] Failed to load image {image_path}: {e}")

    def open_trainer_window(self):
        self.cancel_training = False
        self.training_in_progress = False
        self.trainer_win = tk.Toplevel(self)
        self.trainer_win.title("Trainer")
        self.trainer_win.geometry("800x600")
        self.trainer_win.grab_set()
    
        settings = UM.load_settings()
        self.data_index_path = os.path.normpath(settings["DATA_INDEX"])
        
        # Create index data if not available
        if not os.path.exists(self.data_index_path):
            with open(self.data_index_path, "w") as file:
                writer = csv.writer(file)
                writer.writerow(["image","outcome","race_scores","obese_scores"])
        
        df = pd.read_csv(self.data_index_path)
        # load the image where we last time left off
        self.image_index = df.shape[0]            

        tk.Label(self.trainer_win, text="Trainer", font=("Arial", 20)).pack(pady=10)
    
        # Main frame for everything
        top_frame = tk.Frame(self.trainer_win)
        top_frame.pack(pady=10)
    
        # Previous Button
        previous_button = tk.Frame(top_frame)
        previous_button.pack(side=tk.LEFT, padx=10)
        self.prev_button = tk.Button(previous_button, text="Previous", font=("Arial", 12), command=self.handle_prev_button)
        self.prev_button.pack(pady=20)

        # Image + slider vertical frame
        center_column = tk.Frame(top_frame)
        center_column.pack(side=tk.LEFT, padx=10)
    
        self.attr_slider = Scale(center_column, from_=-1, to=1, resolution=0.1, orient="horizontal", label="Attractiveness", length=100)
        self.attr_slider.set(0)
        self.attr_slider.pack(pady=5, anchor="center")
    
        self.image_label = tk.Label(center_column)
        self.image_label.pack(pady=5, anchor="center")
    
        # Load image into label
        image_path = os.path.join(settings['INIT_DATA_PATH'], f"{self.image_index}.png")
        if self.image_index == count_pngs(settings['INIT_DATA_PATH']):
            image_path = Path(BASE_DIR / "images" / "ui" / "AllDone.png").resolve()
        
        self.load_image_to_label(self.image_label, image_path)
        
        # Next Button
        next_button = tk.Frame(top_frame)
        next_button.pack(side=tk.LEFT, padx=10)
        self.next_button = tk.Button(next_button, text="Confirm & Next", font=("Arial", 12), command=self.handle_next_button)
        self.next_button.pack(pady=20)
        if self.image_index == count_pngs(self.settings.get('INIT_DATA_PATH', '')):
            self.next_button.config(state=tk.DISABLED)
        if self.image_index == 0:
            self.prev_button.config(state=tk.DISABLED)
        # Bottom frame for train/cancel
        self.button_frame = tk.Frame(self.trainer_win)
        self.button_frame.pack(pady=10)
    
        self.train_button = tk.Button(self.button_frame, text="Train", font=("Arial", 12), width=10, command=self.handle_train_or_cancel)
        self.train_button.pack(side=tk.LEFT, padx=10)
    
        return_button = tk.Button(self.button_frame, text="Return", font=("Arial", 12), width=10, command=lambda: self.close_trainer(self.trainer_win))
        return_button.pack(side=tk.LEFT, padx=10)
    
        self.progress_bar = None
        self.epoch_label = None

        # Accuracy selection
        accuracy_frame = tk.Frame(self.trainer_win)
        accuracy_frame.pack(pady=10)

        tk.Label(accuracy_frame, text="Training Accuracy:", font=("Arial", 12)).pack(side=tk.LEFT, padx=5)

        self.accuracy_var = tk.StringVar(value="Moderate")
        accuracy_options = ["Accurate", "Moderate", "Basic", "Custom"]
        self.accuracy_menu = tk.OptionMenu(accuracy_frame, self.accuracy_var, *accuracy_options, command=self.handle_accuracy_selection)
        self.accuracy_menu.config(width=10)
        self.accuracy_menu.pack(side=tk.LEFT)

        # Custom epoch entry (only visible if "Custom" is selected)
        self.custom_epoch_entry = tk.Entry(accuracy_frame, width=5)
        self.custom_epoch_entry.insert(0, "100")  # default
        self.custom_epoch_entry.pack(side=tk.LEFT, padx=5)
        self.custom_epoch_entry.pack_forget()  # hidden initially

    def handle_accuracy_selection(self, value):
        if value == "Custom":
            self.custom_epoch_entry.pack(side=tk.LEFT, padx=5)
        else:
            self.custom_epoch_entry.pack_forget()

    def handle_prev_button(self):
        if self.image_index <= 0:
            return
        self.image_index -= 1
        image_path = os.path.join(f"{self.settings.get('INIT_DATA_PATH', '')}", f"{self.image_index}.png")
        self.load_image_to_label(self.image_label, image_path)
        # Read the row value and restore value
        df = pd.read_csv(self.data_index_path)
        stored_attractiveness = df.loc[df["image"] == f"{self.image_index}.png"].iloc[0].to_dict()["outcome"]
        self.attr_slider.set(stored_attractiveness)
        self.next_button.config(state=tk.NORMAL)
        if self.image_index == 0:
            self.prev_button.config(state=tk.DISABLED)

    def handle_next_button(self):
        # Write the current slider value into csv
        row_dict = self.ground_truth.loc[self.ground_truth["image"] == f"{self.image_index}.png"].iloc[0].to_dict()
        df = pd.read_csv(self.data_index_path)
        match = df["image"] == f"{self.image_index}.png"
        if match.any():
            # Update row if already exist
            df.loc[match, "image"] = row_dict["image"]
            df.loc[match, "outcome"] = self.attr_slider.get()
            df.loc[match, "race_scores"] = row_dict["race_scores"]
            df.loc[match, "obese_scores"] = row_dict["obese_scores"]
        else:
            # Append a new row
            new_row = {
                "image": row_dict["image"],
                "outcome": self.attr_slider.get(),
                "race_scores": row_dict["race_scores"],
                "obese_scores": row_dict["obese_scores"]
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        # Save the updated DataFrame back to the CSV
        df.to_csv(self.data_index_path, index=False)

        self.image_index += 1
        image_path = os.path.join(f"{self.settings.get('INIT_DATA_PATH', '')}", f"{self.image_index}.png")
        self.prev_button.config(state=tk.NORMAL)
        if self.image_index == count_pngs(self.settings.get('INIT_DATA_PATH', '')):
            self.next_button.config(state=tk.DISABLED)
            image_path = Path(BASE_DIR / "images" / "ui" / "AllDone.png").resolve()
        self.load_image_to_label(self.image_label, image_path)
        match = df["image"] == f"{self.image_index}.png"
        if match.any():
            # Load the previous value if it has been set
            self.attr_slider.set(float(df.loc[match, "outcome"]))
        else:
            self.attr_slider.set(0)

    def handle_train_or_cancel(self):
        if not self.training_in_progress:
            self.training_in_progress = True
            self.cancel_training = False
            self.train_button.config(text="Cancel")

            self.progress_bar = Progressbar(self.trainer_win, orient="horizontal", length=500, mode="determinate")
            self.progress_bar.pack(pady=(20, 5))
            self.epoch_label = tk.Label(self.trainer_win, text="", font=("Arial", 12))
            self.epoch_label.pack(pady=(0, 10))
            self.prev_button.pack_forget()
            self.next_button.pack_forget()
            self.attr_slider.pack_forget()
            self.image_label.pack_forget()
            threading.Thread(target=self.run_training_with_progress, daemon=True).start()
        else:
            self.prev_button.pack()
            self.next_button.pack()
            self.attr_slider.pack()
            self.image_label.pack()
            self.cancel_training = True
            self.train_button.config(state=tk.DISABLED)


    def run_training_with_progress(self):
        settings = UM.load_settings()
        ML.init_models()

        train_loader, _ = ML.construct_dataset(
            os.path.normpath(settings["DATA_INDEX"]),
            os.path.normpath(settings["INIT_DATA_PATH"]),
            int(settings["IMG_SIZE"]),
            int(settings["BATCH_SIZE"]),
            float(settings["TTS"])
        )

        total_epochs = 200
        model_path = os.path.normpath(settings["MODELPATH"])

        accuracy_choice = self.accuracy_var.get()
        if accuracy_choice == "Accurate (500 epochs)":
            total_epochs = 500
        elif accuracy_choice == "Moderate (200 epochs)":
            total_epochs = 200
        elif accuracy_choice == "Basic (100 epochs)":
            total_epochs = 100
        elif accuracy_choice == "Custom":
            try:
                total_epochs = int(self.custom_epoch_entry.get())
            except ValueError:
                total_epochs = 100  # fallback default
        else:
            total_epochs = 200  # fallback default

        self.trainer_win.after(0, lambda: self.progress_bar.config(maximum=total_epochs))

        def log_progress(epoch):
            self.trainer_win.after(0, lambda: self.progress_bar.config(value=epoch - 1))
            self.trainer_win.after(0, lambda: self.epoch_label.config(text=f"Epoch {epoch} / {total_epochs} (it takes around 1 minute for each epoch)"))

        ML.train_classifier_with_metadata(
            train_loader=train_loader,
            num_epochs=total_epochs,
            image_size=int(settings["IMG_SIZE"]),
            model_path=model_path,
            cancel_flag=lambda: self.cancel_training,
            progress_callback=log_progress
        )

        self.trainer_win.after(0, self.training_finished)
    
    def training_finished(self):
        self.training_in_progress = False
        self.train_button.config(text="Train", state=tk.NORMAL)
        self.prev_button.pack()
        self.next_button.pack()
        self.attr_slider.pack()
        self.image_label.pack()
        if self.progress_bar:
            self.progress_bar.destroy()
            self.progress_bar = None

        if self.epoch_label:
            self.epoch_label.destroy()
            self.epoch_label = None

    def close_trainer(self, window):
        window.grab_release()
        window.destroy()

    def select_profile(self, full_path, profile_name, init=False):
        full_path = os.path.normpath(full_path)
        if self.selected_button:
            self.selected_button.config(bg="SystemButtonFace")

        button = self.profile_buttons.get(profile_name)
        if button:
            button.config(bg="lightgreen")
            self.selected_button = button

        self.selected_profile_path = full_path
        self.settings["MODELPATH"] = full_path
        self.settings["DATA_INDEX"] = os.path.splitext(full_path)[0] + ".csv"
        self.settings["PROFILEPATH"] = os.path.dirname(full_path)
        with open(SETTINGS_PATH, "w") as f:
            json.dump(self.settings, f, indent=4)

        self.update_right_panel(full_path)
        if not init:
            print(f"Selected model path: {full_path}")

    def create_new_profile(self):
        name = simpledialog.askstring("New Profile", "Enter profile name:")
        if name:
            full_name = name + ".h5"
            full_path = os.path.normpath(os.path.join(WEIGHT_FOLDER, name, full_name))
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            open(full_path, "a").close()
            self.refresh_profile_buttons()
            self.select_profile(full_path, name)

def count_pngs(folder_path):
    return len([f for f in os.listdir(folder_path) if f.lower().endswith('.png')])

if __name__ == "__main__":
    if not os.path.exists(WEIGHT_FOLDER):
        os.makedirs(WEIGHT_FOLDER)

    app = MainUI()
    app.mainloop()
