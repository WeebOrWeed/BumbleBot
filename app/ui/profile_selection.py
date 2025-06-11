import tkinter as tk
import os
from PIL import Image, ImageTk
import utils.utilities as UM

class ProfileSelectionPage(tk.Frame):
    def __init__(self, parent, weightfolder, modelpath, on_profile_selected):
        super().__init__(parent, bg="#a259c6")  # Match AuthUI theme
        print("[DEBUG] ProfileSelectionPage initialized")
        self.weightfolder = weightfolder
        self.modelpath = modelpath
        self.on_profile_selected = on_profile_selected
        self.profile_select_buttons = {}
        self.profile_select_shades = {}
        self.profile_select_shade_images = {}
        self.selected_profile_name = None
        self.input_frame = None  # Track the input frame for new profile
        self.card = tk.Frame(self, bg="white", bd=2, relief="groove")
        self.card.place(relx=0.5, rely=0.5, anchor="center", width=520, height=320)
        tk.Label(self.card, text="SELECT PROFILE", font=("Arial", 15, "bold"), fg="#2a6cf6", bg="white").pack(pady=(20, 5))

        # Container frame for scrollable area and continue button
        content_frame = tk.Frame(self.card, bg="white")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10)

        # Always create the scrollable area for profiles (grey background)
        if not os.path.exists(self.weightfolder):
            os.makedirs(self.weightfolder, exist_ok=True)
        self.canvas = tk.Canvas(content_frame, bg="#f5f5f5", highlightthickness=0, width=500, height=180)
        self.scrollbar = tk.Scrollbar(content_frame, orient="vertical", command=self.canvas.yview)
        self.profiles_row = tk.Frame(self.canvas, bg="#f5f5f5")
        self.profiles_row_id = self.canvas.create_window((self.canvas.winfo_reqwidth() // 2, 0), window=self.profiles_row, anchor="n")
        def _center_profiles_row(event):
            self.canvas.coords(self.profiles_row_id, event.width // 2, 0)
        self.canvas.bind("<Configure>", _center_profiles_row)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20)
        self.scrollbar.pack_forget()
        def update_scrollregion(event=None):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            bbox = self.canvas.bbox("all")
            if bbox:
                content_height = bbox[3] - bbox[1]
                canvas_height = self.canvas.winfo_height()
                if content_height <= canvas_height:
                    self.canvas.yview_moveto(0)
                    self.canvas.unbind_all("<MouseWheel>")
                    self.canvas.unbind_all("<Button-4>")
                    self.canvas.unbind_all("<Button-5>")
                else:
                    self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
                    self.canvas.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
                    self.canvas.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))
        self.profiles_row.bind("<Configure>", update_scrollregion)
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        # Always call render_profiles (even if no profiles)
        self.render_profiles()

        # Continue button in a separate frame at the bottom
        button_frame = tk.Frame(self.card, bg="white")
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, 20))
        self.continue_btn = tk.Button(button_frame, text="Continue", font=("Arial", 12), bg="#2a6cf6", fg="white", width=12, height=1, state=tk.DISABLED, command=self.on_continue)
        self.continue_btn.pack(pady=(5, 0))

    def make_circular_shade(self, size=48, color=(162, 89, 198, 128)):
        # No longer need to create an image, we'll draw directly on canvas
        return color

    def render_profiles(self, select_name=None):
        if not os.path.exists(self.weightfolder):
            os.makedirs(self.weightfolder, exist_ok=True)
        for widget in self.profiles_row.winfo_children():
            widget.destroy()
        profiles = [fname for fname in sorted(os.listdir(self.weightfolder)) if os.path.isdir(os.path.join(self.weightfolder, fname))]
        max_per_row = 5
        profile_idx = 0
        row = 0
        col = 0
        if not profiles:
            # Only plus sign in the first cell
            plus_frame = tk.Frame(self.profiles_row, width=80, height=110, bg="#f5f5f5")
            plus_frame.grid_propagate(False)
            plus_frame.grid(row=row, column=col, padx=3, pady=5)
            plus_icon = tk.Canvas(plus_frame, width=64, height=64, bg="#f5f5f5", highlightthickness=0)
            plus_icon.place(x=8, y=0, width=64, height=64)
            plus_icon.create_text(32, 32, text="+", font=("Arial", 32, "bold"), fill="black")
            plus_icon.bind("<Button-1>", lambda e: self.show_new_profile_popup())
            tk.Label(plus_frame, text="New Profile", font=("Arial", 10), bg="#f5f5f5", wraplength=76, justify="center").place(relx=0.5, y=72, anchor="n", width=76)
            return
        def select_profile(profile_name):
            if self.input_frame:
                if self.input_frame is not None:
                    try:
                        self.input_frame.destroy()
                    except Exception:
                        pass
                    self.input_frame = None
                if getattr(self, "plus_btn", None):
                    try:
                        self.plus_btn.config(state=tk.NORMAL)
                    except tk.TclError:
                        pass
            # Redraw all icons as unselected
            for name, draw_icon in self.profile_select_shades.items():
                draw_icon(False)
            # Draw selected icon as selected
            if profile_name in self.profile_select_shades:
                self.profile_select_shades[profile_name](True)
            self.selected_profile_name = profile_name
            self.continue_btn.config(state=tk.NORMAL)
        # Determine if plus button should be included in the last row
        n_profiles = len(profiles)
        n_full_rows = n_profiles // max_per_row
        n_last_row_profiles = n_profiles % max_per_row
        include_plus_in_last_row = (n_last_row_profiles != 0)
        total_rows = n_full_rows + (1 if n_last_row_profiles or not profiles else 0)
        for row in range(total_rows):
            is_last_row = (row == total_rows - 1 and include_plus_in_last_row)
            if is_last_row:
                row_profiles = profiles[profile_idx:profile_idx + n_last_row_profiles]
                row_plus = True
            else:
                row_profiles = profiles[profile_idx:profile_idx + max_per_row]
                row_plus = False
            n_row_items = len(row_profiles) + (1 if row_plus else 0)
            if is_last_row:
                left_spacers = 0
                right_spacers = max_per_row - n_row_items
            else:
                n_spacers = max_per_row - n_row_items
                left_spacers = n_spacers // 2
                right_spacers = n_spacers - left_spacers
            col = 0
            # Add left spacers
            for _ in range(left_spacers):
                spacer = tk.Frame(self.profiles_row, width=80, height=110, bg="#f5f5f5")
                spacer.grid_propagate(False)
                spacer.grid(row=row, column=col, padx=3, pady=5)
                col += 1
            # Add profile cells
            for profile_name in row_profiles:
                cell_frame = tk.Frame(self.profiles_row, width=80, height=110, bg="#f5f5f5")
                cell_frame.grid_propagate(False)
                cell_frame.grid(row=row, column=col, padx=3, pady=5)
                icon_canvas = tk.Canvas(cell_frame, width=64, height=64, bg="#f5f5f5", highlightthickness=0)
                icon_canvas.place(x=8, y=0, width=64, height=64)
                def make_draw_icon(profile_name, icon_canvas=icon_canvas):
                    def draw(selected):
                        icon_canvas.delete("all")
                        if selected:
                            icon_canvas.create_oval(0, 0, 64, 64, fill="#a259c6", stipple="gray50", outline="")
                            icon_canvas.create_text(32, 32, text=profile_name[0].upper(), font=("Arial", 22, "bold"), fill="white")
                        else:
                            icon_canvas.create_oval(0, 0, 64, 64, fill="#f5f5f5", outline="#e0e0e0", width=2)
                            icon_canvas.create_text(32, 32, text=profile_name[0].upper(), font=("Arial", 22, "bold"), fill="black")
                    return draw
                draw_icon = make_draw_icon(profile_name, icon_canvas)
                icon_canvas.bind("<Button-1>", lambda e, n=profile_name: select_profile(n))
                self.profile_select_buttons[profile_name] = icon_canvas
                self.profile_select_shades[profile_name] = draw_icon
                label = tk.Label(cell_frame, text=profile_name, font=("Arial", 10), bg="#f5f5f5", wraplength=76, justify="center")
                label.place(relx=0.5, y=72, anchor="n", width=76)
                col += 1
            # Add plus button if needed
            if row_plus:
                plus_frame = tk.Frame(self.profiles_row, width=80, height=110, bg="#f5f5f5")
                plus_frame.grid_propagate(False)
                plus_frame.grid(row=row, column=col, padx=3, pady=5)
                plus_icon = tk.Canvas(plus_frame, width=64, height=64, bg="#f5f5f5", highlightthickness=0)
                plus_icon.place(x=8, y=0, width=64, height=64)
                plus_icon.create_text(32, 32, text="+", font=("Arial", 32, "bold"), fill="black")
                plus_icon.bind("<Button-1>", lambda e: self.show_new_profile_popup())
                tk.Label(plus_frame, text="New Profile", font=("Arial", 10), bg="#f5f5f5", wraplength=76, justify="center").place(relx=0.5, y=72, anchor="n", width=76)
                col += 1
            # Add right spacers
            for _ in range(right_spacers):
                spacer = tk.Frame(self.profiles_row, width=80, height=110, bg="#f5f5f5")
                spacer.grid_propagate(False)
                spacer.grid(row=row, column=col, padx=3, pady=5)
                col += 1
            profile_idx += max_per_row if not row_plus else n_last_row_profiles
        # If the last row is full, add a new row with only the plus button, left-aligned
        if n_last_row_profiles == 0:
            row = total_rows
            col = 0
            plus_frame = tk.Frame(self.profiles_row, width=80, height=110, bg="#f5f5f5")
            plus_frame.grid_propagate(False)
            plus_frame.grid(row=row, column=col, padx=3, pady=5)
            plus_icon = tk.Canvas(plus_frame, width=64, height=64, bg="#f5f5f5", highlightthickness=0)
            plus_icon.place(x=8, y=0, width=64, height=64)
            plus_icon.create_text(32, 32, text="+", font=("Arial", 32, "bold"), fill="black")
            plus_icon.bind("<Button-1>", lambda e: self.show_new_profile_popup())
            tk.Label(plus_frame, text="New Profile", font=("Arial", 10), bg="#f5f5f5", wraplength=76, justify="center").place(relx=0.5, y=72, anchor="n", width=76)
        # If a profile should be selected after render (e.g., after creation)
        if select_name and select_name in self.profile_select_buttons:
            select_profile(select_name)
        else:
            # Draw all as unselected by default
            for name, draw_icon in self.profile_select_shades.items():
                draw_icon(False)
        # Explicitly update scrollregion after rendering
        self.profiles_row.event_generate('<Configure>')

    def show_new_profile_popup(self):
        # No overlay, just show the popup
        popup = tk.Toplevel(self)
        popup.title("Create New Profile")
        popup.iconbitmap(UM.resource_path("BumbleBotLogo.ico"))
        popup.geometry("320x320")
        popup.transient(self)
        popup.grab_set()
        popup.resizable(False, False)
        popup.configure(bg="#faf9fb")
        # Center the popup over the profile page
        self.update_idletasks()
        px = self.winfo_rootx() + (self.winfo_width() // 2) - 160
        py = self.winfo_rooty() + (self.winfo_height() // 2) - 160
        popup.geometry(f"320x320+{px}+{py}")

        # Modern circular user icon
        icon_canvas = tk.Canvas(popup, width=90, height=90, bg="#faf9fb", highlightthickness=0)
        icon_canvas.pack(pady=(24, 10))
        icon_canvas.create_oval(5, 5, 85, 85, fill="#a259c6", outline="")
        icon_canvas.create_text(45, 45, text="+", font=("Arial", 44, "bold"), fill="white")

        # Title and subtitle
        tk.Label(popup, text="Create Your Profile", font=("Arial", 18, "bold"), bg="#faf9fb", fg="#222").pack(pady=(0, 2))
        tk.Label(popup, text="Enter a profile name", font=("Arial", 11), bg="#faf9fb", fg="#888").pack(pady=(0, 18))

        MAX_PROFILE_NAME_LEN = 16
        # Modern rounded entry
        entry_frame = tk.Frame(popup, bg="#faf9fb")
        entry_frame.pack(pady=(0, 18))
        entry = tk.Entry(entry_frame, font=("Arial", 13), width=18, bg="#f5f5f5", relief="flat", highlightthickness=1, highlightbackground="#e0e0e0")
        entry.pack(ipady=8, padx=8)
        entry.focus_set()
        def on_entry_key(event):
            value = entry.get()
            if len(value) >= MAX_PROFILE_NAME_LEN and event.keysym not in ("BackSpace", "Delete", "Left", "Right"):
                return "break"
        entry.bind('<KeyPress>', on_entry_key)

        def on_create():
            name = entry.get().strip()
            if not name:
                return
            if len(name) > MAX_PROFILE_NAME_LEN:
                import tkinter.messagebox as messagebox
                messagebox.showwarning("Name Too Long", f"Profile name cannot exceed {MAX_PROFILE_NAME_LEN} characters.")
                entry.focus_set()
                return
            if name in [fname for fname in os.listdir(self.weightfolder) if os.path.isdir(os.path.join(self.weightfolder, fname))]:
                import tkinter.messagebox as messagebox
                messagebox.showwarning("Profile Exists", f"A profile named '{name}' already exists. Please choose a different name.")
                entry.focus_set()
                return
            full_name = name + ".h5"
            full_path = os.path.normpath(os.path.join(self.weightfolder, name, full_name))
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            open(full_path, "a").close()
            popup.destroy()
            self.render_profiles(select_name=name)
            self.after(50, lambda: self.scroll_to_profile(name))
        entry.bind('<Return>', lambda event: on_create())

        # Modern rounded Create button
        create_btn = tk.Button(popup, text="Create", font=("Arial", 13, "bold"), command=on_create,
                               bg="#7c3aed", fg="white", activebackground="#a259c6", activeforeground="white",
                               relief="flat", bd=0, padx=10, pady=8)
        create_btn.pack(ipady=6, ipadx=30, pady=(0, 18))
        create_btn.configure(cursor="hand2")
        create_btn.bind("<Enter>", lambda e: create_btn.config(bg="#a259c6"))
        create_btn.bind("<Leave>", lambda e: create_btn.config(bg="#7c3aed"))

        popup.protocol("WM_DELETE_WINDOW", lambda: popup.destroy())

    def on_continue(self):
        if self.selected_profile_name:
            profile_folder = os.path.join(self.weightfolder, self.selected_profile_name)
            self.on_profile_selected(profile_folder)

    def scroll_to_profile(self, profile_name):
        icon_canvas = self.profile_select_buttons.get(profile_name)
        if icon_canvas:
            self.canvas.update_idletasks()
            # Get the y position of the icon_canvas relative to the canvas
            try:
                y = icon_canvas.winfo_rooty() - self.canvas.winfo_rooty() + self.canvas.canvasy(0) - 48  # Scroll even higher to show icon
                canvas_height = self.canvas.winfo_height()
                self.canvas.yview_moveto(max(0, y / max(1, self.canvas.bbox(self.profiles_row_id)[3] - canvas_height)))
            except Exception:
                pass 

    def destroy(self):
        if hasattr(self, 'canvas'):
            self.canvas.unbind_all("<MouseWheel>")
            self.canvas.unbind_all("<Button-4>")
            self.canvas.unbind_all("<Button-5>")
        super().destroy() 