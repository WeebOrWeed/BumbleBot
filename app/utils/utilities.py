import json
from pathlib import Path
import sys
import os

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
        executable_dir = Path(__file__).resolve().parent.parent # This gives you C:\YourProject\
        # You might need to adjust this for development if your 'configs', 'images', 'weights'
        # folders are relative to a different part of your project structure than main.py
        # For example, if main.py is in 'app/', and these folders are in the project root:
        # executable_dir = Path(__file__).resolve().parents[1] # Go up two levels from main.py

    return (executable_dir / relative_path).resolve()

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # If not running as a bundled executable (e.g., during development)
        # Assume relative_path is relative to the script's directory (app/)
        base_path = Path(__file__).resolve().parent.parent

    return os.path.join(base_path, relative_path)

# BASE_DIR now refers to the directory containing the executable
BASE_DIR_EXE = get_executable_dir_path()

def load_settings():
    settings_path = BASE_DIR_EXE / "configs" / "settings.json"
    setf = open(settings_path, "r")
    settings = json.load(setf)
    return settings
