import machineLearning as ML
import bumbleMethods as BM
import utilities as UM
from selenium import webdriver
import os
import time

def make_predictions():
    try:
        # load up all the settings
        settings = UM.load_settings()
        # first go to bumble.com
        driver = webdriver.Chrome()
        # also load up the model cause why do that later
        model = ML.build_model(int(settings["IMG_SIZE"]))
        # try loading up the weights
        try:
            model.load_weights(settings["MODELPATH"])
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
            csvsessdata.write("profile,prediction,outcome\n")
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
                pictures = ML.load_images_for_prediction(datafp, int(settings["IMG_SIZE"]), profile)
                prediction = ML.make_prediction(pictures, model)
                decision = ML.make_decision(prediction, settings['THRESH'])
                # log this in the logger 
                csvsessdata.write(f"{profile},{prediction},{decision}\n")
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


if __name__ == "__main__":
    make_predictions()