import tkinter as tk
from tkinter import Scale
from utils import utilities as UM
import os
import pandas as pd
from pathlib import Path
import csv
from PIL import Image, ImageTk
import shutil

class ReviewPanel(tk.Toplevel):
    class ImageInfo:
        def __init__(self, image_path, score, outcome, race_score, obesity_score, profile):
            self.image_path = image_path
            self.score = score
            self.outcome = outcome
            self.race_score = race_score
            self.obesity_score = obesity_score
            self.profile = profile
        
    def __init__(self, parent):
        super().__init__(parent)
        self.settings = UM.load_settings()
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
        
        self.title("Review Past")
        self.geometry("800x600")
        self.iconbitmap(UM.resource_path("BumbleBotLogo.ico"))
        self.focus_set()
        self.grab_set()
        tk.Label(self, text="Review your predictions", font=("Arial", 20)).pack(pady=10)
        # Main frame for everything
        top_frame = tk.Frame(self)
        top_frame.pack(pady=10)
        
        # Image + slider vertical frame
        center_column = tk.Frame(top_frame)
        center_column.pack(side=tk.LEFT, padx=10)
    
        self.attr_slider = Scale(center_column, from_=-1, to=1, resolution=0.1, orient="horizontal", label="Attractiveness", length=100)
        self.attr_slider.pack(pady=5, anchor="center")
    
        self.image_label = tk.Label(center_column)
        self.image_label.pack(pady=5, anchor="center")
        
        self.decision_label = tk.Label(center_column)
        self.decision_label.pack(pady=5, anchor="center")
        
        # Next Button
        next_button_frame = tk.Frame(top_frame)
        next_button_frame.pack(side=tk.LEFT, padx=10)
        self.next_button = tk.Button(next_button_frame, text="Confirm & Next", font=("Arial", 12), command=self.handle_next_button)
        self.next_button.pack(pady=20)
        self.update_buttons()
        
        if self.image_index == len(self.images):
            self.load_image_to_label(os.path.join(self.settings["BASE_DIR"], "images", "ui", "NoReviews.png"))
            self.next_button.destroy()
            self.attr_slider.destroy()
        else:
            self.load_image_to_label(self.images[self.image_index].image_path)
            self.attr_slider.set(self.images[self.image_index].score)
            self.update_decision_label(self.images[self.image_index].outcome)
        
    
    def handle_next_button(self):
        img = self.images[self.image_index]
        # First check if the prediction score is changed, if so, then store the image in the training dataset
        if abs(self.attr_slider.get() - self.images[self.image_index].score) >= 0.1:
            # print(f"Score changed, store into training dataset {self.attr_slider.get()} vs {self.images[self.image_index].score}")
            training_path = os.path.join(self.settings["BASE_DIR"], self.settings["PROFILEPATH"], "TRAINING")
            os.makedirs(training_path, exist_ok=True)
            verdict_path = os.path.join(self.settings["BASE_DIR"], self.settings["PROFILEPATH"], "user_verdicts.csv")
            file_exists = os.path.exists(verdict_path)
            # Open the file for writing ('w') if it doesn't exist (to write header)
            # or for appending ('a') if it already exists (to add data)
            with open(verdict_path, "a" if file_exists else "w", newline="") as file:
                writer = csv.writer(file)
                if not file_exists:
                # If the file didn't exist, write the header row first
                    writer.writerow(["image","outcome","race_scores","obese_scores"])
                img_name = img.profile + ".png"
                # Now, write the data row regardless of whether the header was just written or not
                writer.writerow([img_name, self.attr_slider.get(), img.race_score, img.obesity_score])
                
            # Move copy the image over to training set with new path
            shutil.copy(img.image_path, os.path.join(self.settings["BASE_DIR"], self.settings["PROFILEPATH"], "TRAINING", img_name))
                
        # delete line in predictions
        predictions_path = os.path.join(self.settings["BASE_DIR"], self.settings["PROFILEPATH"], "predictions.csv")
        df = pd.read_csv(predictions_path)
        df = df[df["profile"] != img.profile]
        df.to_csv(predictions_path, index=False)
            
        # remove profile from PREDICTION folder
        # print(f"deleted {os.path.join(self.settings["BASE_DIR"], self.settings["PROFILEPATH"], "PREDICTION", img.profile)}")
        shutil.rmtree(os.path.join(self.settings["BASE_DIR"], self.settings["PROFILEPATH"], "PREDICTION", img.profile))
                
        self.image_index += 1
        if self.image_index == len(self.images):
            self.load_image_to_label(os.path.join(self.settings["BASE_DIR"], "images", "ui", "ReviewComplete.png"))
            self.next_button.destroy()
            self.attr_slider.destroy()
            # self.button = tk.Button(self, text="Train", font=("Arial", 12), command=self.go_to_train)
        else:
            self.load_image_to_label(self.images[self.image_index].image_path)
            self.attr_slider.set(self.images[self.image_index].score)
            self.update_decision_label(self.images[self.image_index].outcome)
            self.update_buttons()
    
    # TODO: add to train button once Train Window becomes it's own class
    # def go_to_train(self):
            
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
    
            # Calculate new width while maintaining aspect ratio
            width, height = image.size
            aspect_ratio = width / height
            new_height = fixed_height
            new_width = int(aspect_ratio * new_height)
    
            resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            tk_image = ImageTk.PhotoImage(resized_image)
    
            # Store a reference to avoid garbage collection
            self.image_label.image = tk_image
            self.image_label.config(image=tk_image)
        except Exception as e:
            print(f"[ERROR] Failed to load image {image_path}: {e}")
        