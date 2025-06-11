import tkinter as tk
from cefpython3 import cefpython as cef
import sys
from ui.swipe_status import SwipeStatusPage

class SwipeCompositePage(tk.Frame):
    def __init__(self, parent, on_back):
        super().__init__(parent, bg="#a259c6")
        self.parent = parent
        self.on_back = on_back
        self.browser_frame = None
        self.cef_initialized = False
        self._cef_loop_running = True

        # Left: CEF browser (wider)
        self.browser_container = tk.Frame(self, bg="white", width=700, height=600)
        self.browser_container.pack_propagate(False)
        self.browser_container.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 0))
        
        # Right: Status panel (fixed width)
        self.status_page = SwipeStatusPage(self, on_back=self.on_back)
        self.status_page.config(width=370, height=600)
        self.status_page.pack_propagate(False)
        self.status_page.pack(side=tk.LEFT, fill=tk.Y)

        self.after(100, self.embed_cef)

    def embed_cef(self):
        if not self.cef_initialized:
            self.cef_initialized = True
            sys.excepthook = cef.ExceptHook  # To shutdown all CEF processes on error
            self.browser_frame = BrowserFrame(self.browser_container, self.parent)
            self.browser_frame.pack(fill=tk.BOTH, expand=True)
            self.after(10, self.cef_loop)

    def cef_loop(self):
        if not self._cef_loop_running:
            return
        if self.browser_frame:
            self.browser_frame.cef_notify_resize()
        cef.MessageLoopWork()
        self.after(10, self.cef_loop)

    def destroy(self):
        self._cef_loop_running = False
        if self.browser_frame:
            self.browser_frame.destroy()
        super().destroy()

    def get_cef_browser(self):
        return self.browser_frame.browser if self.browser_frame else None

class BrowserFrame(tk.Frame):
    def __init__(self, master, main_ui):
        super().__init__(master, bg="#222")
        self.main_ui = main_ui
        self.browser = None
        self._needs_notify_resize = False
        self.bind("<Configure>", self.on_configure)
        toplevel = self.winfo_toplevel()
        toplevel.bind("<Configure>", self.on_main_configure)
        self.after(0, self.embed_browser)

    def embed_browser(self):
        if self.browser is None:
            self.main_ui.state('zoomed')  # Maximize window (Windows)
            window_info = cef.WindowInfo()
            rect = [self.winfo_rootx(), self.winfo_rooty(),
                    self.winfo_rootx() + self.winfo_width(),
                    self.winfo_rooty() + self.winfo_height()]
            window_info.SetAsChild(self.winfo_id(), rect)
            self.browser = cef.CreateBrowserSync(window_info, url="https://bumble.com/app")
            # self.browser.SetZoomLevel(-1)  # Make content smaller
            self.browser.ExecuteJavascript("""
                document.body.style.background = 'white';
                document.body.style.margin = '0';
                document.body.style.padding = '0';
                document.documentElement.style.margin = '0';
                document.documentElement.style.padding = '0';
            """)
            self.focus_set()
            self.main_ui.state('normal')
            self.main_ui.geometry("950x750")

    def on_configure(self, event):
        if self.browser:
            if sys.platform == "win32":
                ctypes = __import__('ctypes')
                ctypes.windll.user32.SetWindowPos(self.browser.GetWindowHandle(), 0,
                                                  0, 0, event.width, event.height, 0x0002)
            else:
                self.browser.SetBounds(0, 0, event.width, event.height)
            self._needs_notify_resize = True

    def on_main_configure(self, event):
        self._needs_notify_resize = True

    def cef_notify_resize(self):
        if self.browser and self._needs_notify_resize:
            self.browser.NotifyMoveOrResizeStarted()
            self._needs_notify_resize = False

    def destroy(self):
        if self.browser:
            self.browser.CloseBrowser(True)
            self.browser = None
        super().destroy() 