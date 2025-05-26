import json
from pathlib import Path

def load_settings():
    settings_path = Path(__file__).parent.parent / "configs" / "settings.json"
    setf = open(settings_path, "r")
    settings = json.load(setf)
    return settings
