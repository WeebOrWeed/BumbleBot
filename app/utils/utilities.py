import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SETTINGS_PATH = (BASE_DIR / ".." / "config" / "settings.json").resolve()
def load_settings():
    setf = open(os.path.join(os.getcwd(), SETTINGS_PATH), "r")
    settings = json.load(setf)
    return settings
