# this method loads all the files and then based on the markers it switches between all the files
from ui.ui import Application
import os
import tkinter as tk
from pathlib import Path
from utils import utilities as UM
import json

BASE_DIR = Path(__file__).resolve().parent
WEIGHT_FOLDER = (BASE_DIR / "weights").resolve()
SETTINGS_PATH = (BASE_DIR / "configs" / "settings.json").resolve()
def main():
    if not os.path.exists(WEIGHT_FOLDER):
        os.makedirs(WEIGHT_FOLDER)

    settings = UM.load_settings()
    settings["BASE_DIR"] = str(BASE_DIR)
    with open(SETTINGS_PATH, "w") as f:
        json.dump(settings, f, indent=4)
    app = Application()
    app.mainloop()

try:
    if __name__ == "__main__":
        print("Trying")
        main()
    else:
        print("Name not right")
except Exception as e:
    print("\n--- UNHANDLED EXCEPTION ---")
    print(f"Error type: {type(e).__name__}")
    print(f"Error message: {e}")
finally:
    print("\nPress Enter to close this console window...")
    input()