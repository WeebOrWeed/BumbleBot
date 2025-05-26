from .fairface import fairface as PD
import sys
from pathlib import Path

# adding FairFace to the system path
BASE_DIR = Path(__file__).resolve().parent
FAIRFACE_PATH = (BASE_DIR / "fairface").resolve()
sys.path.insert(0, FAIRFACE_PATH)
def init_models():
    PD.init_models()

def predict(image):
    return PD.predict(image)