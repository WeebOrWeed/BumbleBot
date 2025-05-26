# test_app.py (simplified to isolate _tkinter)
import sys
import time
import traceback
import os
import tkinter as tk # Only this Tkinter import

try:
    print("Hello from test_app.py!")
    print(f"Python version: {sys.version}")
    print(f"Current working directory: {os.getcwd()}")
    if hasattr(sys, '_MEIPASS'):
        print(f"Running from PyInstaller temp path: {sys._MEIPASS}")
    else:
        print("Not running from PyInstaller bundle.")
    time.sleep(5) # Keep the console open for 5 seconds
    print("Exiting test_app.py.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
    traceback.print_exc()
finally:
    print("\nPress Enter to exit the test app...")
    input()