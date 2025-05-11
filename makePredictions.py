import machineLearning as ML
import bumbleMethods as BM
import utilities as UM
import numpy as np
from machineLearning import InterestRegressorWithMetadata  # Import the regression model
from obeseTrainer import BodyTypeClassifier
from selenium import webdriver
import torch
import os
import time
import sys
import tkinter as tk
import threading
import traceback

root = None
settings = None
loaded_model = None

def make_predictions():
    global root, settings, loaded_model
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
        wait_for_login_callback(driver)
    except Exception as e:
        print("Sorry something went wrong")
        # Get the traceback information
        tb = sys.exc_info()[2]
        # Extract the line number from the traceback
        lineno = tb.tb_lineno
        # Print the exception and the line number
        print(f"An error occurred on line {lineno}: {e}")

def wait_for_login_callback(driver):
    import tkinter as tk
    import threading
    import time
    global root, settings, loaded_model

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

    def swipe_on_background():
        print("Now logged in")
        # now make the log file for this session
        profile_name = os.path.splitext(os.path.basename(settings["MODELPATH"]))[0]
        folder_path = os.path.join("Weights",profile_name)
        os.makedirs(os.path.dirname(folder_path), exist_ok=True)
        # Make a Predicions folder if necessary, this folder contains all photos downloaded
        datafp = os.path.join(folder_path, "PREDICTION")
        os.makedirs(os.path.dirname(datafp), exist_ok=True)
        # Create profile prediction csv if not available
        prediction_csv_path = os.path.join(folder_path, f"predictions.csv")
        if not os.path.exists(prediction_csv_path):
            with open(prediction_csv_path, "w") as file:
                writer = csv.writer(file)
                # We only display first image and it's predictions
                writer.writerow(["profile","prediction","race_scores","obese_scores"])
        
        df = pd.read_csv(prediction_csv_path)
        # now open a file in this folder
        csvsessdata = open(, "w")
        csvsessdata.write("profile,prediction_score,decision\n")  # Changed header
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
            # make a prediction on this profile
            profile_dataloader = ML.load_images_for_prediction_dataloader(datafp, int(settings["IMG_SIZE"]), profile)
            # Make predictions for all images in the DataLoader
            raw_predictions = ML.predict(loaded_model, profile_dataloader)
            print("predicted scores " + str(raw_predictions))

            # Decide based on the continuous predictions
            # Example: Average score and threshold
            avg_prediction = np.mean(raw_predictions) if raw_predictions else 0.0
            decision_threshold = float(settings.get('THRESH', 0.2)) # Example threshold
            decision = 1 if avg_prediction > decision_threshold or sum(1 for item in raw_predictions if item > 0.5) >= 2 or sum(1 for item in raw_predictions if item > 0.8) >= 1 else 0
            print(f"average prediction score: {avg_prediction:.4f}, final decision: {decision}")

            # log this in the logger
            csvsessdata.write(f"{profile},{avg_prediction},{decision}\n") # Log the continuous score

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
    root.geometry("300x120")
    root.attributes("-topmost", True)
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