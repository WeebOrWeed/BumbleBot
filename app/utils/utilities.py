import json
import os
from pathlib import Path

def load_settings():
    settings_path = Path(__file__).parent / "settings.json"
    setf = open(settings_path, "r")
    settings = json.load(setf)
    return settings
