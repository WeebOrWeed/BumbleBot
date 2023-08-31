from selenium import webdriver
import os
import bumbleMethods as BM
import utilities as UM


def main_scrapping_app():
    try:
        # load up all the settings
        settings = UM.load_settings()
        # first go to bumble.com
        driver = webdriver.Chrome()
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
            datafp = os.path.join(os.getcwd(), settings["DATA"], sessionID)
            os.mkdir(datafp)
            # now open a file in this folder
            csvsessdata = open(os.path.join(datafp, f"{sessionID}.csv"), "w")
            csvsessdata.write("profile,outcome\n")
            # this is the end of the first initial setup
            while True:
                # this begins the while true loop of saving data
                userinput = input(
                    "If you like this person type y, if not type n, then press enter, if you want to quit out of training press enter without typing anything: "
                )
                if userinput.strip().lower() not in ["y", "n"]:
                    break
                # first save all of this data in the data folder
                else:
                    profile = BM.find_download_all_pictures(driver, datafp)
                    if userinput.strip().lower() == "y":
                        # send a like to that person
                        BM.like_profile(driver)
                        # add that this person was liked
                        csvsessdata.write(f"{profile},positive\n")
                    else:
                        BM.dislike_profile(driver)
                        csvsessdata.write(f"{profile},negetive\n")
            # This is what happens when the while loop is exited
            print("Now exiting")
            driver.close()
            csvsessdata.close()
            exit()
        else:
            print("Sorry you gotta logging")
            driver.close()
    except Exception as e:
        print("Sorry something went wrong")
        print(str(e))


if __name__ == "__main__":
    main_scrapping_app()
