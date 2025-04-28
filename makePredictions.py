import machineLearning as ML
import bumbleMethods as BM
import utilities as UM
import numpy as np
from machineLearning import InterestRegressor  # Import the regression model
from selenium import webdriver
import torch
import os
import time

def make_predictions():
    try:
        # load up all the settings
        settings = UM.load_settings()
        # first go to bumble.com
        driver = webdriver.Chrome()
        # also load up the model cause why do that later
        loaded_model = InterestRegressor(int(settings["IMG_SIZE"]))  # Load the regression model
        # try loading up the weights
        try:
            load_path = settings["MODELPATH"]
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
        login = input("Type in yes when you have logged in (Then ofc press enter): ")
        if login == "yes":
            # return to the login prompt area
            print("Now logged in")
            # now make the log file for this session
            # first make a folder in the data folder
            sessionID = driver.session_id
            # create a folder under the data param with this name
            datafp = os.path.join(os.getcwd(), f"{sessionID}-PREDICTION")
            os.mkdir(datafp)
            # now open a file in this folder
            csvsessdata = open(os.path.join(datafp, f"{sessionID}-PREDICTION.csv"), "w")
            csvsessdata.write("profile,prediction_score,decision\n")  # Changed header
            # this is the end of the first initial setup
            counter = int(settings["TOTALSWIPES"])
            while counter > 0:
                # increment the counter down
                counter = counter - 1
                # wait for about 5 seconds
                time.sleep(5)
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
        else:
            print("Sorry you gotta logging")
            driver.close()
    except Exception as e:
        print("Sorry something went wrong")
        print(str(e))