from model import machineLearning as ML
from automation import bumbleMethods as BM
from utils import utilities as UM
import numpy as np
from model.machineLearning import InterestRegressorWithMetadata  # Import the regression model
from model.obeseTrainer import BodyTypeClassifier
import torch
import os
import time
import sys
import tkinter as tk
import threading
import traceback
import csv
import shutil
import random
from ui.swipe_controller import SwipeController

root = None
settings = None

def make_predictions(browser, set_status=None, show_continue=None, show_stop=None, set_continue_callback=None, set_stop_callback=None):
    """Start the swiping process with the given UI callbacks and CEF browser"""
    controller = SwipeController(
        browser=browser,
        set_status=set_status,
        show_continue=show_continue,
        show_stop=show_stop,
        set_continue_callback=set_continue_callback,
        set_stop_callback=set_stop_callback
    )
    controller.start()

def wait_for_login_callback(driver, loaded_model, set_status=None, show_continue=None, show_stop=None, set_continue_callback=None, set_stop_callback=None):
    import threading
    import time
    global settings

    login_confirmed = [False]
    root_alive = True
    # UI callbacks
    if set_status is None:
        set_status = lambda text: print(text)
    if show_continue is None:
        show_continue = lambda: None
    if show_stop is None:
        show_stop = lambda: None
    # These will be settable by the UI
    continue_callback = [None]
    stop_callback = [None]

    def stop_everything():
        try:
            if driver:
                driver.quit()
        except:
            pass
        root_alive = False
        if stop_callback[0]:
            stop_callback[0]()

    def on_continue():
        nonlocal root_alive
        root_alive = False
        login_confirmed[0] = True
        set_status("Logged in, swiping...")
        show_stop()
        show_continue()  # Hide continue button if needed
        threading.Thread(target=swipe_on_background, daemon=True).start()

    def clear_overflow_profile(prediction_csv_path, max_profile_number = 100):
        existing_rows = []
        with open(prediction_csv_path, "r", newline="") as file:
            reader = csv.reader(file)
            for row in reader:
                if row:
                    existing_rows.append(row)
            num_profiles = len(existing_rows) - 1
            existing_rows = existing_rows[1:] # Skip the first title row
            if num_profiles <= max_profile_number:
                return

        with open(prediction_csv_path, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["profile","image","race_score","obesity_score","predicted_attractiveness","final_decision"])
            for i in range(max_profile_number):
                writer.writerow(existing_rows[num_profiles - max_profile_number + i])
            # Remove the no longer recorded profiles
            for i in range(num_profiles - max_profile_number):
                user_name = os.path.splitext(os.path.basename(settings["MODELPATH"]))[0]
                folder_path = os.path.join(settings['BASE_DIR'],"weights",user_name,"PREDICTION",existing_rows[i][0]) # assumes profile is the first column
                if os.path.exists(folder_path):
                    try:
                        shutil.rmtree(folder_path)
                        print(f"Folder '{folder_path}' and its contents have been removed due to we keep only up to {max_profile_number} most recent profiles.")
                    except Exception as e:
                        print(f"Error removing folder '{folder_path}': {e}")
                else:
                    print(f"Folder '{folder_path}' does not exist.")

    def swipe_on_background():
        set_status("Now logged in. Starting auto swipe...")
        user_name = os.path.splitext(os.path.basename(settings["MODELPATH"]))[0]
        folder_path = os.path.join(settings["BASE_DIR"],"weights",user_name)
        os.makedirs(folder_path, exist_ok=True)
        datafp = os.path.join(folder_path, "PREDICTION")
        os.makedirs(datafp, exist_ok=True)
        prediction_csv_path = os.path.join(folder_path, f"predictions.csv")
        if not os.path.exists(prediction_csv_path):
            with open(prediction_csv_path, "w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["profile","image","race_score","obesity_score","predicted_attractiveness","final_decision"])
        clear_overflow_profile(prediction_csv_path, settings["MAX_PROFILE_STORED"])
        print("[DEBUG] Starting swiping read csv")
        with open(prediction_csv_path, "a+", newline="") as file:
            writer = csv.writer(file)
            counter = int(settings["TOTALSWIPES"])
            print("[DEBUG] CSV read")
            while counter > 0:
                counter = counter - 1
                print("[DEBUG] Swiping... counter", counter)
                value = np.random.normal(loc=3, scale=0.3)
                set_status(f"Swiping... {counter} swipes left.")
                time.sleep(value)
                profile = BM.find_download_all_pictures(driver, datafp)
                if profile == 'invalid':
                    set_status("No photos detected, skipping profile.")
                    continue
                profile_dataloader = ML.load_images_for_prediction_dataloader(datafp, int(settings["IMG_SIZE"]), profile)
                raw_predictions, race_scores, obesity_scores = ML.predict(loaded_model, profile_dataloader)
                avg_prediction = np.mean(raw_predictions) if raw_predictions else 0.0
                decision_threshold = float(settings.get('THRESH', 0.2))
                decision = 1 if avg_prediction > decision_threshold or sum(1 for item in raw_predictions if item > 0.9) >= 2 else 0
                set_status(f"Profile: {profile}\nAvg score: {avg_prediction:.4f}\nDecision: {'Like' if decision else 'Dislike'}")
                image_files = sorted(os.listdir(os.path.join(datafp, profile)))
                if image_files:
                    idx = random.randint(0, len(image_files) - 1)
                    image_file = image_files[idx]
                    writer.writerow([profile, image_file, race_scores[idx], obesity_scores[idx], raw_predictions[idx], decision])
                file.flush()
                clear_overflow_profile(prediction_csv_path, settings["MAX_PROFILE_STORED"])
                if (decision == 1):
                    BM.like_profile(driver)
                else:
                    BM.dislike_profile(driver)
                time.sleep(2)
        set_status("Auto swipe finished. You can close this page.")
        show_continue()
        stop_everything()

    def monitor_chrome():
        nonlocal root_alive
        while root_alive:
            try:
                _ = driver.title
            except:
                stop_everything()
                break
            time.sleep(1)

    # Set up callbacks for UI
    if set_continue_callback:
        set_continue_callback(on_continue)
    if set_stop_callback:
        set_stop_callback(stop_everything)
    # Show the continue button
    show_continue()
    set_status("Log in to Bumble, then click to continue.")
    # Optionally, monitor Chrome in a thread
    threading.Thread(target=monitor_chrome, daemon=True).start()
    # The UI will call on_continue() when the user clicks continue