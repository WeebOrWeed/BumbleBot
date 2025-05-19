# this method loads all the files and then based on the markers it switches between all the files
from ui.ui import MainUI
import os
import tkinter as tk
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
WEIGHT_FOLDER = (BASE_DIR / "weights").resolve()
def main():
    if not os.path.exists(WEIGHT_FOLDER):
        os.makedirs(WEIGHT_FOLDER)

    app = MainUI()
    app.mainloop()


if __name__ == "__main__":
    main()