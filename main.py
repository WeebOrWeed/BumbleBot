# this method loads all the files and then based on the markers it switches between all the files
import sys
import trainingDataCollector as TC
import trainer as TRN
import makePredictions as MP


modes = {"SCRAPE":"Scrape data so that you can train a model. Opens up bumble for you and you get swipe and get data",
"TRAIN":"Trains the model based on a given data set",
"SWIPE":"Auto-swipe on bumble based on the machine learning model that has been created",
"HELP":"Prints out all the help associated with the bot"}

def main(MODE):
    if MODE == "HELP":
        print("Here is what you can do: ")
        for i in modes:
            print(f"{i}: {modes[i]}")
    elif MODE == "SCRAPE":
        TC.main_scrapping_app()
    elif MODE == "TRAIN":
        TRN.main_trainning_app()
    elif MODE == "SWIPE":
        MP.make_predictions()


if __name__ == "__main__":
    try:
        mode = sys.argv[1]
        if mode in modes:
            main(mode)
        else:
            print("Sorry that was not a recognized mode please type HELP to show all possible modes")
    except Exception as e:
        print("You must pass in an argument, type HELP to view all possible options")