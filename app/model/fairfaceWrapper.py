from .fairface import fairface as PD
import sys
from pathlib import Path

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

# BASE_DIR now refers to the directory containing the executable
BASE_DIR_EXE = get_executable_dir_path()

FAIRFACE_PATH = (BASE_DIR_EXE / "model" / "fairface").resolve()
sys.path.insert(0, FAIRFACE_PATH)
def init_models():
    PD.init_models()

def predict(image):
    return PD.predict(image)