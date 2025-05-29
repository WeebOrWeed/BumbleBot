# this method loads all the files and then based on the markers it switches between all the files
from ui.ui import Application
import os
import tkinter as tk
from pathlib import Path
from utils import utilities as UM
import json
import sys

def get_executable_dir_path(relative_path=""):
    """
    Get the absolute path to a file or folder located relative to the executable.
    Works for both development and compiled PyInstaller executables.
    """
    if getattr(sys, 'frozen', False):
        # We are running in a bundle (PyInstaller)
        # sys.executable is the path to the .exe itself (e.g., D:\BumbleBot\app\dist\BumbleBot.exe)
        executable_dir = Path(sys.executable).parent # This gives you D:\BumbleBot\app\dist\
    else:
        # We are running in a normal Python environment (development)
        # __file__ is the path to the script (e.g., C:\YourProject\main.py)
        executable_dir = Path(__file__).resolve().parent # This gives you C:\YourProject\
        # You might need to adjust this for development if your 'configs', 'images', 'weights'
        # folders are relative to a different part of your project structure than main.py
        # For example, if main.py is in 'app/', and these folders are in the project root:
        # executable_dir = Path(__file__).resolve().parents[1] # Go up two levels from main.py

    return (executable_dir / relative_path).resolve()

# BASE_DIR now refers to the directory containing the executable
BASE_DIR_EXE = get_executable_dir_path()

# Use get_executable_dir_path for folders next to the EXE
WEIGHT_FOLDER = get_executable_dir_path("weights")
SETTINGS_PATH = get_executable_dir_path(os.path.join("configs", "settings.json"))

def main():
    if not os.path.exists(WEIGHT_FOLDER):
        os.makedirs(WEIGHT_FOLDER)

    settings = UM.load_settings()
    settings["BASE_DIR"] = str(BASE_DIR_EXE)
    with open(SETTINGS_PATH, "w") as f:
        json.dump(settings, f, indent=4)
    app = Application()
    app.mainloop()

try:
    if __name__ == "__main__":
        main()
except Exception as e:
    print("\n--- UNHANDLED EXCEPTION ---")
    print(f"Error type: {type(e).__name__}")
    print(f"Error message: {e}")
finally:
    print("BumbleBot exited.")