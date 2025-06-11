import tkinter as tk
from tkinter import Scale, ttk
from utils import utilities as UM
import os
import pandas as pd
from pathlib import Path
import csv
from PIL import Image, ImageTk
import shutil

class ReviewPanel(tk.Frame):
    class ImageInfo:
        def __init__(self, image_path, score, outcome, race_score, obesity_score, profile):
            self.image_path = image_path
            self.score = score
            self.outcome = outcome
            self.race_score = race_score
            self.obesity_score = obesity_score
            self.profile = profile
        
    def __init__(self, parent, on_back=None):
        super().__init__(parent, bg="#a259c6")  # Match AuthUI theme
        self.settings = UM.load_settings()
        self.on_back = on_back
        
        # Load the image paths
        self.images = []
        predictions_path = os.path.join(self.settings["BASE_DIR"], self.settings["PROFILEPATH"], "predictions.csv")
        if not os.path.exists(predictions_path):
            with open(predictions_path, "w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["profile","image","predicted_attractiveness","final_decision"])
                file.flush()
        df = pd.read_csv(predictions_path)
        for row in df.itertuples():
            self.images.append(self.ImageInfo(os.path.join(self.settings["BASE_DIR"], self.settings["PROFILEPATH"], "PREDICTION", row.profile, row.image), row.predicted_attractiveness, row.final_decision, row.race_score, row.obesity_score, row.profile))
        self.image_index = 0

        # Modern phone-like card
        card = tk.Frame(self, bg="white", bd=0, highlightthickness=0)
        card.place(relx=0.5, rely=0.5, anchor="center", width=370, height=750)

        # Modern back button
        if self.on_back:
            back_btn = tk.Button(card, text="← Back", font=("Arial", 12), bg="#e9eef6", relief="flat", command=self.handle_back, cursor="hand2")
            back_btn.place(relx=0.02, rely=0.01, anchor="nw")

        # Large title and subtitle
        tk.Label(card, text="Review", font=("Arial", 22, "bold"), bg="white", fg="#7c3aed").pack(pady=(32, 2))
        tk.Label(card, text="Review and adjust your past predictions", font=("Arial", 12), bg="white", fg="#888").pack(pady=(0, 10))

        # Progress indicator
        self.progress_label = tk.Label(card,
                                     text=f"Image {self.image_index + 1} of {len(self.images)}",
                                     font=("Arial", 12),
                                     bg="white",
                                     fg="#666")
        self.progress_label.pack(pady=(0, 20))

        # Main vertical layout
        main_column = tk.Frame(card, bg="white")
        main_column.pack(fill=tk.BOTH, expand=True, pady=(0, 0))

        # Large, centered image (phone style)
        self.image_label = tk.Label(main_column, bg="#f5f5f5", width=300, height=300, bd=0, relief="flat")
        self.image_label.pack(pady=(8, 18))

        # Attractiveness meter (modern, long, pretty)
        self.meter_frame = tk.Frame(main_column, bg="white")
        self.meter_label = tk.Label(self.meter_frame, text="Attractiveness", font=("Arial", 12, "bold"), bg="white", fg="#7c3aed")
        self.attr_slider = Scale(self.meter_frame, 
                               from_=-1, 
                               to=1, 
                               resolution=0.1, 
                               orient="horizontal", 
                               length=320, 
                               bg="white", 
                               highlightbackground="white", 
                               troughcolor="#e0e0e0", 
                               sliderrelief="flat", 
                               showvalue=True, 
                               width=18, 
                               sliderlength=32, 
                               font=("Arial", 11, "bold"))
        # Decision label
        self.decision_label = tk.Label(main_column, bg="white")
        self.decision_label.pack(pady=20)
        # Next button
        self.next_button = tk.Button(main_column, 
                                   text="Confirm & Next", 
                                   font=("Arial", 12, "bold"), 
                                   command=self.handle_next_button, 
                                   bg="#7c3aed", 
                                   fg="white", 
                                   relief="flat", 
                                   cursor="hand2", 
                                   activebackground="#a259c6", 
                                   width=16)
        self.next_button.pack(pady=20, ipadx=6, ipady=4)

        self.update_buttons()
        
        if self.image_index == len(self.images) or len(self.images) == 0:
            self.load_image_to_label(os.path.join(self.settings["BASE_DIR"], "images", "ui", "NoReviews.png"))
            self.next_button.pack_forget()
            self.meter_frame.pack_forget()
        else:
            self.load_image_to_label(self.images[self.image_index].image_path)
            self.meter_frame.pack(pady=(2, 0))
            self.meter_label.pack(anchor="center", pady=(0, 0))
            self.attr_slider.pack(anchor="center", pady=(0, 4))
            self.attr_slider.set(self.images[self.image_index].score)
            self.update_decision_label(self.images[self.image_index].outcome)

    def handle_back(self):
        if self.on_back:
            self.on_back()

    def handle_next_button(self):
        img = self.images[self.image_index]
        # First check if the prediction score is changed, if so, then store the image in the training dataset
        if abs(self.attr_slider.get() - self.images[self.image_index].score) >= 0.1:
            training_path = os.path.join(self.settings["BASE_DIR"], self.settings["PROFILEPATH"], "TRAINING")
            os.makedirs(training_path, exist_ok=True)
            verdict_path = os.path.join(self.settings["BASE_DIR"], self.settings["PROFILEPATH"], "user_verdicts.csv")
            file_exists = os.path.exists(verdict_path)
            with open(verdict_path, "a" if file_exists else "w", newline="") as file:
                writer = csv.writer(file)
                if not file_exists:
                    writer.writerow(["image","outcome","race_scores","obese_scores"])
                img_name = img.profile + ".png"
                writer.writerow([img_name, self.attr_slider.get(), img.race_score, img.obesity_score])
                
            shutil.copy(img.image_path, os.path.join(self.settings["BASE_DIR"], self.settings["PROFILEPATH"], "TRAINING", img_name))
                
        predictions_path = os.path.join(self.settings["BASE_DIR"], self.settings["PROFILEPATH"], "predictions.csv")
        df = pd.read_csv(predictions_path)
        df = df[df["profile"] != img.profile]
        df.to_csv(predictions_path, index=False)
            
        shutil.rmtree(os.path.join(self.settings["BASE_DIR"], self.settings["PROFILEPATH"], "PREDICTION", img.profile))
                
        self.image_index += 1
        self.progress_label.config(text=f"Image {self.image_index + 1} of {len(self.images)}")
        
        if self.image_index == len(self.images):
            self.load_image_to_label(os.path.join(self.settings["BASE_DIR"], "images", "ui", "ReviewComplete.png"))
            self.next_button.pack_forget()
            self.meter_frame.pack_forget()
        else:
            self.load_image_to_label(self.images[self.image_index].image_path)
            self.meter_frame.pack(pady=(2, 0))
            self.meter_label.pack(anchor="center", pady=(0, 0))
            self.attr_slider.pack(anchor="center", pady=(0, 4))
            self.attr_slider.set(self.images[self.image_index].score)
            self.update_decision_label(self.images[self.image_index].outcome)
            self.update_buttons()
    
    def update_buttons(self):
        if self.image_index == len(self.images):
            self.next_button.config(state=tk.DISABLED)
        else:
            self.next_button.config(state=tk.NORMAL)
    
    def update_decision_label(self, liked, fixed_height=80):
        try:
            image_path = ""
            if liked:
                image_path = os.path.join(self.settings["BASE_DIR"], "images", "ui", "Liked.png")
            else:
                image_path = os.path.join(self.settings["BASE_DIR"], "images", "ui", "Nope.png")
            image = Image.open(image_path).convert("RGBA")
            bg = Image.new("RGBA", image.size, (0, 0, 0, 0))
            image = Image.alpha_composite(bg, image)
    
            # Calculate new width while maintaining aspect ratio
            width, height = image.size
            aspect_ratio = width / height
            new_height = fixed_height
            new_width = int(aspect_ratio * new_height)
    
            resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            tk_image = ImageTk.PhotoImage(resized_image)
    
            # Store a reference to avoid garbage collection
            self.decision_label.image = tk_image
            self.decision_label.config(image=tk_image)
        except Exception as e:
            print(f"[ERROR] Failed to load image {image_path}: {e}")
    
    def load_image_to_label(self, image_path, fixed_height=300):
        try:
            image = Image.open(image_path).convert("RGB")
            width, height = image.size
            aspect_ratio = width / height
            new_height = fixed_height
            new_width = int(aspect_ratio * new_height)
            resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            tk_image = ImageTk.PhotoImage(resized_image)
            self.image_label.image = tk_image
            self.image_label.config(image=tk_image)
        except Exception as e:
            print(f"[ERROR] Failed to load image {image_path}: {e}")
        