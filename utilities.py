import json
import os


def load_settings():
    setf = open(os.path.join(os.getcwd(), "settings.json"), "r")
    settings = json.load(setf)
    return settings
