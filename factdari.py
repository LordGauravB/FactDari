#FactDari.py - Simple Fact Viewer Application
import os
import sys
import signal
import atexit
import config
import ctypes
import pyodbc
import pyttsx3
import webbrowser
import subprocess
import tkinter as tk
import random
import threading
from ctypes import wintypes
from PIL import Image, ImageTk
from datetime import datetime, timedelta
from tkinter import ttk, simpledialog, messagebox

class ToolTip:
    """Lightweight tooltip for Tk widgets."""
    def __init__(self, widget, text, delay=400):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tipwindow = None
        self._after_id = None
        widget.bind("<Enter>", self._schedule)
        widget.bind("<Leave>", self._hide)
        widget.bind("<ButtonPress>", self._hide)

    def _schedule(self, event=None):
        self._cancel()
        self._after_id = self.widget.after(self.delay, self._show)

    def _cancel(self):
        if self._after_id:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _show(self, event=None):
        if self.tipwindow or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert") if self.widget.winfo_viewable() else (0, 0, 0, 0)
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify='left',
                         background="#333333", foreground="#ffffff",
                         relief='solid', borderwidth=1,
                         font=("Trebuchet MS", 9))
        label.pack(ipadx=6, ipady=3)

    def _hide(self, event=None):
        self._cancel()
        if self.tipwindow:
            try:
                self.tipwindow.destroy()
            except Exception:
                pass
            self.tipwindow = None

class FactDariApp:
    def __init__(self):
        # Get database connection string from config
        self.CONN_STR = config.get_connection_string()
        
        # Get UI configurations
        self.WINDOW_WIDTH = config.UI_CONFIG['window_width']
        self.WINDOW_HEIGHT = config.UI_CONFIG['window_height']
        self.WINDOW_STATIC_POS = config.UI_CONFIG['window_static_pos']
        self.POPUP_POSITION = config.UI_CONFIG['popup_position']
        self.POPUP_ADD_CARD_SIZE = config.UI_CONFIG['popup_add_card_size']
        self.POPUP_EDIT_CARD_SIZE = config.UI_CONFIG['popup_edit_card_size']
        self.POPUP_CATEGORIES_SIZE = config.UI_CONFIG['popup_categories_size']
        self.POPUP_INFO_SIZE = config.UI_CONFIG.get('popup_info_size', "420x480")
        self.POPUP_CONFIRM_SIZE = config.UI_CONFIG.get('popup_confirm_size', "360x180")
        self.POPUP_RENAME_SIZE = config.UI_CONFIG.get('popup_rename_size', "420x200")
        self.CORNER_RADIUS = config.UI_CONFIG['corner_radius']
        
        # Colors
        self.BG_COLOR = config.UI_CONFIG['bg_color']
        self.TITLE_BG_COLOR = config.UI_CONFIG['title_bg_color']
        self.LISTBOX_BG_COLOR = config.UI_CONFIG['listbox_bg_color']
        self.TEXT_COLOR = config.UI_CONFIG['text_color']
        self.GREEN_COLOR = config.UI_CONFIG['green_color']
        self.BLUE_COLOR = config.UI_CONFIG['blue_color']
        self.RED_COLOR = config.UI_CONFIG['red_color']
        self.YELLOW_COLOR = config.UI_CONFIG['yellow_color']
        self.GRAY_COLOR = config.UI_CONFIG['gray_color']
        self.STATUS_COLOR = config.UI_CONFIG['status_color']
        
        # Fonts
        self.TITLE_FONT = config.get_font('title')
        self.NORMAL_FONT = config.get_font('normal')
        self.SMALL_FONT = config.get_font('small')
        self.LARGE_FONT = config.get_font('large')
        self.STATS_FONT = config.get_font('stats')
        
        # Instance variables
        self.x_window = 0
        self.y_window = 0
        self.current_fact_id = None
        self.is_home_page = True
        self.all_facts = []  # Store all facts for navigation
        self.current_fact_index = 0
        self.current_fact_is_favorite = False  # Track if current fact is a favorite
        self.current_fact_is_easy = False  # Track if current fact is known/easy
        # Speech state
        self.speech_engine = pyttsx3.init()
        self.speaking_thread = None

        # Timing/session state
        self.current_session_id = None
        self.session_start_time = None
        self.current_fact_start_time = None
        self.current_review_log_id = None
        # Inactivity tracking
        self.idle_timeout_seconds = getattr(config, 'IDLE_TIMEOUT_SECONDS', 300)
        self.idle_end_session = getattr(config, 'IDLE_END_SESSION', True)
        self.idle_navigate_home = getattr(config, 'IDLE_NAVIGATE_HOME', True)
        self.last_activity_time = datetime.now()
        self.idle_triggered = False
        
        # Create main window
        self.root = tk.Tk()
        self.root.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}")
        self.root.overrideredirect(True)
        self.root.configure(bg=self.BG_COLOR)

        # Ensure DB schema supports sessions + durations
        try:
            self.ensure_schema()
        except Exception as _:
            # Non-fatal: app can still run without migrations
            pass
        
        # Set up UI elements
        self.setup_ui()
        
        # Set initial transparency
        self.root.attributes('-alpha', 0.9)
        
        # Bind events
        self.bind_events()
        
        # Final setup
        self.root.update_idletasks()
        self.apply_rounded_corners()
        self.set_static_position()
        self.update_coordinates()
        self.root.after(250, self.update_ui)

        # Show the home page
        self.show_home_page()

        # Ensure we close any active session at process exit
        try:
            atexit.register(self.end_active_session)
        except Exception:
            pass
    
    def load_categories(self):
        """Load categories for the dropdown"""
        query = "SELECT DISTINCT CategoryName FROM Categories WHERE IsActive = 1 ORDER BY CategoryName"
        categories = self.fetch_query(query)
        base_categories = [category[0] for category in categories] if categories else []

        # Build header filters deterministically
        header = ["All Categories", "Favorites"]
        try:
            has_is_easy = self.column_exists('Facts', 'IsEasy')
        except Exception:
            has_is_easy = False
        if has_is_easy:
            header += ["Known", "Not Known"]
        header += ["Not Favorite"]
        return header + base_categories

    def setup_ui(self):
        """Set up all UI elements"""
        # Title bar
        self.title_bar = tk.Frame(self.root, bg=self.TITLE_BG_COLOR, height=30, relief='raised')
        self.title_bar.pack(side="top", fill="x")
        
        tk.Label(self.title_bar, text="FactDari", fg=self.TEXT_COLOR, bg=self.TITLE_BG_COLOR, 
                font=(self.NORMAL_FONT[0], 12, 'bold')).pack(side="left", padx=5, pady=5)
        
        # Category selection - create but don't pack yet
        self.category_frame = tk.Frame(self.title_bar, bg='#000000')
        tk.Label(self.category_frame, text="Category:", fg="white", bg='#000000', 
                font=(self.SMALL_FONT[0], self.SMALL_FONT[1])).pack(side="left", padx=5)
        
        self.category_var = tk.StringVar(self.root, value="All Categories")
        
        # Apply custom styling to the combobox
        style = ttk.Style()
        style.theme_use('default')
        style.configure('Custom.TCombobox', 
                        background=self.BG_COLOR,
                        fieldbackground='#333333',
                        foreground=self.TEXT_COLOR,
                        arrowcolor=self.TEXT_COLOR,
                        bordercolor=self.GREEN_COLOR,
                        lightcolor=self.GREEN_COLOR,
                        darkcolor=self.GREEN_COLOR)
        
        # Create the combobox with custom styling
        self.category_dropdown = ttk.Combobox(self.category_frame, 
                                             textvariable=self.category_var, 
                                             state="readonly", 
                                             width=15,
                                             style='Custom.TCombobox')
        
        self.category_dropdown['values'] = self.load_categories()
        self.category_dropdown.pack(side="left")
        
        # Use option_add to style dropdown items
        self.root.option_add('*TCombobox*Listbox*Background', '#333333')
        self.root.option_add('*TCombobox*Listbox*Foreground', self.TEXT_COLOR)
        self.root.option_add('*TCombobox*Listbox*selectBackground', self.GREEN_COLOR)
        
        # Main content area
        self.content_frame = tk.Frame(self.root, bg=self.BG_COLOR)
        self.content_frame.pack(side="top", fill="both", expand=True, padx=10, pady=5)
        
        # Fact display
        self.fact_frame = tk.Frame(self.content_frame, bg=self.BG_COLOR)
        self.fact_frame.pack(side="top", fill="both", expand=True, pady=5)
        
        # Add top padding to push content down
        self.padding_frame = tk.Frame(self.fact_frame, bg=self.BG_COLOR, height=30)
        self.padding_frame.pack(side="top", fill="x")
        
        self.fact_label = tk.Label(self.fact_frame, text="Welcome to FactDari!", fg=self.TEXT_COLOR, bg=self.BG_COLOR, 
                                  font=self.LARGE_FONT, wraplength=450, justify="center")
        self.fact_label.pack(side="top", fill="both", expand=True, padx=10, pady=10)
        
        # Create slogan label
        self.slogan_label = tk.Label(self.content_frame, text="Review and remember facts effortlessly", 
                              fg=self.GREEN_COLOR, bg=self.BG_COLOR, font=(self.NORMAL_FONT[0], 12, 'italic'))
        
        # Create start reviewing button
        self.start_button = tk.Button(self.content_frame, text="Start Reviewing", command=self.start_reviewing, 
                              bg=self.GREEN_COLOR, fg=self.TEXT_COLOR, cursor="hand2", borderwidth=0, 
                              highlightthickness=0, padx=20, pady=10,
                              font=self.LARGE_FONT)
        
        # Navigation buttons frame
        self.nav_frame = tk.Frame(self.content_frame, bg=self.BG_COLOR)
        
        nav_buttons = tk.Frame(self.nav_frame, bg=self.BG_COLOR)
        nav_buttons.pack(side="top")
        
        # Previous button
        self.prev_button = tk.Button(nav_buttons, text="Previous", command=self.show_previous_fact, 
                           bg=self.BLUE_COLOR, fg=self.TEXT_COLOR,
                           cursor="hand2", borderwidth=0, highlightthickness=0, padx=10, pady=5, width=10)
        self.prev_button.pack(side="left", padx=5)
        
        # Next button
        self.next_button = tk.Button(nav_buttons, text="Next", command=self.show_next_fact,
                                bg=self.BLUE_COLOR, fg=self.TEXT_COLOR, cursor="hand2", borderwidth=0, 
                                highlightthickness=0, padx=10, pady=5, width=10)
        self.next_button.pack(side="left", padx=5)
        
        # Load icons
        self.load_icons()
        
        # Icon buttons frame
        self.icon_buttons_frame = tk.Frame(self.content_frame, bg=self.BG_COLOR)
        
        # Add button
        self.add_icon_button = tk.Button(self.icon_buttons_frame, image=self.add_icon, bg=self.BG_COLOR, command=self.add_new_fact,
                                 cursor="hand2", borderwidth=0, highlightthickness=0)
        self.add_icon_button.pack(side="left", padx=10)
        
        # Create edit button
        self.edit_icon_button = tk.Button(self.icon_buttons_frame, image=self.edit_icon, bg=self.BG_COLOR, command=self.edit_current_fact,
                                  cursor="hand2", borderwidth=0, highlightthickness=0)
        self.edit_icon_button.pack(side="left", padx=10)
        
        # Create delete button
        self.delete_icon_button = tk.Button(self.icon_buttons_frame, image=self.delete_icon, bg=self.BG_COLOR, command=self.delete_current_fact,
                                    cursor="hand2", borderwidth=0, highlightthickness=0)
        self.delete_icon_button.pack(side="left", padx=10)
        
        # Create a spacer frame to help with centering
        self.center_spacer = tk.Frame(self.icon_buttons_frame, bg=self.BG_COLOR, width=60)
        self.center_spacer.pack(side="left")
        
        # Single card warning label - positioned more to the left
        self.single_card_label = tk.Label(self.icon_buttons_frame, text="*Only 1 Card in Category*", 
                                         fg=self.RED_COLOR, bg=self.BG_COLOR, 
                                         font=(self.NORMAL_FONT[0], 9, 'italic'))
        # Don't pack it initially, will be shown/hidden as needed
        
        # Status label - always visible
        self.status_label = self.create_label(self.icon_buttons_frame, "", fg=self.STATUS_COLOR, 
                                        font=self.NORMAL_FONT, side='right')
        self.status_label.pack_configure(pady=5, padx=10)
        
        # Add home and speaker buttons
        self.home_button = tk.Button(self.fact_frame, image=self.home_icon, bg=self.BG_COLOR, bd=0, highlightthickness=0, 
                               cursor="hand2", activebackground=self.BG_COLOR, command=self.show_home_page)
        self.home_button.place(relx=0, rely=0, anchor="nw", x=5, y=5)
        
        self.speaker_button = tk.Button(self.fact_frame, image=self.speaker_icon, bg=self.BG_COLOR, command=self.speak_text, 
                                  cursor="hand2", borderwidth=0, highlightthickness=0)
        self.speaker_button.place(relx=1.0, rely=0, anchor="ne", x=-5, y=5)
        
        # Add graph button (middle between speak and star)
        self.graph_button = tk.Button(self.fact_frame, image=self.graph_icon, bg=self.BG_COLOR, command=self.show_analytics, 
                                cursor="hand2", borderwidth=0, highlightthickness=0)
        self.graph_button.place(relx=1.0, rely=0, anchor="ne", x=-30, y=5)

        # Add easy/known button (left of the star)
        self.easy_button = tk.Button(self.fact_frame, image=self.easy_icon, bg=self.BG_COLOR, command=self.toggle_easy,
                                cursor="hand2", borderwidth=0, highlightthickness=0)
        # Temporarily assign icon after loading icons
        # Will be placed/hidden depending on current screen
        self.easy_button.place(relx=1.0, rely=0, anchor="ne", x=-80, y=5)

        # Add star/favorite button (leftmost of the top-right icons)
        self.star_button = tk.Button(self.fact_frame, image=self.white_star_icon, bg=self.BG_COLOR, command=self.toggle_favorite, 
                                cursor="hand2", borderwidth=0, highlightthickness=0)
        self.star_button.place(relx=1.0, rely=0, anchor="ne", x=-55, y=5)

        # Info button (shown on home page instead of star)
        self.info_button = tk.Button(self.fact_frame, image=self.info_icon, bg=self.BG_COLOR, command=self.show_shortcuts_window,
                                cursor="hand2", borderwidth=0, highlightthickness=0)
        # Initially not placed; placed when showing home page
        
        # Bottom stats frame
        self.stats_frame = tk.Frame(self.root, bg=self.BG_COLOR)
        
        # Stats labels
        self.fact_count_label = self.create_label(self.stats_frame, "Total Facts: 0", 
                                            font=self.STATS_FONT, side='left', fg=self.BLUE_COLOR)
        self.fact_count_label.pack_configure(padx=10)
        
        self.review_stats_label = self.create_label(self.stats_frame, "Seen Today: 0", 
                                       font=self.STATS_FONT, side='left', fg=self.BLUE_COLOR)
        self.review_stats_label.pack_configure(padx=10)
        
        self.coordinate_label = self.create_label(self.stats_frame, "Coordinates: ", 
                                        font=self.STATS_FONT, side='left', fg=self.BLUE_COLOR)
        self.coordinate_label.pack_configure(padx=10)
        
        # Add GitHub link on the right side
        github_label = tk.Label(self.stats_frame, text="GitHub: LordGauravB", 
                              fg=self.BLUE_COLOR, bg=self.BG_COLOR, font=self.STATS_FONT,
                              cursor="hand2")
        github_label.pack(side='right', padx=10)
        github_label.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/LordGauravB"))
        
        # Create helpful tooltips
        self._attach_tooltips()

    def load_icons(self):
        """Load all icons used in the application using the config module"""
        self.home_icon = ImageTk.PhotoImage(Image.open(config.get_icon_path("Home.png")).resize((20, 20), Image.Resampling.LANCZOS))
        self.speaker_icon = ImageTk.PhotoImage(Image.open(config.get_icon_path("speaker_icon.png")).resize((20, 20), Image.Resampling.LANCZOS))
        self.add_icon = ImageTk.PhotoImage(Image.open(config.get_icon_path("add.png")).resize((20, 20), Image.Resampling.LANCZOS))
        self.edit_icon = ImageTk.PhotoImage(Image.open(config.get_icon_path("edit.png")).resize((20, 20), Image.Resampling.LANCZOS))
        self.delete_icon = ImageTk.PhotoImage(Image.open(config.get_icon_path("delete.png")).resize((20, 20), Image.Resampling.LANCZOS))
        self.graph_icon = ImageTk.PhotoImage(Image.open(config.get_icon_path("graph.png")).resize((20, 20), Image.Resampling.LANCZOS))
        self.white_star_icon = ImageTk.PhotoImage(Image.open(config.get_icon_path("White-Star.png")).resize((20, 20), Image.Resampling.LANCZOS))
        self.gold_star_icon = ImageTk.PhotoImage(Image.open(config.get_icon_path("Gold-Star.png")).resize((20, 20), Image.Resampling.LANCZOS))
        self.info_icon = ImageTk.PhotoImage(Image.open(config.get_icon_path("info.png")).resize((20, 20), Image.Resampling.LANCZOS))
        # Easy/known icons
        self.easy_icon = ImageTk.PhotoImage(Image.open(config.get_icon_path("easy.png")).resize((20, 20), Image.Resampling.LANCZOS))
        self.easy_gold_icon = ImageTk.PhotoImage(Image.open(config.get_icon_path("easy-gold.png")).resize((20, 20), Image.Resampling.LANCZOS))
        # Apply default to button if it exists
        if hasattr(self, 'easy_button') and self.easy_button:
            self.easy_button.config(image=self.easy_icon)
    
    def bind_events(self):
        """Bind all event handlers"""
        self.title_bar.bind("<Button-1>", self.on_press)
        self.title_bar.bind("<B1-Motion>", self.on_drag)
        self.root.bind("<FocusIn>", lambda event: self.root.attributes('-alpha', 1.0))
        self.root.bind("<FocusOut>", lambda event: self.root.attributes('-alpha', 0.7))
        self.root.bind("<s>", self.set_static_position)
        self.category_dropdown.bind("<<ComboboxSelected>>", self.on_category_change)
        # Global input to detect activity
        self.root.bind_all('<Any-KeyPress>', lambda e: self.record_activity())
        self.root.bind_all('<Button>', lambda e: self.record_activity())
        
        # Keyboard shortcuts for navigation and actions
        self.root.bind("<Left>", lambda e: self.show_previous_fact())
        self.root.bind("<Right>", lambda e: self.show_next_fact())
        self.root.bind("<space>", lambda e: self.show_next_fact())
        self.root.bind("n", lambda e: self.show_next_fact())
        self.root.bind("p", lambda e: self.show_previous_fact())
        self.root.bind("a", lambda e: self.add_new_fact())
        self.root.bind("e", lambda e: self.edit_current_fact())
        self.root.bind("d", lambda e: self.delete_current_fact())
        self.root.bind("h", lambda e: self.show_home_page())
        self.root.bind("g", lambda e: self.show_analytics())
        self.root.bind("c", lambda e: self.manage_categories())
        self.root.bind("f", lambda e: self.toggle_favorite())  # Shortcut for favorite
        self.root.bind("k", lambda e: self.toggle_easy())  # Shortcut for known/easy
    
    def apply_rounded_corners(self, radius=None):
        """Apply rounded corners to the window"""
        if radius is None:
            radius = self.CORNER_RADIUS
            
        try:
            hwnd = self.root.winfo_id()
            hRgn = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, self.root.winfo_width(), self.root.winfo_height(), radius, radius)
            ctypes.windll.user32.SetWindowRgn(wintypes.HWND(hwnd), hRgn, True)
        except Exception:
            pass

    def _attach_tooltips(self):
        """Attach tooltips to interactive widgets for discoverability."""
        try:
            ToolTip(self.home_button, "Home (h)")
            ToolTip(self.speaker_button, "Speak text")
            ToolTip(self.star_button, "Toggle favorite (f)")
            ToolTip(self.easy_button, "Mark as known (k)")
            ToolTip(self.graph_button, "Analytics (g)")
            ToolTip(self.info_button, "Show shortcuts")
            ToolTip(self.add_icon_button, "Add fact (a)")
            ToolTip(self.edit_icon_button, "Edit fact (e)")
            ToolTip(self.delete_icon_button, "Delete fact (d)")
            ToolTip(self.prev_button, "Previous (←)")
            ToolTip(self.next_button, "Next (→)")
        except Exception:
            pass

    def show_shortcuts_window(self):
        """Show a window listing available keyboard shortcuts."""
        win = tk.Toplevel(self.root)
        win.title("Keyboard Shortcuts")
        # Size and position per UI config
        try:
            win.geometry(f"{self.POPUP_INFO_SIZE}{self.POPUP_POSITION}")
        except Exception:
            win.geometry(self.POPUP_INFO_SIZE)
        win.configure(bg=self.BG_COLOR)

        header = tk.Label(win, text="Keyboard Shortcuts", fg=self.TEXT_COLOR, bg=self.BG_COLOR, font=self.TITLE_FONT)
        header.pack(pady=10)

        content = tk.Frame(win, bg=self.BG_COLOR)
        content.pack(fill="both", expand=True, padx=20, pady=10)

        def row(label_text, keys_text):
            r = tk.Frame(content, bg=self.BG_COLOR)
            r.pack(fill="x", pady=2)
            tk.Label(r, text=label_text+":", fg=self.GREEN_COLOR, bg=self.BG_COLOR, font=(self.NORMAL_FONT[0], self.NORMAL_FONT[1], 'bold'), width=16, anchor='w').pack(side='left')
            tk.Label(r, text=keys_text, fg=self.TEXT_COLOR, bg=self.BG_COLOR, font=self.NORMAL_FONT, anchor='w', justify='left').pack(side='left', fill='x', expand=True)

        # List of shortcuts
        row("Home", "h")
        row("Previous", "Left Arrow, p")
        row("Next", "Right Arrow, n, Space")
        row("Add Fact", "a")
        row("Edit Fact", "e")
        row("Delete Fact", "d")
        row("Analytics", "g")
        row("Categories", "c")
        row("Toggle Favorite", "f")
        row("Static Position", "s")

        tk.Button(win, text="Close", command=win.destroy, bg=self.BLUE_COLOR, fg=self.TEXT_COLOR, cursor="hand2", borderwidth=0, highlightthickness=0, padx=10, pady=5).pack(pady=10)

    def confirm_dialog(self, title, message, ok_text="OK", cancel_text="Cancel"):
        """Custom modal confirmation dialog positioned via UI config. Returns True/False."""
        dlg = tk.Toplevel(self.root)
        dlg.title(title)
        dlg.configure(bg=self.BG_COLOR)
        dlg.transient(self.root)
        dlg.grab_set()
        try:
            dlg.geometry(f"{self.POPUP_CONFIRM_SIZE}{self.POPUP_POSITION}")
        except Exception:
            dlg.geometry(self.POPUP_CONFIRM_SIZE)

        # Content
        tk.Label(dlg, text=title, fg=self.TEXT_COLOR, bg=self.BG_COLOR, font=self.TITLE_FONT).pack(pady=(10, 0))
        msg = tk.Label(dlg, text=message, fg=self.TEXT_COLOR, bg=self.BG_COLOR, font=self.NORMAL_FONT, wraplength=360, justify='center')
        msg.pack(padx=20, pady=10, fill='x')

        result = {'value': False}

        def on_ok():
            result['value'] = True
            dlg.destroy()

        def on_cancel():
            result['value'] = False
            dlg.destroy()

        btn_frame = tk.Frame(dlg, bg=self.BG_COLOR)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text=ok_text, command=on_ok, bg=self.RED_COLOR if ok_text.lower()=="delete" else self.BLUE_COLOR, fg=self.TEXT_COLOR, borderwidth=0, highlightthickness=0, padx=12, pady=5).pack(side='left', padx=6)
        tk.Button(btn_frame, text=cancel_text, command=on_cancel, bg=self.GRAY_COLOR, fg=self.TEXT_COLOR, borderwidth=0, highlightthickness=0, padx=12, pady=5).pack(side='left', padx=6)

        dlg.bind('<Return>', lambda e: on_ok())
        dlg.bind('<Escape>', lambda e: on_cancel())

        self.root.wait_window(dlg)
        return result['value']

    def prompt_dialog(self, title, prompt, initialvalue=""):
        """Custom modal prompt dialog with entry. Returns str or None."""
        dlg = tk.Toplevel(self.root)
        dlg.title(title)
        dlg.configure(bg=self.BG_COLOR)
        dlg.transient(self.root)
        dlg.grab_set()
        try:
            dlg.geometry(f"{self.POPUP_RENAME_SIZE}{self.POPUP_POSITION}")
        except Exception:
            dlg.geometry(self.POPUP_RENAME_SIZE)

        tk.Label(dlg, text=title, fg=self.TEXT_COLOR, bg=self.BG_COLOR, font=self.TITLE_FONT).pack(pady=(10, 0))
        tk.Label(dlg, text=prompt, fg=self.TEXT_COLOR, bg=self.BG_COLOR, font=self.NORMAL_FONT, wraplength=380, justify='left').pack(padx=20, pady=(8, 4), anchor='w')

        entry = tk.Entry(dlg, font=self.NORMAL_FONT)
        entry.pack(padx=20, pady=6, fill='x')
        entry.insert(0, initialvalue or "")
        entry.selection_range(0, tk.END)
        entry.focus_set()

        result = {'value': None}

        def on_ok():
            result['value'] = entry.get().strip()
            dlg.destroy()

        def on_cancel():
            result['value'] = None
            dlg.destroy()

        btn_frame = tk.Frame(dlg, bg=self.BG_COLOR)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="OK", command=on_ok, bg=self.BLUE_COLOR, fg=self.TEXT_COLOR, borderwidth=0, highlightthickness=0, padx=12, pady=5).pack(side='left', padx=6)
        tk.Button(btn_frame, text="Cancel", command=on_cancel, bg=self.GRAY_COLOR, fg=self.TEXT_COLOR, borderwidth=0, highlightthickness=0, padx=12, pady=5).pack(side='left', padx=6)

        dlg.bind('<Return>', lambda e: on_ok())
        dlg.bind('<Escape>', lambda e: on_cancel())

        self.root.wait_window(dlg)
        return result['value']
    
    # Database Methods
    def fetch_query(self, query, params=None):
        """Execute a SELECT query and return the results"""
        try:
            with pyodbc.connect(self.CONN_STR) as conn:
                with conn.cursor() as cursor:
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                    return cursor.fetchall()
        except Exception as e:
            print(f"Database error in fetch_query: {e}")
            return []

    def table_exists(self, table_name):
        """Check if a table exists in the database (SQL Server)."""
        try:
            rows = self.fetch_query(
                """
                SELECT 1
                FROM sys.tables
                WHERE Name = ? AND schema_id = SCHEMA_ID('dbo')
                """,
                (table_name,)
            )
            return bool(rows)
        except Exception:
            return False

    def column_exists(self, table_name, column_name):
        """Check if a column exists in the given table (SQL Server)."""
        try:
            rows = self.fetch_query(
                """
                SELECT 1
                FROM sys.columns
                WHERE Name = ? AND Object_ID = OBJECT_ID(?)
                """,
                (column_name, f"dbo.{table_name}")
            )
            return bool(rows)
        except Exception:
            return False
    
    def execute_update(self, query, params=None):
        """Execute an UPDATE/INSERT/DELETE query with no return value"""
        try:
            with pyodbc.connect(self.CONN_STR) as conn:
                with conn.cursor() as cursor:
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                    conn.commit()
            return True
        except Exception as e:
            print(f"Database error in execute_update: {e}")
            return False

    def execute_insert_return_id(self, query, params=None):
        """Execute an INSERT with OUTPUT ... RETURNING pattern and return the new ID."""
        try:
            with pyodbc.connect(self.CONN_STR) as conn:
                with conn.cursor() as cursor:
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                    row = cursor.fetchone()
                    conn.commit()
                    return row[0] if row else None
        except Exception as e:
            print(f"Database error in execute_insert_return_id: {e}")
            return None

    def ensure_schema(self):
        """Create missing tables/columns for sessions and per-view durations."""
        ddl = """
        /* Create ReviewSessions if missing */
        IF OBJECT_ID('dbo.ReviewSessions','U') IS NULL
        BEGIN
            CREATE TABLE dbo.ReviewSessions (
                SessionID INT IDENTITY(1,1) PRIMARY KEY,
                StartTime DATETIME NOT NULL,
                EndTime DATETIME NULL,
                DurationSeconds INT NULL,
                TimedOut BIT NOT NULL CONSTRAINT DF_ReviewSessions_TimedOut DEFAULT 0
            );
        END;

        /* Ensure ReviewLogs table exists */
        IF OBJECT_ID('dbo.ReviewLogs','U') IS NULL
        BEGIN
            -- Create minimal ReviewLogs table if missing (defensive)
            CREATE TABLE dbo.ReviewLogs (
                ReviewLogID INT IDENTITY(1,1) PRIMARY KEY,
                FactID INT NOT NULL,
                ReviewDate DATETIME NOT NULL
            );
        END;
        
        /* Ensure SessionDuration column exists for per-view timing */
        IF COL_LENGTH('dbo.ReviewLogs','SessionDuration') IS NULL
        BEGIN
            ALTER TABLE dbo.ReviewLogs ADD SessionDuration INT NULL;
        END;
        /* Ensure per-view TimedOut flag exists */
        IF COL_LENGTH('dbo.ReviewLogs','TimedOut') IS NULL
        BEGIN
            ALTER TABLE dbo.ReviewLogs ADD TimedOut BIT NOT NULL CONSTRAINT DF_ReviewLogs_TimedOut DEFAULT 0;
        END;
        /* Ensure session-level TimedOut flag exists */
        IF COL_LENGTH('dbo.ReviewSessions','TimedOut') IS NULL
        BEGIN
            ALTER TABLE dbo.ReviewSessions ADD TimedOut BIT NOT NULL CONSTRAINT DF_ReviewSessions_TimedOut DEFAULT 0;
        END;
        IF COL_LENGTH('dbo.ReviewLogs','SessionID') IS NULL
        BEGIN
            ALTER TABLE dbo.ReviewLogs ADD SessionID INT NULL;
        END;
        IF OBJECT_ID('dbo.FK_ReviewLogs_ReviewSessions','F') IS NULL
        BEGIN
            ALTER TABLE dbo.ReviewLogs
            ADD CONSTRAINT FK_ReviewLogs_ReviewSessions
            FOREIGN KEY (SessionID) REFERENCES dbo.ReviewSessions(SessionID);
        END;
        IF NOT EXISTS (
            SELECT 1 FROM sys.indexes 
            WHERE name = 'IX_ReviewLogs_SessionID' AND object_id = OBJECT_ID('dbo.ReviewLogs')
        )
        BEGIN
            CREATE INDEX IX_ReviewLogs_SessionID ON dbo.ReviewLogs(SessionID);
        END;
        """
        self.execute_update(ddl)
    
    def count_facts(self):
        """Count total facts in the database"""
        result = self.fetch_query("SELECT COUNT(*) FROM Facts")
        return result[0][0] if result and len(result) > 0 else 0
    
    def get_facts_viewed_today(self):
        """Get count of unique facts viewed today"""
        today = datetime.now().strftime('%Y-%m-%d')
        query = """
        SELECT COUNT(DISTINCT FactID) 
        FROM ReviewLogs 
        WHERE CONVERT(date, ReviewDate) = CONVERT(date, ?)
        """
        result = self.fetch_query(query, (today,))
        return result[0][0] if result and len(result) > 0 else 0
    
    def update_ui(self):
        """Update UI elements periodically"""
        self.update_coordinates()
        if not self.is_home_page:
            self.update_fact_count()
            self.update_review_stats()
            # Check inactivity only while in reviewing mode
            try:
                if self.current_session_id:
                    idle_seconds = int((datetime.now() - self.last_activity_time).total_seconds())
                    if not self.idle_triggered and idle_seconds >= int(self.idle_timeout_seconds):
                        self.handle_idle_timeout()
            except Exception:
                pass
        self.root.after(100, self.update_ui)
    
    def update_fact_count(self):
        """Update the fact count display"""
        num_facts = self.count_facts()
        self.fact_count_label.config(text=f"Total Facts: {num_facts}")
    
    def update_review_stats(self):
        """Update the viewing statistics"""
        facts_viewed = self.get_facts_viewed_today()
        self.review_stats_label.config(text=f"Seen Today: {facts_viewed}")
    
    def on_press(self, event):
        """Handle mouse press on title bar for dragging"""
        self.x_window, self.y_window = event.x, event.y
    
    def update_coordinates(self):
        """Update the coordinate display"""
        x, y = self.root.winfo_x(), self.root.winfo_y()
        self.coordinate_label.config(text=f"Coordinates: {x}, {y}")
    
    def on_drag(self, event):
        """Handle window dragging"""
        x, y = event.x_root - self.x_window, event.y_root - self.y_window
        self.root.geometry(f"+{x}+{y}")
        self.coordinate_label.config(text=f"Coordinates: {x}, {y}")
    
    def set_static_position(self, event=None):
        """Set window to a static position"""
        self.root.geometry(self.WINDOW_STATIC_POS)
        self.update_coordinates()
    
    def speak_text(self):
        """Speak the current fact text (non-blocking)."""
        if self.is_home_page:
            return
        text = self.fact_label.cget("text")
        
        # Stop any ongoing speech first
        self.stop_speaking()
        
        # Disable button while speaking
        try:
            self.speaker_button.config(state="disabled")
        except Exception:
            pass
        
        def _worker():
            try:
                self.speech_engine.stop()
                self.speech_engine.say(text)
                self.speech_engine.runAndWait()
            except Exception:
                pass
            finally:
                # Re-enable on UI thread
                self.root.after(0, lambda: self.speaker_button.config(state="normal"))
        
        self.speaking_thread = threading.Thread(target=_worker, daemon=True)
        self.speaking_thread.start()

    def stop_speaking(self):
        """Stop any ongoing speech immediately."""
        try:
            if self.speaking_thread and self.speaking_thread.is_alive():
                try:
                    self.speech_engine.stop()
                except Exception:
                    pass
                # Allow thread to wind down
                try:
                    self.speaking_thread.join(timeout=0.2)
                except Exception:
                    pass
        except Exception:
            pass
    
    def show_analytics(self):
        """Launch the analytics web application"""
        # Check if Flask server is already running
        if hasattr(self, 'flask_process') and self.flask_process.poll() is None:
            # Server is running, just open the browser
            webbrowser.open("http://localhost:5000")
        else:
            # Start the Flask server
            self.start_flask_server()
            # Wait a moment for the server to start
            self.root.after(1000, lambda: webbrowser.open("http://localhost:5000"))

    def start_flask_server(self):
        """Start the Flask server in a separate process"""
        # Path to the Flask app.py file
        flask_app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "analytics_factdari.py")
        
        # Start Flask server
        if sys.platform.startswith('win'):
            python_executable = sys.executable
            self.flask_process = subprocess.Popen([python_executable, flask_app_path], 
                                               creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        else:
            python_executable = sys.executable
            self.flask_process = subprocess.Popen([python_executable, flask_app_path], 
                                               preexec_fn=os.setsid)
        
        # Register exit handler to close Flask server when the main app exits
        atexit.register(self.close_flask_server)

    def close_flask_server(self):
        """Close the Flask server when the main application exits"""
        if hasattr(self, 'flask_process') and self.flask_process.poll() is None:
            if sys.platform.startswith('win'):
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(self.flask_process.pid)])
            else:
                os.killpg(os.getpgid(self.flask_process.pid), signal.SIGTERM)
    
    def load_all_facts(self):
        """Load all facts for the current category"""
        category = self.category_var.get()
        
        has_is_easy = self.column_exists('Facts', 'IsEasy')
        if category == "All Categories":
            if has_is_easy:
                query = """
                    SELECT FactID, Content, IsFavorite, IsEasy
                    FROM Facts
                    ORDER BY NEWID()
                """
            else:
                query = """
                    SELECT FactID, Content, IsFavorite
                    FROM Facts
                    ORDER BY NEWID()
                """
            facts = self.fetch_query(query)
        elif category == "Favorites":
            if has_is_easy:
                query = """
                    SELECT FactID, Content, IsFavorite, IsEasy
                    FROM Facts
                    WHERE IsFavorite = 1
                    ORDER BY NEWID()
                """
            else:
                query = """
                    SELECT FactID, Content, IsFavorite
                    FROM Facts
                    WHERE IsFavorite = 1
                    ORDER BY NEWID()
                """
            facts = self.fetch_query(query)
        elif category == "Known":
            if has_is_easy:
                query = """
                    SELECT FactID, Content, IsFavorite, IsEasy
                    FROM Facts
                    WHERE IsEasy = 1
                    ORDER BY NEWID()
                """
                facts = self.fetch_query(query)
            else:
                facts = []
        elif category == "Not Known":
            if has_is_easy:
                query = """
                    SELECT FactID, Content, IsFavorite, IsEasy
                    FROM Facts
                    WHERE IsEasy = 0
                    ORDER BY NEWID()
                """
                facts = self.fetch_query(query)
            else:
                facts = []
        elif category == "Not Favorite":
            if has_is_easy:
                query = """
                    SELECT FactID, Content, IsFavorite, IsEasy
                    FROM Facts
                    WHERE IsFavorite = 0
                    ORDER BY NEWID()
                """
            else:
                query = """
                    SELECT FactID, Content, IsFavorite
                    FROM Facts
                    WHERE IsFavorite = 0
                    ORDER BY NEWID()
                """
            facts = self.fetch_query(query)
        else:
            if has_is_easy:
                query = """
                    SELECT f.FactID, f.Content, f.IsFavorite, f.IsEasy
                    FROM Facts f
                    JOIN Categories c ON f.CategoryID = c.CategoryID
                    WHERE c.CategoryName = ?
                    ORDER BY NEWID()
                """
            else:
                query = """
                    SELECT f.FactID, f.Content, f.IsFavorite
                    FROM Facts f
                    JOIN Categories c ON f.CategoryID = c.CategoryID
                    WHERE c.CategoryName = ?
                    ORDER BY NEWID()
                """
            facts = self.fetch_query(query, (category,))
        
        self.all_facts = facts if facts else []
        self.current_fact_index = 0
    
    def show_next_fact(self):
        """Show the next fact in the list"""
        if self.is_home_page:
            return
        # Stop any ongoing speech when changing facts
        self.stop_speaking()
        if not self.all_facts:
            self.load_all_facts()
        
        # Only navigate if there's more than one fact
        if self.all_facts and len(self.all_facts) > 1:
            if self.current_fact_index >= len(self.all_facts) - 1:
                # Completed a pass; reshuffle for a fresh random order
                last_id = self.all_facts[self.current_fact_index][0]
                random.shuffle(self.all_facts)
                # Avoid showing the same fact twice in a row after shuffle
                if self.all_facts and self.all_facts[0][0] == last_id and len(self.all_facts) > 1:
                    self.all_facts.append(self.all_facts.pop(0))
                self.current_fact_index = 0
            else:
                self.current_fact_index += 1
            self.display_current_fact()
    
    def show_previous_fact(self):
        """Show the previous fact in the list"""
        if self.is_home_page:
            return
        # Stop any ongoing speech when changing facts
        self.stop_speaking()
        if not self.all_facts:
            self.load_all_facts()
        
        # Only navigate if there's more than one fact
        if self.all_facts and len(self.all_facts) > 1:
            self.current_fact_index = (self.current_fact_index - 1) % len(self.all_facts)
            self.display_current_fact()
    
    def display_current_fact(self):
        """Display the current fact and update tracking"""
        # Ensure we stop speaking when the fact changes
        self.stop_speaking()
        if not self.all_facts:
            self.fact_label.config(text="No facts found. Add some facts first!", 
                                  font=(self.NORMAL_FONT[0], 12))
            self.current_fact_id = None
            self.star_button.config(image=self.white_star_icon)
            if hasattr(self, 'easy_button'):
                self.easy_button.config(image=self.easy_icon)
            # Disable navigation buttons when no facts
            self.prev_button.config(state="disabled", bg=self.GRAY_COLOR)
            self.next_button.config(state="disabled", bg=self.GRAY_COLOR)
            return
        
        # Enable/disable navigation buttons based on fact count
        if len(self.all_facts) <= 1:
            # Only one fact, disable navigation and show warning
            self.prev_button.config(state="disabled", bg=self.GRAY_COLOR)
            self.next_button.config(state="disabled", bg=self.GRAY_COLOR)
            # Pack the warning label after the spacer (more to the left)
            self.single_card_label.pack(side="left", padx=0)
        else:
            # Multiple facts, enable navigation and hide warning
            self.prev_button.config(state="normal", bg=self.BLUE_COLOR)
            self.next_button.config(state="normal", bg=self.BLUE_COLOR)
            self.single_card_label.pack_forget()
        
        fact = self.all_facts[self.current_fact_index]
        self.current_fact_id = fact[0]
        content = fact[1]
        self.current_fact_is_favorite = fact[2] if len(fact) > 2 else False
        self.current_fact_is_easy = fact[3] if len(fact) > 3 else False
        
        # Update star icon based on favorite status
        if self.current_fact_is_favorite:
            self.star_button.config(image=self.gold_star_icon)
        else:
            self.star_button.config(image=self.white_star_icon)
        # Update easy icon
        if self.current_fact_is_easy:
            self.easy_button.config(image=self.easy_gold_icon)
        else:
            self.easy_button.config(image=self.easy_icon)
        
        # Display the fact
        self.fact_label.config(text=content, font=(self.NORMAL_FONT[0], self.adjust_font_size(content)))
        
        # Update tracking in database only if we have more than one fact
        # (to avoid inflating view counts when there's only one fact)
        if len(self.all_facts) > 1 or not hasattr(self, '_last_tracked_fact') or self._last_tracked_fact != self.current_fact_id:
            self.track_fact_view(self.current_fact_id)
            self._last_tracked_fact = self.current_fact_id
        
        # Update status with fact position
        self.status_label.config(text=f"Fact {self.current_fact_index + 1} of {len(self.all_facts)}", 
                               fg=self.STATUS_COLOR)
    
    def track_fact_view(self, fact_id):
        """Track that a fact has been viewed"""
        now = datetime.now()
        self.record_activity()

        # 1) Finalize previous view's duration if any
        try:
            if self.current_review_log_id and self.current_fact_start_time:
                elapsed = int((now - self.current_fact_start_time).total_seconds())
                if elapsed < 0:
                    elapsed = 0
                self.execute_update(
                    """
                    UPDATE ReviewLogs
                    SET SessionDuration = ?
                    WHERE ReviewLogID = ?
                    """,
                    (elapsed, self.current_review_log_id)
                )
        except Exception as _:
            pass

        # 2) Update the fact's view count and last viewed date
        self.execute_update("""
            UPDATE Facts 
            SET TotalViews = TotalViews + 1,
                ReviewCount = ReviewCount + 1,
                LastViewedDate = GETDATE()
            WHERE FactID = ?
        """, (fact_id,))

        # 3) Start a new view log and remember its ID + start time
        try:
            # Ensure we have a session
            if not self.current_session_id:
                self.start_new_session()

            new_id = self.execute_insert_return_id(
                """
                INSERT INTO ReviewLogs (FactID, ReviewDate, SessionID)
                OUTPUT INSERTED.ReviewLogID
                VALUES (?, GETDATE(), ?)
                """,
                (fact_id, self.current_session_id)
            )
            self.current_review_log_id = new_id
            self.current_fact_start_time = now
        except Exception as _:
            # If we couldn't insert with SessionID for some reason, fall back to basic insert
            self.execute_update(
                """
                INSERT INTO ReviewLogs (FactID, ReviewDate)
                VALUES (?, GETDATE())
                """,
                (fact_id,)
            )
            self.current_review_log_id = None
            self.current_fact_start_time = now

    def finalize_current_fact_view(self, timed_out=False):
        """Finalize timing for the current fact view, if active.
        If timed_out=True, also mark the log as ended due to inactivity.
        """
        try:
            if self.current_review_log_id and self.current_fact_start_time:
                elapsed = int((datetime.now() - self.current_fact_start_time).total_seconds())
                if elapsed < 0:
                    elapsed = 0
                # Try to update with TimedOut flag if column exists
                updated = self.execute_update(
                    """
                    UPDATE ReviewLogs
                    SET SessionDuration = ?, TimedOut = ?
                    WHERE ReviewLogID = ?
                    """,
                    (elapsed, 1 if timed_out else 0, self.current_review_log_id)
                )
                if not updated:
                    # Fallback without TimedOut if migration hasn't applied
                    self.execute_update(
                        """
                        UPDATE ReviewLogs
                        SET SessionDuration = ?
                        WHERE ReviewLogID = ?
                        """,
                        (elapsed, self.current_review_log_id)
                    )
        except Exception:
            pass
        finally:
            self.current_review_log_id = None
            self.current_fact_start_time = None

    def start_new_session(self):
        """Start a new reviewing session and store SessionID."""
        # End any existing session first
        self.end_active_session()
        self.session_start_time = datetime.now()
        session_id = self.execute_insert_return_id(
            """
            INSERT INTO ReviewSessions (StartTime)
            OUTPUT INSERTED.SessionID
            VALUES (GETDATE())
            """
        )
        self.current_session_id = session_id

    def end_active_session(self, timed_out=False):
        """End the active reviewing session, if any. If timed_out=True, marks session TimedOut."""
        try:
            # Finalize any ongoing fact view first
            self.finalize_current_fact_view(timed_out=False)

            if self.current_session_id:
                updated = self.execute_update(
                    """
                    UPDATE ReviewSessions
                    SET EndTime = GETDATE(),
                        DurationSeconds = DATEDIFF(second, StartTime, GETDATE()),
                        TimedOut = ?
                    WHERE SessionID = ?
                    """,
                    (1 if timed_out else 0, self.current_session_id)
                )
                if not updated:
                    # Fallback without TimedOut if migration hasn't applied yet
                    self.execute_update(
                        """
                        UPDATE ReviewSessions
                        SET EndTime = GETDATE(),
                            DurationSeconds = DATEDIFF(second, StartTime, GETDATE())
                        WHERE SessionID = ?
                        """,
                        (self.current_session_id,)
                    )
        except Exception as e:
            print(f"Error ending session: {e}")
        finally:
            self.current_session_id = None
            self.session_start_time = None
    
    def toggle_favorite(self):
        """Toggle the favorite status of the current fact"""
        if not self.current_fact_id:
            return
        
        # Toggle the favorite status
        new_status = not self.current_fact_is_favorite
        
        # Update in database
        success = self.execute_update("""
            UPDATE Facts 
            SET IsFavorite = ?
            WHERE FactID = ?
        """, (1 if new_status else 0, self.current_fact_id))
        
        if success:
            # Update local state
            self.current_fact_is_favorite = new_status
            
            # Update star icon
            if new_status:
                self.star_button.config(image=self.gold_star_icon)
                self.status_label.config(text="Added to favorites!", fg=self.YELLOW_COLOR)
            else:
                self.star_button.config(image=self.white_star_icon)
                self.status_label.config(text="Removed from favorites", fg=self.STATUS_COLOR)
            
            # Update the fact in our list
            if self.all_facts and self.current_fact_index < len(self.all_facts):
                fact = list(self.all_facts[self.current_fact_index])
                if len(fact) > 2:
                    fact[2] = new_status
                else:
                    fact.append(new_status)
                self.all_facts[self.current_fact_index] = tuple(fact)
            
            self.clear_status_after_delay(2000)

    def toggle_easy(self):
        """Toggle the 'known/easy' status of the current fact"""
        if not self.current_fact_id:
            return
        if not self.column_exists('Facts', 'IsEasy'):
            self.status_label.config(text="Please update DB to latest (IsEasy column)", fg=self.STATUS_COLOR)
            self.clear_status_after_delay(3000)
            return
        new_status = not self.current_fact_is_easy
        success = self.execute_update("""
            UPDATE Facts
            SET IsEasy = ?
            WHERE FactID = ?
        """, (1 if new_status else 0, self.current_fact_id))
        if success:
            self.current_fact_is_easy = new_status
            if new_status:
                self.easy_button.config(image=self.easy_gold_icon)
                self.status_label.config(text="Marked as known!", fg=self.GREEN_COLOR)
            else:
                self.easy_button.config(image=self.easy_icon)
                self.status_label.config(text="Marked as not known", fg=self.STATUS_COLOR)
            # Update in-memory list
            if self.all_facts and self.current_fact_index < len(self.all_facts):
                fact = list(self.all_facts[self.current_fact_index])
                # Ensure list length
                while len(fact) < 4:
                    fact.append(False)
                fact[3] = new_status
                self.all_facts[self.current_fact_index] = tuple(fact)
            self.clear_status_after_delay(2000)
    
    def add_new_fact(self):
        """Add a new fact to the database"""
        # Create a popup window
        add_window = tk.Toplevel(self.root)
        add_window.title("Add New Fact")
        add_window.geometry(f"{self.POPUP_ADD_CARD_SIZE}{self.POPUP_POSITION}")
        add_window.configure(bg=self.BG_COLOR)
        
        # Get categories for dropdown
        categories = self.fetch_query("SELECT CategoryName FROM Categories WHERE IsActive = 1")
        category_names = [cat[0] for cat in categories] if categories else []
        
        # Create and place widgets
        tk.Label(add_window, text="Add New Fact", fg=self.TEXT_COLOR, bg=self.BG_COLOR, 
                font=self.TITLE_FONT).pack(pady=10)
        
        # Category selection
        cat_frame = tk.Frame(add_window, bg=self.BG_COLOR)
        cat_frame.pack(fill="x", padx=20, pady=5)
        
        tk.Label(cat_frame, text="Category:", fg=self.TEXT_COLOR, bg=self.BG_COLOR, 
                font=self.NORMAL_FONT).pack(side="left", padx=5)
        
        cat_var = tk.StringVar(add_window)
        if category_names:
            cat_var.set(category_names[0])
        else:
            cat_var.set("No Categories")
        
        # Create the combobox with custom styling
        cat_dropdown = ttk.Combobox(cat_frame, 
                                   textvariable=cat_var, 
                                   values=category_names, 
                                   state="readonly", 
                                   width=20,
                                   style='Custom.TCombobox')
        
        cat_dropdown.pack(side="left", padx=5, fill="x", expand=True)
        
        # Fact content
        content_frame = tk.Frame(add_window, bg=self.BG_COLOR)
        content_frame.pack(fill="x", padx=20, pady=5)
        
        tk.Label(content_frame, text="Fact:", fg=self.TEXT_COLOR, bg=self.BG_COLOR, 
                font=self.NORMAL_FONT).pack(side="top", anchor="w", padx=5)
        
        content_text = tk.Text(content_frame, height=8, width=40, font=self.NORMAL_FONT)
        content_text.pack(fill="x", padx=5, pady=5)
        
        def save_fact():
            category = cat_var.get()
            content = content_text.get("1.0", "end-1c").strip()
            
            if not content:
                self.status_label.config(text="Fact content is required!", fg=self.RED_COLOR)
                self.clear_status_after_delay(3000)
                return
            
            # Get category ID
            cat_result = self.fetch_query("SELECT CategoryID FROM Categories WHERE CategoryName = ?", (category,))
            if not cat_result or len(cat_result) == 0:
                self.status_label.config(text="Category not found!", fg=self.RED_COLOR)
                self.clear_status_after_delay(3000)
                return
                
            category_id = cat_result[0][0]
            
            # Insert the new fact
            success = self.execute_update(
                """
                INSERT INTO Facts (CategoryID, Content, DateAdded, ReviewCount, TotalViews, IsFavorite) 
                VALUES (?, ?, GETDATE(), 0, 0, 0)
                """, 
                (category_id, content)
            )
            
            if success:
                add_window.destroy()
                self.status_label.config(text="New fact added successfully!", fg=self.GREEN_COLOR)
                self.clear_status_after_delay(3000)
                self.update_fact_count()
                # Reload facts if we're in viewing mode
                if not self.is_home_page:
                    self.load_all_facts()
                    if self.all_facts:
                        self.current_fact_index = len(self.all_facts) - 1
                        self.display_current_fact()
            else:
                self.status_label.config(text="Error adding new fact!", fg=self.RED_COLOR)
                self.clear_status_after_delay(3000)
        
        # Save button
        save_button = tk.Button(add_window, text="Save Fact", bg=self.GREEN_COLOR, fg=self.TEXT_COLOR, 
                              command=save_fact, cursor="hand2", borderwidth=0, 
                              highlightthickness=0, padx=10, pady=5,
                              font=(self.NORMAL_FONT[0], self.NORMAL_FONT[1], 'bold'))
        save_button.pack(pady=20)
    
    def edit_current_fact(self):
        """Edit the current fact"""
        if not self.current_fact_id:
            return
        
        # Get current fact data
        query = """
        SELECT f.Content, c.CategoryName
        FROM Facts f 
        JOIN Categories c ON f.CategoryID = c.CategoryID
        WHERE f.FactID = ?
        """
        result = self.fetch_query(query, (self.current_fact_id,))
        
        if not result or len(result) == 0:
            self.status_label.config(text="Error: Could not retrieve fact data", fg=self.RED_COLOR)
            self.clear_status_after_delay()
            return
            
        current_content, current_category = result[0]
        
        # Create a popup window
        edit_window = tk.Toplevel(self.root)
        edit_window.title("Edit Fact")
        edit_window.geometry(f"{self.POPUP_EDIT_CARD_SIZE}{self.POPUP_POSITION}")
        edit_window.configure(bg=self.BG_COLOR)
        
        # Get categories for dropdown
        categories = self.fetch_query("SELECT CategoryName FROM Categories WHERE IsActive = 1")
        category_names = [cat[0] for cat in categories] if categories else []
        
        # Create and place widgets
        tk.Label(edit_window, text="Edit Fact", fg=self.TEXT_COLOR, bg=self.BG_COLOR, 
                font=self.TITLE_FONT).pack(pady=10)
        
        # Category selection
        cat_frame = tk.Frame(edit_window, bg=self.BG_COLOR)
        cat_frame.pack(fill="x", padx=20, pady=5)
        
        tk.Label(cat_frame, text="Category:", fg=self.TEXT_COLOR, bg=self.BG_COLOR, 
                font=self.NORMAL_FONT).pack(side="left", padx=5)
        
        cat_var = tk.StringVar(edit_window)
        cat_var.set(current_category)
        
        # Create the combobox with custom styling
        cat_dropdown = ttk.Combobox(cat_frame, 
                                   textvariable=cat_var, 
                                   values=category_names, 
                                   state="readonly", 
                                   width=20,
                                   style='Custom.TCombobox')
        
        cat_dropdown.pack(side="left", padx=5, fill="x", expand=True)
        
        # Fact content
        content_frame = tk.Frame(edit_window, bg=self.BG_COLOR)
        content_frame.pack(fill="x", padx=20, pady=5)
        
        tk.Label(content_frame, text="Fact:", fg=self.TEXT_COLOR, bg=self.BG_COLOR, 
                font=self.NORMAL_FONT).pack(side="top", anchor="w", padx=5)
        
        content_text = tk.Text(content_frame, height=8, width=40, font=self.NORMAL_FONT)
        content_text.insert("1.0", current_content)
        content_text.pack(fill="x", padx=5, pady=5)
        
        def update_fact():
            category = cat_var.get()
            content = content_text.get("1.0", "end-1c").strip()
            
            if not content:
                self.status_label.config(text="Fact content is required!", fg=self.RED_COLOR)
                self.clear_status_after_delay(3000)
                return
            
            # Get category ID
            cat_result = self.fetch_query("SELECT CategoryID FROM Categories WHERE CategoryName = ?", (category,))
            if not cat_result or len(cat_result) == 0:
                self.status_label.config(text="Category not found!", fg=self.RED_COLOR)
                self.clear_status_after_delay(3000)
                return
                
            category_id = cat_result[0][0]
            
            # Update the fact
            success = self.execute_update(
                """
                UPDATE Facts 
                SET CategoryID = ?, Content = ?
                WHERE FactID = ?
                """, 
                (category_id, content, self.current_fact_id)
            )
            
            if success:
                edit_window.destroy()
                self.status_label.config(text="Fact updated successfully!", fg=self.GREEN_COLOR)
                self.clear_status_after_delay(3000)
                
                # Update the current display
                self.fact_label.config(text=content, font=(self.NORMAL_FONT[0], self.adjust_font_size(content)))
                # Update the fact in our list
                if self.all_facts and self.current_fact_index < len(self.all_facts):
                    self.all_facts[self.current_fact_index] = (self.current_fact_id, content)
            else:
                self.status_label.config(text="Error updating fact!", fg=self.RED_COLOR)
                self.clear_status_after_delay(3000)
        
        # Update button
        update_button = tk.Button(edit_window, text="Update Fact", bg=self.BLUE_COLOR, fg=self.TEXT_COLOR, 
                                command=update_fact, cursor="hand2", borderwidth=0, 
                                highlightthickness=0, padx=10, pady=5,
                                font=(self.NORMAL_FONT[0], self.NORMAL_FONT[1], 'bold'))
        update_button.pack(pady=20)
    
    def delete_current_fact(self):
        """Delete the current fact"""
        if not self.current_fact_id:
            return
        
        # Ask for confirmation
        if self.confirm_dialog("Confirm Delete", "Are you sure you want to delete this fact?"):
            # Delete the fact
            success = self.execute_update("DELETE FROM Facts WHERE FactID = ?", (self.current_fact_id,))
            if success:
                self.status_label.config(text="Fact deleted!", fg=self.RED_COLOR)
                self.clear_status_after_delay(3000)
                self.update_fact_count()
                
                # Remove from our list and show next fact
                if self.all_facts and self.current_fact_index < len(self.all_facts):
                    self.all_facts.pop(self.current_fact_index)
                    if self.all_facts:
                        self.current_fact_index = self.current_fact_index % len(self.all_facts)
                        self.display_current_fact()
                    else:
                        self.fact_label.config(text="No facts found. Add some facts first!")
                        self.current_fact_id = None
            else:
                self.status_label.config(text="Error deleting fact!", fg=self.RED_COLOR)
                self.clear_status_after_delay(3000)
    
    def manage_categories(self):
        """Open a window to manage categories"""
        # Create the category management window
        cat_window = self._create_category_window()
        
        # Create the UI components
        self._create_add_category_ui(cat_window)
        _, cat_listbox, refresh_category_list = self._create_category_list_ui(cat_window)
        self._create_category_action_buttons(cat_window, cat_listbox, refresh_category_list)
        
        # Initialize the category list
        refresh_category_list()
    
    def _create_category_window(self):
        """Create the main category management window"""
        cat_window = tk.Toplevel(self.root)
        cat_window.title("Manage Categories")
        try:
            cat_window.geometry(f"{self.POPUP_CATEGORIES_SIZE}{self.POPUP_POSITION}")
        except Exception:
            cat_window.geometry(self.POPUP_CATEGORIES_SIZE)
        cat_window.configure(bg=self.BG_COLOR)
        
        # Create header
        tk.Label(cat_window, text="Manage Categories", fg=self.TEXT_COLOR, bg=self.BG_COLOR, 
                font=self.TITLE_FONT).pack(pady=10)
        
        return cat_window
    
    def _create_add_category_ui(self, parent):
        """Create the UI for adding a new category"""
        # Add new category frame
        add_frame = tk.Frame(parent, bg=self.BG_COLOR)
        add_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Label(add_frame, text="New Category:", fg=self.TEXT_COLOR, bg=self.BG_COLOR, 
                font=self.NORMAL_FONT).pack(side="left", padx=5)
        
        new_cat_entry = tk.Entry(add_frame, width=20, font=self.NORMAL_FONT)
        new_cat_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        add_button = tk.Button(add_frame, text="Add", bg=self.GREEN_COLOR, fg=self.TEXT_COLOR, 
                            command=lambda: self._add_category(new_cat_entry), 
                            cursor="hand2", borderwidth=0, highlightthickness=0, padx=10)
        add_button.pack(side="left", padx=5)
        
        # No return needed; widgets are attached to the parent and remain alive
    
    def _add_category(self, entry_widget):
        """Handle adding a new category"""
        new_cat = entry_widget.get().strip()
        if not new_cat:
            return
        
        # Check if category already exists
        existing = self.fetch_query("SELECT COUNT(*) FROM Categories WHERE CategoryName = ?", (new_cat,))
        if existing and existing[0][0] > 0:
            tk.messagebox.showinfo("Error", f"Category '{new_cat}' already exists!")
            return
        
        # Add the new category
        success = self.execute_update(
            "INSERT INTO Categories (CategoryName, Description) VALUES (?, '')", 
            (new_cat,)
        )
        
        if success:
            entry_widget.delete(0, tk.END)
            # Refresh UI elements
            self.update_category_dropdown()
            return True
        else:
            tk.messagebox.showinfo("Error", "Failed to add new category!")
            return False
    
    def _create_category_list_ui(self, parent):
        """Create the UI for displaying and managing the category list"""
        # Category list frame
        list_frame = tk.Frame(parent, bg=self.BG_COLOR)
        list_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        tk.Label(list_frame, text="Existing Categories:", fg=self.TEXT_COLOR, bg=self.BG_COLOR, 
                font=(self.NORMAL_FONT[0], self.NORMAL_FONT[1], 'bold')).pack(anchor="w", pady=5)
        
        # Scrollable list frame
        scroll_frame = tk.Frame(list_frame, bg=self.BG_COLOR)
        scroll_frame.pack(fill="both", expand=True)
        
        scrollbar = tk.Scrollbar(scroll_frame)
        scrollbar.pack(side="right", fill="y")
        
        cat_listbox = tk.Listbox(scroll_frame, height=15, width=30, font=self.NORMAL_FONT,
                              yscrollcommand=scrollbar.set, bg=self.LISTBOX_BG_COLOR, fg=self.TEXT_COLOR,
                              selectbackground=self.GREEN_COLOR, selectforeground=self.TEXT_COLOR)
        cat_listbox.pack(side="left", fill="both", expand=True)
        
        scrollbar.config(command=cat_listbox.yview)
        
        def refresh_category_list():
            cat_listbox.delete(0, tk.END)
            categories = self.fetch_query("SELECT CategoryName, CategoryID FROM Categories ORDER BY CategoryName")
            for cat in categories:
                cat_listbox.insert(tk.END, f"{cat[0]} (ID: {cat[1]})")
        
        return list_frame, cat_listbox, refresh_category_list
    
    def _create_category_action_buttons(self, parent, cat_listbox, refresh_callback):
        """Create action buttons for category management"""
        # Action buttons frame
        action_frame = tk.Frame(parent, bg=self.BG_COLOR)
        action_frame.pack(fill="x", padx=20, pady=10)
        
        # Rename button
        rename_button = tk.Button(action_frame, text="Rename", bg=self.BLUE_COLOR, fg=self.TEXT_COLOR, 
                                command=lambda: self._rename_category(cat_listbox, refresh_callback), 
                                cursor="hand2", borderwidth=0, highlightthickness=0, padx=10, pady=5)
        rename_button.pack(side="left", padx=5)
        
        # Delete button
        delete_button_cat = tk.Button(action_frame, text="Delete", bg=self.RED_COLOR, fg=self.TEXT_COLOR, 
                                    command=lambda: self._delete_category(cat_listbox, refresh_callback), 
                                    cursor="hand2", borderwidth=0, highlightthickness=0, padx=10, pady=5)
        delete_button_cat.pack(side="left", padx=5)
        
        # Close button
        close_button = tk.Button(parent, text="Close", bg=self.GRAY_COLOR, fg=self.TEXT_COLOR, 
                              command=parent.destroy, cursor="hand2", borderwidth=0, 
                              highlightthickness=0, padx=20, pady=5,
                              font=(self.NORMAL_FONT[0], self.NORMAL_FONT[1], 'bold'))
        close_button.pack(pady=15)
    
    def _rename_category(self, cat_listbox, refresh_callback):
        """Handle renaming a category"""
        selection = cat_listbox.curselection()
        if not selection:
            return
        
        # Extract category ID from selection text
        cat_text = cat_listbox.get(selection[0])
        cat_id = int(cat_text.split("ID: ")[1].rstrip(")"))
        
        # Get current name
        cat_result = self.fetch_query("SELECT CategoryName FROM Categories WHERE CategoryID = ?", (cat_id,))
        if not cat_result or len(cat_result) == 0:
            tk.messagebox.showinfo("Error", "Category not found!")
            return
            
        cat_name = cat_result[0][0]
        
        # Ask for new name
        new_name = self.prompt_dialog("Rename Category", f"New name for '{cat_name}':", initialvalue=cat_name)
        if not new_name or new_name == cat_name:
            return
        
        # Check if the new name already exists
        existing = self.fetch_query(
            "SELECT COUNT(*) FROM Categories WHERE CategoryName = ? AND CategoryID != ?", 
            (new_name, cat_id)
        )
        
        if existing and existing[0][0] > 0:
            tk.messagebox.showinfo("Error", f"Category '{new_name}' already exists!")
            return
        
        # Update the category
        success = self.execute_update(
            "UPDATE Categories SET CategoryName = ? WHERE CategoryID = ?", 
            (new_name, cat_id)
        )
        
        if success:
            refresh_callback()
            self.update_category_dropdown()
        else:
            tk.messagebox.showinfo("Error", "Failed to rename category!")
    
    def _delete_category(self, cat_listbox, refresh_callback):
        """Handle deleting a category"""
        selection = cat_listbox.curselection()
        if not selection:
            return
        
        # Extract category ID from selection text
        cat_text = cat_listbox.get(selection[0])
        cat_id = int(cat_text.split("ID: ")[1].rstrip(")"))
        cat_name = cat_text.split(" (ID:")[0]
        
        # Check if category has facts
        fact_count_result = self.fetch_query(
            "SELECT COUNT(*) FROM Facts WHERE CategoryID = ?", 
            (cat_id,)
        )
        
        if not fact_count_result:
            tk.messagebox.showinfo("Error", "Failed to check category content!")
            return
            
        fact_count = fact_count_result[0][0]
        
        if fact_count > 0:
            if not self.confirm_dialog(
                "Warning",
                f"Category '{cat_name}' has {fact_count} facts. Deleting it will also delete all associated facts. Continue?",
                ok_text="Delete",
                cancel_text="Cancel"
            ):
                return
        
        # Delete the category and its facts
        success = self.execute_update("""
            BEGIN TRANSACTION;
            
            DELETE FROM Facts WHERE CategoryID = ?;
            DELETE FROM Categories WHERE CategoryID = ?;
            
            COMMIT TRANSACTION;
        """, (cat_id, cat_id))
        
        if success:
            refresh_callback()
            self.update_category_dropdown()
            self.update_fact_count()
            # Reload facts if we're viewing
            if not self.is_home_page:
                self.load_all_facts()
                if self.all_facts:
                    self.display_current_fact()
        else:
            tk.messagebox.showinfo("Error", "Failed to delete category!")
    
    def update_category_dropdown(self):
        """Update the category dropdown with current categories"""
        categories = self.load_categories()
        self.category_dropdown['values'] = categories
        # Keep current selection if it exists in new list, otherwise reset
        current_category = self.category_var.get()
        if current_category in categories:
            self.category_var.set(current_category)
        else:
            self.category_var.set("All Categories")
    
    def adjust_font_size(self, text):
        """Dynamically adjust font size based on text length"""
        return max(8, min(12, int(12 - (len(text) / 150))))
    
    def create_label(self, parent, text, fg="white", cursor=None, font=("Trebuchet MS", 7), side='left'):
        """Create a styled label"""
        label = tk.Label(parent, text=text, fg=fg, bg=self.BG_COLOR, font=font)
        if cursor:
            label.configure(cursor=cursor)
        label.pack(side=side)
        return label
    
    def on_category_change(self, event=None):
        """Handle category dropdown change"""
        self.load_all_facts()
        if self.all_facts and not self.is_home_page:
            self.display_current_fact()
    
    def clear_status_after_delay(self, delay_ms=3000):
        """Clear the status message after a specified delay"""
        self.root.after(delay_ms, lambda: self.status_label.config(text=""))
    
    def show_home_page(self):
        """Show the home page with welcome message and start button"""
        # End any active reviewing session and finalize current view
        self.end_active_session()
        self.is_home_page = True
        
        # Hide all fact-related UI elements
        self.stats_frame.pack_forget()
        self.icon_buttons_frame.pack_forget()
        self.nav_frame.pack_forget()
        self.category_frame.pack_forget()
        self.single_card_label.pack_forget()  # Hide warning label

        # Swap star with info icon on home page
        try:
            # Stop any ongoing speech and hide speaker on home
            self.stop_speaking()
            self.star_button.place_forget()
            # Hide easy button on home page
            try:
                self.easy_button.place_forget()
            except Exception:
                pass
            self.info_button.place(relx=1.0, rely=0, anchor="ne", x=-55, y=5)
            # Hide speaker on home page
            self.speaker_button.place_forget()
        except Exception:
            pass
        
        # Update the welcome message
        self.fact_label.config(text="Welcome to FactDari!\n\nYour Simple Fact Viewer", 
                             font=self.LARGE_FONT,
                             wraplength=450, justify="center")
        
        # Show the slogan
        self.slogan_label.config(text="Review and remember facts effortlessly")
        self.slogan_label.pack(side="top", pady=5)
        
        # Show the start reviewing button
        self.start_button.pack(pady=20)
        
        # Update status to shortcut hint
        self.status_label.config(text="Shortcuts: Prev = Left/p, Next = Right/n/Space", fg=self.STATUS_COLOR)

        # Apply rounded corners again after UI changes
        self.root.update_idletasks()
        self.apply_rounded_corners()
    
    def start_reviewing(self):
        """Switch from home page to fact viewing interface"""
        self.is_home_page = False
        self.record_activity()

        # Start a new reviewing session
        try:
            self.start_new_session()
        except Exception as _:
            pass

        # Hide home page elements
        self.slogan_label.pack_forget()
        self.start_button.pack_forget()
        
        # Show all fact-related UI elements
        self.category_frame.pack(side="right", padx=5, pady=3)
        self.nav_frame.pack(side="top", fill="x", pady=10)
        self.icon_buttons_frame.pack(side="top", fill="x", pady=5)
        self.stats_frame.pack(side="bottom", fill="x", padx=10, pady=3)

        # Swap back: hide info, show star icon
        try:
            self.info_button.place_forget()
            # Show easy button before star
            self.easy_button.place(relx=1.0, rely=0, anchor="ne", x=-80, y=5)
            self.star_button.place(relx=1.0, rely=0, anchor="ne", x=-55, y=5)
            # Show speaker on reviewing page
            self.speaker_button.place(relx=1.0, rely=0, anchor="ne", x=-5, y=5)
        except Exception:
            pass
        
        # Load facts and display the first one
        self.load_all_facts()
        if self.all_facts:
            self.display_current_fact()
        else:
            self.fact_label.config(text="No facts found. Add some facts first!")
        
        # Show shortcut hints
        self.status_label.config(text="Shortcuts: ← Previous, → Next, Space Next", fg=self.STATUS_COLOR)

        # Apply rounded corners again after UI changes
        self.root.update_idletasks()
        self.apply_rounded_corners()

    def run(self):
        """Start the application mainloop"""
        self.root.mainloop()

    # Activity/idle helpers
    def record_activity(self):
        """Record user activity and reset idle trigger."""
        self.last_activity_time = datetime.now()
        self.idle_triggered = False

    def handle_idle_timeout(self):
        """Handle inactivity: finalize current view and optionally end session."""
        self.idle_triggered = True
        try:
            # Finalize current fact view as timed out
            self.finalize_current_fact_view(timed_out=True)
            if self.idle_end_session:
                # End the session as timed out
                self.end_active_session(timed_out=True)
                # Optionally navigate to Home after ending session
                if self.idle_navigate_home:
                    try:
                        self.show_home_page()
                    except Exception:
                        pass
            # Let the user know
            try:
                msg = "Ended due to inactivity"
                if self.idle_navigate_home and self.idle_end_session:
                    msg += "; returned to Home"
                self.status_label.config(text=msg, fg=self.STATUS_COLOR)
                self.clear_status_after_delay(4000)
            except Exception:
                pass
        except Exception:
            pass


# Usage example
if __name__ == "__main__":
    app = FactDariApp()
    app.run()
