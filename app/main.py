# this method loads all the files and then based on the markers it switches between all the files
from ui.auth_ui import AuthUI
from ui.auth_ui import MainUI
import os
import tkinter as tk
from pathlib import Path
from utils import utilities as UM
import json

BASE_DIR = Path(__file__).resolve().parent
WEIGHT_FOLDER = (BASE_DIR / "weights").resolve()
SETTINGS_PATH = (BASE_DIR / "utils" / "settings.json").resolve()
def main():
    if not os.path.exists(WEIGHT_FOLDER):
        os.makedirs(WEIGHT_FOLDER)

    settings = UM.load_settings()
    settings["BASE_DIR"] = str(BASE_DIR)
    with open(SETTINGS_PATH, "w") as f:
        json.dump(settings, f, indent=4)
    auth_app = AuthUI()
    auth_app.mainloop()
    if auth_app.open_bumble_bot:
        bumblebot_app = MainUI()
        bumblebot_app.mainloop()


if __name__ == "__main__":
    main()