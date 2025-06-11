import tkinter as tk
from automation import makePredictions as MP
from ui.swipe_controller import SwipeController

class SwipeStatusPage(tk.Frame):
    def __init__(self, parent, on_back):
        super().__init__(parent, bg="#a259c6")  # Match AuthUI theme
        self.on_back = on_back
        self.continue_callback = None
        self.parent = parent
        
        # Create card frame
        self.card = tk.Frame(self, bg="white", bd=0, highlightthickness=0, height=220)
        self.card.pack(fill=tk.X, anchor="n", padx=(10, 0), pady=(50, 0))
        
        # Back button
        back_btn = tk.Button(self.card, text="← Back", font=("Arial", 12), bg="#e9eef6", relief="flat", command=self._on_back_and_stop, cursor="hand2")
        back_btn.place(relx=0.02, rely=0.01, anchor="nw")
        
        # Status label
        self.status_label = tk.Label(self.card, text="", font=("Arial", 12), bg="white", fg="#222", wraplength=380, justify=tk.LEFT)
        self.status_label.place(relx=0.5, rely=0.3, anchor="center")
        
        # Continue button
        self.continue_btn = tk.Button(self.card, text="Continue", font=("Arial", 14, "bold"), width=16, height=2, 
                                    bg="#4CAF50", fg="white", relief="flat", bd=0, cursor="hand2",
                                    command=self._on_continue)
        self.continue_btn.place(relx=0.5, rely=0.5, anchor="center")
        
        # Stop button (initially hidden)
        self.stop_btn = tk.Button(self.card, text="Stop", font=("Arial", 14, "bold"), width=16, height=2,
                                bg="#AF4C4C", fg="white", relief="flat", bd=0, cursor="hand2",
                                command=self._on_stop)
        self.stop_btn.place(relx=0.5, rely=0.5, anchor="center")
        self.stop_btn.place_forget()
        
        # Start the swiping process
        self._start_swiping()
    
    def _start_swiping(self):
        """Start the swiping process when the browser is ready"""
        def try_start():
            cef_browser = self.master.get_cef_browser() if hasattr(self.master, 'get_cef_browser') else None
            if cef_browser is not None:
                print("[DEBUG] Starting swiping controller")
                self.controller = SwipeController(
                    browser=cef_browser,
                    set_status=self._update_status,
                    show_continue=self._show_continue,
                    show_stop=self._show_stop,
                    set_continue_callback=self._set_continue_callback,
                    set_stop_callback=self._set_stop_callback
                )
                self.controller.start()
            else:
                self.after(100, try_start)  # Try again in 100ms
        print("[DEBUG] Starting to try start swiping")
        self.after(100, try_start)  # Delay the first call to try_start
    
    def _update_status(self, text):
        """Update the status label text in a thread-safe way"""
        def do_update():
            try:
                if self.status_label.winfo_exists():
                    self.status_label.config(text=text)
            except tk.TclError:
                pass  # Widget was destroyed, ignore
        self.after(0, do_update)
    
    def _show_continue(self):
        def do_show():
            try:
                if self.continue_btn.winfo_exists():
                    self.continue_btn.place(relx=0.5, rely=0.5, anchor="center")
                    self.stop_btn.place_forget()
            except tk.TclError:
                pass
        self.after(0, do_show)
    
    def _show_stop(self):
        def do_show():
            try:
                if self.stop_btn.winfo_exists():
                    self.stop_btn.place(relx=0.5, rely=0.5, anchor="center")
                    self.continue_btn.place_forget()
                    # Restore stop button to original state
                    self.stop_btn.config(state=tk.NORMAL, bg="#AF4C4C", fg="white", activebackground="#AF4C4C", activeforeground="white", width=16, height=2)
            except tk.TclError:
                pass
        self.after(0, do_show)
    
    def _set_continue_callback(self, callback):
        """Set the continue button callback and enable the button"""
        self.continue_btn.config(command=callback, state=tk.NORMAL)
    
    def _set_stop_callback(self, callback):
        """Set the stop button callback, but wrap it to update UI first"""
        def wrapped_stop():
            self.stop_btn.config(state=tk.DISABLED, bg="#cccccc", fg="#888888", activebackground="#cccccc", activeforeground="#888888")
            self._update_status("Stopping...")
            self.update_idletasks()
            callback()
        self.stop_btn.config(command=wrapped_stop)
    
    def _on_continue(self):
        if self.continue_callback:
            self.continue_callback()
        else:
            self._show_stop()
    
    def _on_stop(self):
        """Handle stop button click"""
        return
        #self.stop_btn.config(state=tk.DISABLED, bg="#cccccc", fg="#888888", activebackground="#cccccc", activeforeground="#888888", width=32, height=4)
        #self._update_status("Stopping...")
        #self.update_idletasks()
    
    def _on_back_and_stop(self):
        # Stop swiping if running, then go back
        if hasattr(self, 'stop_btn') and self.stop_btn['command']:
            self.stop_btn.invoke()  # This will call the stop callback if set
        self.on_back()
    
    def _on_return(self):
        self.on_back() 