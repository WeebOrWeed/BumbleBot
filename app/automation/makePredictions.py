from model import machineLearning as ML
from automation import bumbleMethods as BM
from utils import utilities as UM
import numpy as np
from model.machineLearning import InterestRegressorWithMetadata  # Import the regression model
from model.obeseTrainer import BodyTypeClassifier
from selenium import webdriver
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

root = None
settings = None

def make_predictions():
    global root, settings
    try:
        # load up all the settings
        settings = UM.load_settings()
        # first go to bumble.com
        driver = webdriver.Chrome()
        # also load up the model cause why do that later
        loaded_model = InterestRegressorWithMetadata(int(settings["IMG_SIZE"]))  # Load the regression model
        ML.init_models()
        # try loading up the weights
        try:
            load_path = os.path.normpath(settings["MODELPATH"])
            device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            loaded_state_dict = torch.load(load_path, map_location=device)
            loaded_model.load_state_dict(loaded_state_dict)
            loaded_model.to(device)
            loaded_model.eval()
        except Exception as e:
            print("Couldn't load existing model")
            print("Exiting ... please train a model first")
            exit()
        # then navigate to bumble
        driver.get("https://bumble.com/app")
        # do nothing await user input
        # login = input("Type in yes when you have logged in (Then ofc press enter): ")
        wait_for_login_callback(driver, loaded_model)
    except Exception as e:
        print("Sorry something went wrong")
        # Get the traceback information
        tb = sys.exc_info()[2]
        # Extract the line number from the traceback
        lineno = tb.tb_lineno
        # Print the exception and the line number
        print(f"An error occurred on line {lineno}: {e}")

def wait_for_login_callback(driver, loaded_model):
    import tkinter as tk
    import threading
    import time
    global root, settings

    root_alive = True
    login_confirmed = [False]  # Use mutable container to allow setting from inner scope
    label = None
    continue_button = None
    stop_button = None
    def stop_everything():
        try:
            if driver:
                driver.quit()
        except:
            pass
        try:
            root.after(1, root.destroy)
        except:
            pass

    def on_continue():
        nonlocal root_alive
        root_alive = False
        login_confirmed[0] = True
        if label:
            label.config(text="Logged in, swiping...")
        if continue_button:
            continue_button.pack_forget()
        if stop_button:
            stop_button.pack()
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
                folder_path = os.path.join("Weights",user_name,"PREDICTION",existing_rows[i][0]) # assumes profile is the first column
                if os.path.exists(folder_path):
                    try:
                        shutil.rmtree(folder_path)
                        print(f"Folder '{folder_path}' and its contents have been removed due to we keep only up to {max_profile_number} most recent profiles.")
                    except Exception as e:
                        print(f"Error removing folder '{folder_path}': {e}")
                else:
                    print(f"Folder '{folder_path}' does not exist.")


    def swipe_on_background():
        print("Now logged in")
        # now make the log file for this session
        user_name = os.path.splitext(os.path.basename(settings["MODELPATH"]))[0]
        folder_path = os.path.join("Weights",user_name)
        os.makedirs(folder_path, exist_ok=True)
        # Make a Predicions folder if necessary, this folder contains all photos downloaded
        datafp = os.path.join(folder_path, "PREDICTION")
        os.makedirs(datafp, exist_ok=True)
        # Create profile prediction csv if not available
        prediction_csv_path = os.path.join(folder_path, f"predictions.csv")
        if not os.path.exists(prediction_csv_path):
            with open(prediction_csv_path, "w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["profile","image","race_score","obesity_score","predicted_attractiveness","final_decision"])
        clear_overflow_profile(prediction_csv_path, settings["MAX_PROFILE_STORED"])
        with open(prediction_csv_path, "a+", newline="") as file:
            writer = csv.writer(file)
            # this is the end of the first initial setup
            counter = int(settings["TOTALSWIPES"])
            while counter > 0:
                # increment the counter down
                counter = counter - 1
                # wait for about 5 seconds
                value = np.random.normal(loc=3, scale=0.3)
                print(f"Sleep for {value} seconds")
                time.sleep(value)
                # then save all the pictures in the right directory
                profile = BM.find_download_all_pictures(driver, datafp)
                if profile == 'invalid':
                    print("no photos detected, proceed to the next")
                    continue
                # make a prediction on this profile
                profile_dataloader = ML.load_images_for_prediction_dataloader(datafp, int(settings["IMG_SIZE"]), profile)
                # Make predictions for all images in the DataLoader
                raw_predictions, race_scores, obesity_scores = ML.predict(loaded_model, profile_dataloader)
                print("predicted scores " + str(raw_predictions))
    
                # Decide based on the continuous predictions
                # Example: Average score and threshold
                avg_prediction = np.mean(raw_predictions) if raw_predictions else 0.0
                decision_threshold = float(settings.get('THRESH', 0.2)) # Example threshold
                decision = 1 if avg_prediction > decision_threshold or sum(1 for item in raw_predictions if item > 0.9) >= 2 else 0
                print(f"average prediction score: {avg_prediction:.4f}, final decision: {decision}")
    
                # log a random image of profile to csv
                image_files = sorted(os.listdir(os.path.join(datafp, profile)))
                if image_files:
                    idx = random.randint(0, len(image_files) - 1)
                    image_file = image_files[idx]
                    writer.writerow([profile, image_file, race_scores[idx], obesity_scores[idx], raw_predictions[idx], decision])  # add other fields if needed
                file.flush()
                clear_overflow_profile(prediction_csv_path, settings["MAX_PROFILE_STORED"])

                # then actually swipe left or right
                if (decision == 1):
                    BM.like_profile(driver)
                else:
                    BM.dislike_profile(driver)
                time.sleep(2)

    def on_close():
        nonlocal root_alive
        root_alive = False
        try:
            driver.quit()
        except:
            pass
        try:
            if root.winfo_exists():
                root.after(1, root.destroy)
        except:
            pass

    def monitor_chrome():
        nonlocal root_alive
        while root_alive:
            try:
                _ = driver.title
            except:
                try:
                    if root.winfo_exists():
                        root.after(1, root.destroy)
                except:
                    pass
                break
            time.sleep(1)

    root = tk.Tk()
    root.title("Login Required")
    root.iconbitmap(UM.resource_path("BumbleBotLogo.ico"))
    root.geometry("300x120")
    root.attributes("-topmost", True)
    root.focus_set()
    root.protocol("WM_DELETE_WINDOW", on_close)

    label = tk.Label(root, text="Log in to Bumble,\nthen click to continue.", font=("Arial", 11))
    label.pack(pady=10)
    button_row = tk.Frame(root)
    button_row.pack(pady=10)
    continue_button = tk.Button(button_row, text="I'm Logged In", command=on_continue)
    continue_button.pack(side=tk.LEFT, padx=10)
    stop_button = tk.Button(button_row, text="Stop", command=stop_everything)
    stop_button.pack(side=tk.LEFT, padx=10)
    stop_button.pack_forget()

    threading.Thread(target=monitor_chrome, daemon=True).start()

    # Start mainloop safely in main thread
    root.mainloop()

    # Now you're safe to proceed after the UI closes
    if not login_confirmed[0]:
        raise RuntimeError("User closed login popup or Chrome before confirming.")