import tkinter as tk
from utils import utilities as UM
import os
import csv
import pandas as pd
from tkinter import Scale
from PIL import Image, ImageTk
from tkinter.ttk import Progressbar
import threading
from model import machineLearning as ML

def count_pngs(folder_path):
    return len([f for f in os.listdir(folder_path) if f.lower().endswith('.png')])

class TrainPanel(tk.Frame):
    def __init__(self, parent, on_back=None):
        super().__init__(parent, bg="#a259c6")
        self.settings = UM.load_settings()
        self.cancel_training = False
        self.training_in_progress = False
        self.on_back = on_back

        # Profile-specific paths
        profile_dir = os.path.join(self.settings["BASE_DIR"], self.settings["PROFILEPATH"])
        profile_name = os.path.basename(profile_dir)
        self.profile_csv_path = os.path.join(profile_dir, f"{profile_name}.csv")
        
        # Use global init_data folder for images and ground truth
        self.init_data_folder = os.path.join(self.settings["BASE_DIR"], self.settings.get("INIT_DATA_PATH", ""))
        self.ground_truth = pd.read_csv(os.path.join(self.init_data_folder, "init_data.csv")) if os.path.exists(os.path.join(self.init_data_folder, "init_data.csv")) else pd.DataFrame()

        # Load progress
        if os.path.exists(self.profile_csv_path):
            self.progress_df = pd.read_csv(self.profile_csv_path)
        else:
            self.progress_df = pd.DataFrame(columns=["image","outcome","race_scores","obese_scores"])

        # Find next image index
        done_images = set(self.progress_df["image"]) if not self.progress_df.empty else set()
        self.image_list = list(self.ground_truth["image"]) if not self.ground_truth.empty else []
        self.image_index = 0
        for idx, img in enumerate(self.image_list):
            if img not in done_images:
                self.image_index = idx
                break
        else:
            self.image_index = len(self.image_list)  # All done

        # Modern phone-like card
        card = tk.Frame(self, bg="white", bd=0, highlightthickness=0)
        card.place(relx=0.5, rely=0.5, anchor="center", width=370, height=750)

        # Modern back button
        if self.on_back:
            back_btn = tk.Button(card, text="← Back", font=("Arial", 12), bg="#e9eef6", relief="flat", command=self.handle_back, cursor="hand2")
            back_btn.place(relx=0.02, rely=0.01, anchor="nw")

        # Large title and subtitle
        tk.Label(card, text="Trainer", font=("Arial", 22, "bold"), bg="white", fg="#7c3aed").pack(pady=(32, 2))
        tk.Label(card, text="Adjust your preferences and train your model", font=("Arial", 12), bg="white", fg="#888").pack(pady=(0, 10))

        # Main vertical layout
        main_column = tk.Frame(card, bg="white")
        main_column.pack(fill=tk.BOTH, expand=True, pady=(0, 0))

        # Attractiveness meter (modern, long, pretty)
        meter_frame = tk.Frame(main_column, bg="white")
        meter_frame.pack(pady=(2, 0))
        tk.Label(meter_frame, text="Attractiveness", font=("Arial", 12, "bold"), bg="white", fg="#7c3aed").pack(anchor="center", pady=(0, 0))
        self.attr_slider = Scale(meter_frame, from_=-1, to=1, resolution=0.1, orient="horizontal", length=320, bg="white", highlightbackground="white", troughcolor="#e0e0e0", sliderrelief="flat", showvalue=True, width=18, sliderlength=32, font=("Arial", 11, "bold"))
        self.attr_slider.set(0)
        self.attr_slider.pack(anchor="center", pady=(0, 4))

        # Large, centered image (phone style)
        self.image_label = tk.Label(main_column, bg="#f5f5f5", width=300, height=300, bd=0, relief="flat")
        self.image_label.pack(pady=(8, 18))
        if self.image_index < len(self.image_list):
            image_path = os.path.join(self.init_data_folder, self.image_list[self.image_index])
        else:
            image_path = os.path.join(self.settings["BASE_DIR"], "images", "ui", "AllDone.png")
        self.load_image_to_label(self.image_label, image_path, fixed_height=300)

        # Navigation buttons (just below image, phone style)
        nav_frame = tk.Frame(main_column, bg="white")
        nav_frame.pack(pady=(0, 18))
        self.prev_button = tk.Button(nav_frame, text="Previous", font=("Arial", 12), command=self.handle_prev_button, bg="#e9eef6", relief="flat", cursor="hand2", width=10)
        self.prev_button.pack(side=tk.LEFT, padx=10, ipadx=6, ipady=4)
        self.next_button = tk.Button(nav_frame, text="Confirm & Next", font=("Arial", 12, "bold"), command=self.handle_next_button, bg="#7c3aed", fg="white", relief="flat", cursor="hand2", activebackground="#a259c6", width=16)
        self.next_button.pack(side=tk.LEFT, padx=10, ipadx=6, ipady=4)
        if self.image_index >= len(self.image_list):
            self.next_button.config(state=tk.DISABLED)
        if self.image_index == 0:
            self.prev_button.config(state=tk.DISABLED)

        # Training options and action buttons (bottom row)
        action_frame = tk.Frame(card, bg="white")
        action_frame.pack(side=tk.BOTTOM, pady=(0, 8))
        accuracy_frame = tk.Frame(action_frame, bg="white")
        accuracy_frame.pack(pady=(0, 10))
        tk.Label(accuracy_frame, text="Training Accuracy:", font=("Arial", 12), bg="white").pack(side=tk.LEFT, padx=5)
        self.accuracy_var = tk.StringVar(value="Moderate")
        accuracy_options = ["Accurate", "Moderate", "Basic", "Custom"]
        self.accuracy_menu = tk.OptionMenu(accuracy_frame, self.accuracy_var, *accuracy_options, command=self.handle_accuracy_selection)
        self.accuracy_menu.config(width=10)
        self.accuracy_menu.pack(side=tk.LEFT)
        self.custom_epoch_entry = tk.Entry(accuracy_frame, width=5)
        self.custom_epoch_entry.insert(0, "100")  # default
        self.custom_epoch_entry.pack(side=tk.LEFT, padx=5)
        self.custom_epoch_entry.pack_forget()  # hidden initially
        self.train_button = tk.Button(action_frame, text="Train", font=("Arial", 12, "bold"), width=16, command=self.handle_train_or_cancel, bg="#4CAF50", fg="white", relief="flat", cursor="hand2", activebackground="#388e3c", padx=16)
        self.train_button.pack(side=tk.LEFT, padx=16, ipadx=12, ipady=3, pady=7)

        # Feedback label just above action_frame at the bottom
        verdict_path = os.path.join(self.settings["BASE_DIR"], self.settings["PROFILEPATH"], "user_verdicts.csv")
        if os.path.exists(verdict_path):
            df = pd.read_csv(verdict_path)
            feedbackNum = len(df)
            self.feedback_label = tk.Label(
                card,
                text=f"You also made {feedbackNum} feedbacks that will go together into the training process.",
                font=("Arial", 10),
                bg="white",
                fg="#888",
                wraplength=320,
                justify="center"
            )
            self.feedback_label.pack(pady=(0, 8), before=action_frame)

        self.progress_bar = None
        self.epoch_label = None

    def load_image_to_label(self, label_widget, image_path, fixed_height=300):
        try:
            image = Image.open(image_path).convert("RGB")
            width, height = image.size
            aspect_ratio = width / height
            new_height = fixed_height
            new_width = int(aspect_ratio * new_height)
            resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            tk_image = ImageTk.PhotoImage(resized_image)
            label_widget.image = tk_image
            label_widget.config(image=tk_image)
        except Exception as e:
            print(f"[ERROR] Failed to load image {image_path}: {e}")

    def handle_accuracy_selection(self, value):
        if value == "Custom":
            self.custom_epoch_entry.pack(side=tk.LEFT, padx=5)
        else:
            self.custom_epoch_entry.pack_forget()

    def handle_prev_button(self):
        if self.image_index <= 0:
            return
        self.image_index -= 1
        image_path = os.path.join(self.init_data_folder, self.image_list[self.image_index])
        self.load_image_to_label(self.image_label, image_path)
        # Restore value if present
        img_name = self.image_list[self.image_index]
        match = self.progress_df["image"] == img_name
        if match.any():
            stored_attractiveness = self.progress_df.loc[match, "outcome"].values[0]
            self.attr_slider.set(stored_attractiveness)
        else:
            self.attr_slider.set(0)
        self.next_button.config(state=tk.NORMAL)
        if self.image_index == 0:
            self.prev_button.config(state=tk.DISABLED)

    def handle_next_button(self):
        # Write the current slider value into csv
        img_name = self.image_list[self.image_index]
        row_dict = self.ground_truth.loc[self.ground_truth["image"] == img_name].iloc[0].to_dict()
        match = self.progress_df["image"] == img_name
        if match.any():
            # Update row if already exist
            self.progress_df.loc[match, "outcome"] = self.attr_slider.get()
            self.progress_df.loc[match, "race_scores"] = row_dict["race_scores"]
            self.progress_df.loc[match, "obese_scores"] = row_dict["obese_scores"]
        else:
            # Append a new row
            new_row = {
                "image": row_dict["image"],
                "outcome": self.attr_slider.get(),
                "race_scores": row_dict["race_scores"],
                "obese_scores": row_dict["obese_scores"]
            }
            self.progress_df = pd.concat([self.progress_df, pd.DataFrame([new_row])], ignore_index=True)
        # Save the updated DataFrame back to the CSV
        self.save_progress()
        self.image_index += 1
        if self.image_index < len(self.image_list):
            image_path = os.path.join(self.init_data_folder, self.image_list[self.image_index])
            self.prev_button.config(state=tk.NORMAL)
            self.next_button.config(state=tk.NORMAL)
            # Restore value if present
            img_name = self.image_list[self.image_index]
            match = self.progress_df["image"] == img_name
            if match.any():
                self.attr_slider.set(float(self.progress_df.loc[match, "outcome"]))
            else:
                self.attr_slider.set(0)
        else:
            self.next_button.config(state=tk.DISABLED)
            image_path = os.path.join(self.settings["BASE_DIR"], "images", "ui", "AllDone.png")
            self.attr_slider.set(0)
        self.load_image_to_label(self.image_label, image_path)

    def handle_train_or_cancel(self):
        if not self.training_in_progress:
            self.training_in_progress = True
            self.cancel_training = False
            self.train_button.config(text="Cancel")

            self.progress_bar = Progressbar(self, orient="horizontal", length=500, mode="determinate")
            self.progress_bar.pack(pady=(20, 5))
            self.epoch_label = tk.Label(self, text="", font=("Arial", 12))
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
            os.path.normpath(os.path.join(settings["BASE_DIR"], settings["DATA_INDEX"])),
            os.path.normpath(os.path.join(settings["BASE_DIR"], settings["PROFILEPATH"], "user_verdicts.csv")),
            os.path.normpath(os.path.join(settings["BASE_DIR"], settings["INIT_DATA_PATH"])),
            int(settings["IMG_SIZE"]),
            int(settings["BATCH_SIZE"]),
            float(settings["TTS"])
        )

        total_epochs = 200
        model_path = os.path.normpath(os.path.join(settings["BASE_DIR"],settings["MODELPATH"]))

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

        self.after(0, lambda: self.progress_bar.config(maximum=total_epochs))

        def log_progress(epoch):
            self.after(0, lambda: self.progress_bar.config(value=epoch - 1))
            self.after(0, lambda: self.epoch_label.config(text=f"Epoch {epoch} / {total_epochs} (it takes around 1 minute for each epoch)"))

        ML.train_classifier_with_metadata(
            train_loader=train_loader,
            num_epochs=total_epochs,
            image_size=int(settings["IMG_SIZE"]),
            model_path=model_path,
            cancel_flag=lambda: self.cancel_training,
            progress_callback=log_progress
        )

        self.after(0, self.training_finished)
    
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

    def handle_back(self):
        if self.on_back:
            self.on_back()

    def save_progress(self):
        """Save the current progress DataFrame to the profile's CSV file"""
        print(f"[DEBUG] Saving progress to {self.profile_csv_path}")
        self.progress_df.to_csv(self.profile_csv_path, index=False)