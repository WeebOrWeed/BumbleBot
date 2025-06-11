import threading
import time
from model import machineLearning as ML
from model.machineLearning import InterestRegressorWithMetadata
from automation import bumbleMethods as BM
from utils import utilities as UM
import numpy as np
import os
import csv
import shutil
import random
import torch

class SwipeController:
    def __init__(self, browser, set_status, show_continue, show_stop, set_continue_callback, set_stop_callback):
        self.browser = browser
        self.set_status = set_status or (lambda text: print(text))
        self.show_continue = show_continue or (lambda: None)
        self.show_stop = show_stop or (lambda: None)
        self.set_continue_callback = set_continue_callback
        self.set_stop_callback = set_stop_callback
        self._stop_callback = None
        
        self.loaded_model = None
        self.settings = None
        self.root_alive = True
        self.login_confirmed = [False]

    def start(self):
        """Start the swiping process"""
        try:
            self.settings = UM.load_settings()
            self._load_model()
            print("[DEBUG] Loading browser")
            self.browser.LoadUrl("https://bumble.com/app")
            self._wait_for_login()
        except Exception as e:
            self.set_status(f"Error starting swipe process: {str(e)}")
            self._cleanup()

    def _load_model(self):
        """Load the ML model"""
        try:
            self.loaded_model = InterestRegressorWithMetadata(int(self.settings["IMG_SIZE"]))
            ML.init_models()
            load_path = os.path.normpath(self.settings["MODELPATH"])
            device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            loaded_state_dict = torch.load(load_path, map_location=device)
            self.loaded_model.load_state_dict(loaded_state_dict)
            self.loaded_model.to(device)
            self.loaded_model.eval()
        except Exception as e:
            self.set_status("Couldn't load existing model. Please train a model first.")
            raise

    def _wait_for_login(self):
        """Handle the login waiting process"""
        def on_continue():
            print("[DEBUG] Login confirmed. Starting auto swipe...")
            self.root_alive = True
            self.login_confirmed[0] = True
            self.set_status("Logged in, swiping...")
            self.show_stop()
            threading.Thread(target=self._swipe_on_background, daemon=True).start()

        print("[DEBUG] Setting up callbacks...")
        # Set up callbacks
        if self.set_continue_callback:
            self.set_continue_callback(on_continue)
        if self.set_stop_callback:
            self.set_stop_callback(self._stop_swiping)

        # Show initial UI state
        self.show_continue()
        self.set_status("Log in then click Continue to start.")

    def _set_stop_callback(self, callback):
        self._stop_callback = callback

    def _stop_swiping(self):
        self._cleanup()
        if self._stop_callback:
            self._stop_callback()

    def _cleanup(self):
        self.root_alive = False

    def _clear_overflow_profile(self, prediction_csv_path, max_profile_number=100):
        """Clear old profiles from storage"""
        existing_rows = []
        with open(prediction_csv_path, "r", newline="") as file:
            reader = csv.reader(file)
            for row in reader:
                if row:
                    existing_rows.append(row)
            num_profiles = len(existing_rows) - 1
            existing_rows = existing_rows[1:]  # Skip the first title row
            if num_profiles <= max_profile_number:
                return

        with open(prediction_csv_path, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["profile","image","race_score","obesity_score","predicted_attractiveness","final_decision"])
            for i in range(max_profile_number):
                writer.writerow(existing_rows[num_profiles - max_profile_number + i])
            
            # Remove old profile folders
            for i in range(num_profiles - max_profile_number):
                user_name = os.path.splitext(os.path.basename(self.settings["MODELPATH"]))[0]
                folder_path = os.path.join(self.settings['BASE_DIR'],"weights",user_name,"PREDICTION",existing_rows[i][0])
                if os.path.exists(folder_path):
                    try:
                        shutil.rmtree(folder_path)
                    except Exception as e:
                        print(f"Error removing folder '{folder_path}': {e}")

    def _swipe_on_background(self):
        """Main swiping process"""
        self.set_status("Now logged in. Starting auto swipe...")
        print("[DEBUG] Now logged in. Starting auto swipe...")
        
        # Setup directories and files
        user_name = os.path.splitext(os.path.basename(self.settings["MODELPATH"]))[0]
        folder_path = os.path.join(self.settings["BASE_DIR"],"weights",user_name)
        os.makedirs(folder_path, exist_ok=True)
        datafp = os.path.join(folder_path, "PREDICTION")
        os.makedirs(datafp, exist_ok=True)
        prediction_csv_path = os.path.join(folder_path, f"predictions.csv")
        
        if not os.path.exists(prediction_csv_path):
            with open(prediction_csv_path, "w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["profile","image","race_score","obesity_score","predicted_attractiveness","final_decision"])

        self._clear_overflow_profile(prediction_csv_path, self.settings["MAX_PROFILE_STORED"])

        # Main swiping loop
        with open(prediction_csv_path, "a+", newline="") as file:
            print("[DEBUG] CSV opened")
            writer = csv.writer(file)
            counter = int(self.settings["TOTALSWIPES"])
            print("[DEBUG] Counter and root alive", counter, self.root_alive)
            while counter > 0 and self.root_alive:
                print("[DEBUG] Swiping... counter", counter)
                counter = counter - 1
                value = np.random.normal(loc=3, scale=0.3)
                self.set_status(f"Swiping... {counter} swipes left.")
                time.sleep(value)

                profile = BM.find_download_all_pictures(self.browser, datafp)
                if profile == 'invalid':
                    self.set_status("No photos detected, skipping profile.")
                    continue

                # Make predictions
                profile_dataloader = ML.load_images_for_prediction_dataloader(datafp, int(self.settings["IMG_SIZE"]), profile)
                raw_predictions, race_scores, obesity_scores = ML.predict(self.loaded_model, profile_dataloader)
                
                avg_prediction = np.mean(raw_predictions) if raw_predictions else 0.0
                decision_threshold = float(self.settings.get('THRESH', 0.2))
                decision = 1 if avg_prediction > decision_threshold or sum(1 for item in raw_predictions if item > 0.9) >= 2 else 0
                
                self.set_status(f"Profile: {profile}\nAvg score: {avg_prediction:.4f}\nDecision: {'Like' if decision else 'Dislike'}")

                # Log results
                image_files = sorted(os.listdir(os.path.join(datafp, profile)))
                if image_files:
                    idx = random.randint(0, len(image_files) - 1)
                    image_file = image_files[idx]
                    writer.writerow([profile, image_file, race_scores[idx], obesity_scores[idx], raw_predictions[idx], decision])
                file.flush()
                
                self._clear_overflow_profile(prediction_csv_path, self.settings["MAX_PROFILE_STORED"])

                # Perform swipe
                if decision == 1:
                    BM.like_profile(self.browser)
                else:
                    BM.dislike_profile(self.browser)
                time.sleep(2)

        self.set_status("Click to swipe again")
        self.show_continue()
        self._cleanup() 