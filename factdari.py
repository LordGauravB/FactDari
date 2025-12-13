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
import requests
import time
import re
from ctypes import wintypes
from PIL import Image, ImageTk
from datetime import datetime, timedelta
from tkinter import ttk, simpledialog, messagebox
from tkinter import font as tkfont
import gamification

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
        self.POPUP_ACHIEVEMENTS_SIZE = config.UI_CONFIG.get('popup_achievements_size', self.POPUP_INFO_SIZE)
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
        # Brand colors for welcome page
        self.BRAND_FACT_COLOR = config.UI_CONFIG.get('brand_fact_color', '#34d399')
        self.BRAND_DARI_COLOR = config.UI_CONFIG.get('brand_dari_color', '#38bdf8')
        
        # Fonts
        self.TITLE_FONT = config.get_font('title')
        self.NORMAL_FONT = config.get_font('normal')
        self.SMALL_FONT = config.get_font('small')
        self.LARGE_FONT = config.get_font('large')
        self.STATS_FONT = config.get_font('stats')

        # AI model/pricing (used for logging and cost estimation)
        self.ai_model = config.AI_PRICING.get('model', "deepseek-ai/DeepSeek-V3.1")
        self.ai_provider = config.AI_PRICING.get('provider', "together")
        try:
            self.ai_prompt_cost_per_1k = float(config.AI_PRICING.get('prompt_cost_per_1k', 0) or 0)
        except Exception:
            self.ai_prompt_cost_per_1k = 0.0
        try:
            self.ai_completion_cost_per_1k = float(config.AI_PRICING.get('completion_cost_per_1k', 0) or 0)
        except Exception:
            self.ai_completion_cost_per_1k = 0.0
        self.ai_currency = config.AI_PRICING.get('currency', 'USD')
        
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
        self.speech_engine = None  # not used for playback; preserved for future config
        self.speaking_thread = None
        self.active_tts_engine = None  # engine instance used by the current speech thread

        # Timing/session state
        self.current_session_id = None
        self.session_start_time = None
        self.current_fact_start_time = None
        self.current_review_log_id = None
        # Timer pause state (exclude non-review time like add/edit/delete dialogs)
        self.timer_paused = False
        self.pause_started_at = None
        self.category_dropdown_open = False
        self._dropdown_seen_open = False
        # Prevent overlapping AI requests
        self.ai_request_inflight = False
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
        
        # Initialize gamification helper (profile + achievements)
        try:
            self.gamify = gamification.Gamification(self.CONN_STR)
            self.gamify.ensure_profile()
        except Exception:
            self.gamify = None
        
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
        profile_id = self.get_active_profile_id()
        query = "SELECT DISTINCT CategoryName FROM Categories WHERE IsActive = 1 AND CreatedBy = ? ORDER BY CategoryName"
        categories = self.fetch_query(query, (profile_id,))
        base_categories = [category[0] for category in categories] if categories else []

        # Build header filters deterministically
        header = ["All Categories", "Favorites"]
        try:
            has_profile_state = self.column_exists('ProfileFacts', 'IsEasy')
        except Exception:
            has_profile_state = False
        if has_profile_state:
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

        # Brand header for Home (Fact light green, Dari sky blue)
        self.brand_frame = tk.Frame(self.fact_frame, bg=self.BG_COLOR)
        # Render the entire header on a single Canvas for perfect baseline alignment
        brand_font = tkfont.Font(
            family=self.LARGE_FONT[0],
            size=self.LARGE_FONT[1],
            weight=('bold' if len(self.LARGE_FONT) > 2 else 'normal')
        )
        prefix_text = "Welcome to "
        fact_text = "Fact"
        dari_text = "Dari"
        w_prefix = brand_font.measure(prefix_text)
        w_fact = brand_font.measure(fact_text)
        w_dari = brand_font.measure(dari_text)
        total_width = w_prefix + w_fact + w_dari
        line_height = brand_font.metrics('linespace')
        self.brand_canvas = tk.Canvas(
            self.brand_frame,
            bg=self.BG_COLOR,
            highlightthickness=0,
            bd=0,
            width=total_width,
            height=line_height
        )
        # Draw all segments aligned to top-left so they share the same baseline
        x = 0
        y = 0
        self.brand_canvas.create_text(x, y, text=prefix_text, anchor='nw', fill=self.TEXT_COLOR, font=brand_font)
        x += w_prefix
        self.brand_canvas.create_text(x, y, text=fact_text, anchor='nw', fill=self.BRAND_FACT_COLOR, font=brand_font)
        x += w_fact
        self.brand_canvas.create_text(x, y, text=dari_text, anchor='nw', fill=self.BRAND_DARI_COLOR, font=brand_font)
        self.brand_canvas.pack(side='left', padx=0)

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

        # AI explain button (placed before Mark as Known)
        self.ai_button = tk.Button(
            self.fact_frame,
            image=self.ai_icon,
            bg=self.BG_COLOR,
            command=self.explain_fact_with_ai,
            cursor="hand2",
            borderwidth=0,
            highlightthickness=0
        )
        self.ai_button.place(relx=1.0, rely=0, anchor="ne", x=-105, y=5)

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

        # Level label: show next to Home icon (top-left), clickable for Achievements
        self.level_label = tk.Label(self.fact_frame, text="Level 1 - 0 XP", fg=self.GREEN_COLOR, bg=self.BG_COLOR,
                                    font=self.STATS_FONT, cursor="hand2")
        # Place to the right of the Home icon (20px wide) with padding
        self.level_label.place(x=32, y=7)
        try:
            self.level_label.bind("<Button-1>", lambda e: self.show_achievements_window())
        except Exception:
            pass
        
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
        try:
            self.ai_icon = ImageTk.PhotoImage(Image.open(config.get_icon_path("AI.png")).resize((20, 20), Image.Resampling.LANCZOS))
            if hasattr(self, 'ai_button') and self.ai_button:
                self.ai_button.config(image=self.ai_icon)
        except Exception:
            self.ai_icon = None
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
        self.category_dropdown.bind("<Button-1>", self.on_category_dropdown_open, add="+")
        self.category_dropdown.bind("<<ComboboxSelected>>", self.on_category_dropdown_selected)
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
        self.root.bind("r", lambda e: self.start_reviewing())  # Shortcut for start reviewing
        self.root.bind("h", lambda e: self.show_home_page())
        self.root.bind("g", lambda e: self.show_analytics())
        self.root.bind("c", lambda e: self.manage_categories())
        self.root.bind("i", lambda e: self.show_shortcuts_window())  # Shortcut for shortcuts/info
        self.root.bind("l", lambda e: self.show_achievements_window())  # Shortcut for achievements
        self.root.bind("f", lambda e: self.toggle_favorite())  # Shortcut for favorite
        self.root.bind("k", lambda e: self.toggle_easy())  # Shortcut for known/easy
        self.root.bind("x", lambda e: self.explain_fact_with_ai())  # Shortcut for AI explain
        self.root.bind("v", lambda e: self.speak_text())  # Shortcut for speak/voice

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
            ToolTip(self.speaker_button, "Speak text (v)")
            ToolTip(self.star_button, "Toggle favorite (f)")
            ToolTip(self.easy_button, "Mark as known (k)")
            ToolTip(self.ai_button, "AI explain fact (x)")
            ToolTip(self.graph_button, "Analytics (g)")
            ToolTip(self.info_button, "Show shortcuts (i)")
            ToolTip(self.add_icon_button, "Add fact (a)")
            ToolTip(self.edit_icon_button, "Edit fact (e)")
            ToolTip(self.delete_icon_button, "Delete fact (d)")
            ToolTip(self.prev_button, "Previous (<-)")
            ToolTip(self.next_button, "Next (->)")
            ToolTip(self.level_label, "Click for achievements")
        except Exception:
            pass

    def show_shortcuts_window(self):
        """Show a window listing available keyboard shortcuts."""
        # Pause timing while shortcuts popup is open
        try:
            self.pause_review_timer()
        except Exception:
            pass
        win = tk.Toplevel(self.root)
        win.title("Keyboard Shortcuts")
        # Size and position per UI config
        try:
            win.geometry(f"{self.POPUP_INFO_SIZE}{self.POPUP_POSITION}")
        except Exception:
            win.geometry(self.POPUP_INFO_SIZE)
        win.configure(bg=self.BG_COLOR)

        def on_close():
            try:
                self.resume_review_timer()
            except Exception:
                pass
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", on_close)

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
        row("Start Reviewing", "r")
        row("Analytics", "g")
        row("Categories", "c")
        row("AI Explain", "x")
        row("Speak Text", "v")
        row("Achievements", "l")
        row("Show Shortcuts", "i")
        row("Toggle Favorite", "f")
        row("Mark as Known", "k")
        row("Static Position", "s")

        tk.Button(win, text="Close", command=on_close, bg=self.BLUE_COLOR, fg=self.TEXT_COLOR, cursor="hand2", borderwidth=0, highlightthickness=0, padx=10, pady=5).pack(pady=10)

    def show_achievements_window(self):
        """Display achievements, status, and progress."""
        if not getattr(self, 'gamify', None):
            try:
                self.status_label.config(text="Gamification unavailable", fg=self.STATUS_COLOR)
                self.clear_status_after_delay(2000)
            except Exception:
                pass
            return
        try:
            self.pause_review_timer()
        except Exception:
            pass
        win = tk.Toplevel(self.root)
        win.title("Achievements")
        try:
            win.geometry(f"{self.POPUP_ACHIEVEMENTS_SIZE}{self.POPUP_POSITION}")
        except Exception:
            win.geometry(self.POPUP_ACHIEVEMENTS_SIZE)
        win.configure(bg=self.BG_COLOR)

        def on_close():
            try:
                self.resume_review_timer()
            except Exception:
                pass
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", on_close)

        header = tk.Label(win, text="Achievements", fg=self.TEXT_COLOR, bg=self.BG_COLOR, font=self.TITLE_FONT)
        header.pack(pady=(10, 4))
        sub = tk.Label(win, text="Click a column to resize. Unlocked achievements show in green.", fg=self.STATUS_COLOR, bg=self.BG_COLOR, font=self.SMALL_FONT)
        sub.pack()

        # Treeview for achievements (with scrollbars so all columns are accessible even on small widths)
        cols = ("Status", "Name", "Category", "Progress", "Reward")
        table_frame = tk.Frame(win, bg=self.BG_COLOR)
        table_frame.pack(fill='both', expand=True, padx=10, pady=10)
        # Use grid to position tree + scrollbars
        try:
            table_frame.grid_rowconfigure(0, weight=1)
            table_frame.grid_columnconfigure(0, weight=1)
        except Exception:
            pass
        tree = ttk.Treeview(table_frame, columns=cols, show='headings', height=16)
        for c, w in (("Status", 80), ("Name", 220), ("Category", 90), ("Progress", 120), ("Reward", 70)):
            tree.heading(c, text=c)
            tree.column(c, width=w, anchor='w')
        # Scrollbars
        vsb = ttk.Scrollbar(table_frame, orient='vertical', command=tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient='horizontal', command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        # Layout
        try:
            tree.grid(row=0, column=0, sticky='nsew')
            vsb.grid(row=0, column=1, sticky='ns')
            hsb.grid(row=1, column=0, sticky='ew')
        except Exception:
            # Fallback to pack if grid unavailable for any reason
            tree.pack(fill='both', expand=True)
            vsb.pack(side='right', fill='y')
            hsb.pack(side='bottom', fill='x')

        # Fetch and populate
        try:
            data = self.gamify.get_achievements_with_status()
        except Exception:
            data = []
        # Sort unlocked (most recent first) above locked
        def _ach_sort(row):
            unlocked_flag = 0 if row.get('Unlocked') else 1
            ts = 0
            try:
                dt = row.get('UnlockDate')
                if dt:
                    ts = float(dt.timestamp()) if hasattr(dt, "timestamp") else 0
            except Exception:
                ts = 0
            category = str(row.get('Category') or "")
            threshold_val = 0
            try:
                threshold_val = int(row.get('Threshold') or 0)
            except Exception:
                threshold_val = 0
            return (unlocked_flag, -ts, category, threshold_val)

        try:
            data = sorted(data, key=_ach_sort)
        except Exception:
            pass
        for row in data:
            unlocked = row.get('Unlocked')
            name = row.get('Name')
            category = row.get('Category')
            threshold = int(row.get('Threshold', 0))
            reward = int(row.get('RewardXP', 0))
            progress = int(row.get('ProgressCurrent', 0))
            status_text = "Unlocked" if unlocked else "Locked"
            prog_text = f"{min(progress, threshold)}/{threshold}"
            vals = (status_text, name, category, prog_text, f"{reward} XP")
            iid = tree.insert('', 'end', values=vals)
            # Color unlocked achievements
            try:
                if unlocked:
                    tree.item(iid, tags=('unlocked',))
            except Exception:
                pass
        try:
            tree.tag_configure('unlocked', foreground=self.GREEN_COLOR)
        except Exception:
            pass

        # Close button
        btns = tk.Frame(win, bg=self.BG_COLOR)
        btns.pack(pady=(0, 10))
        tk.Button(btns, text="Close", command=on_close,
                  bg=self.GRAY_COLOR, fg=self.TEXT_COLOR, cursor="hand2", borderwidth=0, highlightthickness=0, padx=10, pady=5).pack(side='left', padx=6)

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

    def get_active_profile_id(self) -> int:
        """Fetch the current GamificationProfile ID, defaulting to 1."""
        try:
            if getattr(self, 'gamify', None):
                prof = self.gamify.get_profile()
                pid = prof.get('ProfileID') if isinstance(prof, dict) else None
                if pid:
                    return int(pid)
        except Exception:
            pass
        try:
            rows = self.fetch_query("SELECT TOP 1 ProfileID FROM GamificationProfile ORDER BY ProfileID")
            if rows and rows[0]:
                return int(rows[0][0])
        except Exception:
            pass
        return 1

    def ensure_schema(self):
        """No-op: schema is managed externally via factdari_setup.sql."""
        return
    
    def count_facts(self):
        """Count total facts in the database"""
        profile_id = self.get_active_profile_id()
        result = self.fetch_query("SELECT COUNT(*) FROM Facts WHERE CreatedBy = ?", (profile_id,))
        return result[0][0] if result and len(result) > 0 else 0
    
    def get_facts_viewed_today(self):
        """Get count of unique facts viewed today"""
        today = datetime.now().strftime('%Y-%m-%d')
        profile_id = self.get_active_profile_id()
        # Count only actual view actions (exclude add/edit/delete logs)
        query = """
        SELECT COUNT(DISTINCT rl.FactID)
        FROM ReviewLogs rl
        LEFT JOIN ReviewSessions rs ON rs.SessionID = rl.SessionID
        WHERE CONVERT(date, rl.ReviewDate) = CONVERT(date, ?)
          AND (rl.Action IS NULL OR rl.Action = 'view')
          AND (rs.ProfileID = ? OR rl.SessionID IS NULL)
        """
        result = self.fetch_query(query, (today, profile_id))
        return result[0][0] if result and len(result) > 0 else 0

    def update_level_progress(self):
        """Update level label from gamification profile with next-level hint."""
        try:
            if not hasattr(self, 'gamify') or not self.gamify:
                return
            prog = self.gamify.get_level_progress()
            level = prog.get('level', 1)
            xp = prog.get('xp', 0)
            to_next = prog.get('xp_to_next', 0)
            if level >= 100:
                self.level_label.config(text=f"Level {level} - {xp} XP (MAX)")
            else:
                # If progress shows no XP to next but level < 100, it's gated by achievements
                if int(to_next or 0) <= 0:
                    self.level_label.config(text=f"Level {level} - {xp} XP (achievements required)")
                else:
                    self.level_label.config(text=f"Level {level} - {xp} XP ({to_next} to next)")
        except Exception:
            pass
    
    def update_ui(self):
        """Update UI elements periodically"""
        self.update_coordinates()
        if not self.is_home_page:
            self.update_fact_count()
            self.update_review_stats()
            # Update gamification progress
            try:
                self.update_level_progress()
            except Exception:
                pass
            # Check inactivity only while in reviewing mode
            try:
                if self.current_session_id and not getattr(self, 'timer_paused', False):
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
                # Initialize a fresh engine inside the worker to avoid reuse issues
                engine = pyttsx3.init()
                # Expose this engine so stop_speaking can interrupt it
                self.active_tts_engine = engine
                engine.say(text)
                engine.runAndWait()
            except Exception:
                pass
            finally:
                try:
                    # Clear active engine reference
                    self.active_tts_engine = None
                except Exception:
                    pass
                # Re-enable on UI thread
                self.root.after(0, lambda: self.speaker_button.config(state="normal"))

        self.speaking_thread = threading.Thread(target=_worker, daemon=True)
        self.speaking_thread.start()

    def explain_fact_with_ai(self):
        """Open a popup and ask Together AI to explain the current fact in simple words."""
        if self.is_home_page or not self.current_fact_id:
            return
        if getattr(self, "ai_request_inflight", False):
            try:
                self.status_label.config(text="AI request already in progress…", fg=self.STATUS_COLOR)
                self.clear_status_after_delay(2500)
            except Exception:
                pass
            return

        fact_text = (self.fact_label.cget("text") or "").strip()
        if not fact_text:
            self.status_label.config(text="No fact to explain", fg=self.RED_COLOR)
            self.clear_status_after_delay(3000)
            return

        fact_id = self.current_fact_id
        session_id = self.current_session_id
        api_key = config.get_together_api_key()
        if not api_key:
            messagebox.showerror("API Key Missing", "Set FACTDARI_TOGETHER_API_KEY or TOGETHER_API_KEY environment variable.")
            return

        # Pause session timer while popup is open
        self.pause_review_timer()
        self.ai_request_inflight = True

        win = tk.Toplevel(self.root)
        win.title("AI Fact Explanation")
        try:
            win.geometry(f"{self.POPUP_EDIT_CARD_SIZE}{self.POPUP_POSITION}")
        except Exception:
            win.geometry(self.POPUP_EDIT_CARD_SIZE)
        win.configure(bg=self.BG_COLOR)

        ai_usage_row_id = None
        reading_started_at = None
        track_reading_time = False
        # Disable the AI button until this window closes to avoid duplicate clicks
        try:
            self.ai_button.config(state="disabled")
        except Exception:
            pass

        def on_close():
            nonlocal reading_started_at, ai_usage_row_id, track_reading_time
            duration_sec = 0
            if track_reading_time and reading_started_at is not None:
                try:
                    duration_sec = int(time.perf_counter() - reading_started_at)
                    if duration_sec < 0:
                        duration_sec = 0
                except Exception:
                    duration_sec = 0
            if ai_usage_row_id:
                try:
                    self.execute_update(
                        "UPDATE AIUsageLogs SET ReadingDurationSec = ? WHERE AIUsageID = ?",
                        (duration_sec, ai_usage_row_id),
                    )
                except Exception as exc:
                    print(f"Failed to update AI reading duration: {exc}")
            try:
                self.resume_review_timer()
            except Exception:
                pass
            try:
                self.ai_button.config(state="normal")
            except Exception:
                pass
            try:
                self.ai_request_inflight = False
            except Exception:
                pass
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", on_close)

        tk.Label(win, text="AI Explanation", fg=self.TEXT_COLOR, bg=self.BG_COLOR, font=self.TITLE_FONT).pack(pady=10)

        fact_frame = tk.Frame(win, bg=self.BG_COLOR)
        fact_frame.pack(fill="both", expand=False, padx=20, pady=5)
        tk.Label(fact_frame, text="Fact", fg=self.TEXT_COLOR, bg=self.BG_COLOR, font=self.NORMAL_FONT).pack(anchor="w")
        fact_box = tk.Text(fact_frame, height=4, wrap="word", font=self.NORMAL_FONT, bg=self.LISTBOX_BG_COLOR, fg=self.TEXT_COLOR, bd=0)
        fact_box.insert("1.0", fact_text)
        fact_box.config(state="disabled")
        fact_box.pack(fill="both", expand=True, pady=4)

        explain_frame = tk.Frame(win, bg=self.BG_COLOR)
        explain_frame.pack(fill="both", expand=True, padx=20, pady=5)
        tk.Label(explain_frame, text="AI Explanation", fg=self.TEXT_COLOR, bg=self.BG_COLOR, font=self.NORMAL_FONT).pack(anchor="w")
        explain_box = tk.Text(explain_frame, height=8, wrap="word", font=self.NORMAL_FONT, bg=self.LISTBOX_BG_COLOR, fg=self.TEXT_COLOR, bd=0)
        explain_box.insert("1.0", "Fetching explanation...")
        explain_box.config(state="disabled")
        explain_box.pack(fill="both", expand=True, pady=4)

        def update_text(text, use_markdown=False):
            try:
                if not explain_box.winfo_exists():
                    return
            except Exception:
                return
            if use_markdown:
                self._render_markdown_to_text(explain_box, text)
            else:
                explain_box.config(state="normal")
                explain_box.delete("1.0", "end")
                explain_box.insert("1.0", text.strip())
                explain_box.config(state="disabled")

        def mark_explanation_ready(text):
            nonlocal reading_started_at
            update_text(text, use_markdown=True)
            if track_reading_time and reading_started_at is None:
                try:
                    reading_started_at = time.perf_counter()
                except Exception:
                    reading_started_at = None

        def worker():
            nonlocal ai_usage_row_id, track_reading_time
            result_text, usage_info = self._call_together_ai(fact_text, api_key)

            try:
                ai_usage_row_id = self._record_ai_usage(usage_info, fact_id=fact_id, session_id=session_id, reading_duration_sec=0)
            except Exception as exc:
                print(f"AI usage logging error: {exc}")
                ai_usage_row_id = None

            track_reading_time = (usage_info.get("status") == "SUCCESS")
            
            self.root.after(0, lambda: mark_explanation_ready(result_text))

        threading.Thread(target=worker, daemon=True).start()

    def _call_together_ai(self, fact_text: str, api_key: str):
        """Call Together AI to explain a fact; returns (text, usage_info)."""
        started = time.perf_counter()
        usage_info = {
            "operation_type": "EXPLANATION",
            "model": getattr(self, 'ai_model', "deepseek-ai/DeepSeek-V3.1"),
            "provider": getattr(self, 'ai_provider', "together"),
            "status": "SUCCESS",
        }

        def _record_latency():
            try:
                usage_info["latency_ms"] = int((time.perf_counter() - started) * 1000)
            except Exception:
                pass

        try:
            payload = {
                "model": usage_info["model"],
                "messages": [
                    {
                        "role": "system",
                        "content": "Explain facts simply in 2 short paragraphs. Include a relatable analogy."
                    },
                    {
                        "role": "user",
                        "content": f"Explain simply and wit an analogy in the second short paragraph:\n\n{fact_text}"
                    }
                ],
                "max_tokens": 500,
                "temperature": 0.35,
            }
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            resp = requests.post(
                "https://api.together.xyz/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=30
            )
            _record_latency()
            if resp.status_code != 200:
                usage_info["status"] = "FAILED"
                return f"Error from AI ({resp.status_code}): {resp.text}", usage_info
            data = resp.json()
            choices = data.get("choices") or []
            if not choices:
                usage_info["status"] = "FAILED"
                return "No explanation returned.", usage_info
            message = choices[0].get("message", {}).get("content", "")
            raw_usage = data.get("usage") or {}
            input_tokens = raw_usage.get("prompt_tokens")
            output_tokens = raw_usage.get("completion_tokens")
            total_tokens = raw_usage.get("total_tokens")
            # Fallback computation if total not provided but parts are
            if total_tokens is None and (input_tokens is not None or output_tokens is not None):
                total_tokens = int(input_tokens or 0) + int(output_tokens or 0)
            if total_tokens == 0 and input_tokens is None and output_tokens is None:
                total_tokens = None
            usage_info.update({
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
            })
            return message.strip() or "No explanation returned.", usage_info
        except requests.exceptions.Timeout:
            _record_latency()
            usage_info["status"] = "FAILED"
            return "Timed out contacting AI. Please try again.", usage_info
        except requests.exceptions.ConnectionError:
            _record_latency()
            usage_info["status"] = "FAILED"
            return "Network error reaching AI service. Check your connection or VPN and retry.", usage_info
        except Exception as exc:
            _record_latency()
            usage_info["status"] = "FAILED"
            return f"Failed to fetch explanation: {exc}", usage_info

    def _estimate_ai_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate call cost using configured per-1K token prices."""
        try:
            prompt_val = int(prompt_tokens or 0)
        except Exception:
            prompt_val = 0
        try:
            completion_val = int(completion_tokens or 0)
        except Exception:
            completion_val = 0
        prompt_cost = (prompt_val / 1000.0) * float(getattr(self, 'ai_prompt_cost_per_1k', 0) or 0)
        completion_cost = (completion_val / 1000.0) * float(getattr(self, 'ai_completion_cost_per_1k', 0) or 0)
        return round(prompt_cost + completion_cost, 9)

    def _render_markdown_to_text(self, text_widget, markdown_text):
        """Render markdown text with formatting tags in a tkinter Text widget.

        Supports: **bold**, *italic*, ### headers, and cleans up markdown syntax.
        """
        text_widget.config(state="normal")
        text_widget.delete("1.0", "end")

        # Configure text tags for formatting
        font_family = self.NORMAL_FONT[0] if isinstance(self.NORMAL_FONT, tuple) else "Segoe UI"
        font_size = self.NORMAL_FONT[1] if isinstance(self.NORMAL_FONT, tuple) and len(self.NORMAL_FONT) > 1 else 10

        text_widget.tag_configure("bold", font=(font_family, font_size, "bold"))
        text_widget.tag_configure("italic", font=(font_family, font_size, "italic"))
        text_widget.tag_configure("header", font=(font_family, font_size + 2, "bold"))

        lines = markdown_text.strip().split('\n')

        for i, line in enumerate(lines):
            # Handle headers (### Header)
            header_match = re.match(r'^#{1,6}\s+(.+)$', line)
            if header_match:
                header_text = header_match.group(1).strip()
                text_widget.insert("end", header_text, "header")
                text_widget.insert("end", "\n\n")
                continue

            # Process inline formatting (**bold** and *italic*)
            pos = 0
            # Pattern for **bold** or *italic* (bold first to avoid conflicts)
            pattern = re.compile(r'(\*\*(.+?)\*\*|\*(.+?)\*)')
            last_end = 0

            for match in pattern.finditer(line):
                # Insert text before the match
                if match.start() > last_end:
                    text_widget.insert("end", line[last_end:match.start()])

                # Check if bold (**) or italic (*)
                if match.group(2):  # Bold match
                    text_widget.insert("end", match.group(2), "bold")
                elif match.group(3):  # Italic match
                    text_widget.insert("end", match.group(3), "italic")

                last_end = match.end()

            # Insert remaining text after last match
            if last_end < len(line):
                text_widget.insert("end", line[last_end:])

            # Add newline (double for paragraph breaks on empty lines)
            if i < len(lines) - 1:
                text_widget.insert("end", "\n")

        text_widget.config(state="disabled")

    def _record_ai_usage(self, usage_info: dict, fact_id: int, session_id=None, reading_duration_sec: int = 0):
        """Persist AI usage row and roll totals into gamification profile.
        Returns AIUsageID if insert succeeds (else None).
        """
        if not usage_info:
            return None
        if fact_id is None:
            return None
        model_name = usage_info.get("model") or getattr(self, 'ai_model', None)
        provider = usage_info.get("provider") or getattr(self, 'ai_provider', None)
        operation_type = usage_info.get("operation_type") or "EXPLANATION"
        input_tokens = usage_info.get("input_tokens")
        output_tokens = usage_info.get("output_tokens")
        total_tokens = usage_info.get("total_tokens")

        try:
            input_tokens = int(input_tokens) if input_tokens is not None else None
        except Exception:
            input_tokens = None
        try:
            output_tokens = int(output_tokens) if output_tokens is not None else None
        except Exception:
            output_tokens = None

        if total_tokens is not None:
            try:
                total_tokens = int(total_tokens)
            except Exception:
                total_tokens = None

        if total_tokens is None and (input_tokens is not None or output_tokens is not None):
            total_tokens = (input_tokens or 0) + (output_tokens or 0)

        cost = usage_info.get("cost")
        if cost is None and (input_tokens is not None or output_tokens is not None):
            cost = self._estimate_ai_cost(input_tokens or 0, output_tokens or 0)

        latency_ms = usage_info.get("latency_ms")
        try:
            latency_ms = int(latency_ms) if latency_ms is not None else None
        except Exception:
            latency_ms = None

        try:
            reading_duration_sec = int(reading_duration_sec) if reading_duration_sec is not None else 0
        except Exception:
            reading_duration_sec = 0

        status = usage_info.get("status") or "SUCCESS"
        try:
            status = str(status).upper()
        except Exception:
            status = "SUCCESS"
        if status not in ("SUCCESS", "FAILED"):
            status = "SUCCESS"

        resolved_session_id = session_id if session_id is not None else getattr(self, 'current_session_id', None)

        return self._log_ai_usage(
            fact_id=fact_id,
            session_id=resolved_session_id,
            operation_type=operation_type,
            status=status,
            model_name=model_name,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost=cost,
            latency_ms=latency_ms,
            reading_duration_sec=reading_duration_sec,
        )

    def _log_ai_usage(self, fact_id, session_id, operation_type, status, model_name, provider, input_tokens, output_tokens, total_tokens, cost, latency_ms, reading_duration_sec=0):
        """Insert into AIUsageLogs and roll totals into GamificationProfile. Returns AIUsageID or None."""
        try:
            cost_val = None if cost is None else round(float(cost), 9)
        except Exception:
            cost_val = None

        # Normalize tokens for insert
        it = input_tokens if input_tokens is None else int(input_tokens)
        ot = output_tokens if output_tokens is None else int(output_tokens)
        total_for_profile = total_tokens
        if total_for_profile is None:
            total_for_profile = (0 if it is None else it) + (0 if ot is None else ot)
            if total_for_profile == 0:
                total_for_profile = None

        try:
            reading_duration_sec = int(reading_duration_sec) if reading_duration_sec is not None else 0
        except Exception:
            reading_duration_sec = 0

        profile_id = self.get_active_profile_id()
        ai_usage_id = None
        try:
            ai_usage_id = self.execute_insert_return_id(
                """
                INSERT INTO AIUsageLogs (FactID, SessionID, ProfileID, OperationType, Status, ModelName, Provider, InputTokens, OutputTokens, Cost, CurrencyCode, LatencyMs, ReadingDurationSec)
                OUTPUT INSERTED.AIUsageID
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fact_id,
                    session_id,
                    profile_id,
                    operation_type,
                    status,
                    model_name,
                    provider,
                    it,
                    ot,
                    cost_val,
                    getattr(self, 'ai_currency', 'USD'),
                    latency_ms,
                    reading_duration_sec,
                ),
            )
        except Exception as exc:
            print(f"Database error in _log_ai_usage: {exc}")

        try:
            if self.gamify and (total_for_profile is not None or (cost_val is not None and cost_val != 0)):
                self.gamify.add_ai_usage(total_for_profile or 0, cost_val or 0.0)
        except Exception as exc:
            print(f"Gamification error in _log_ai_usage: {exc}")

        return ai_usage_id

    def stop_speaking(self):
        """Stop any ongoing speech immediately."""
        try:
            # Signal the active engine (if any) to stop
            if getattr(self, 'active_tts_engine', None) is not None:
                try:
                    self.active_tts_engine.stop()
                except Exception:
                    pass
                finally:
                    # Do not reuse this engine
                    self.active_tts_engine = None
            # If a worker thread exists, let it wind down
            if self.speaking_thread and self.speaking_thread.is_alive():
                # Allow thread to wind down
                try:
                    self.speaking_thread.join(timeout=1.0)
                except Exception:
                    pass
            # Ensure UI button is enabled even if thread ended unexpectedly
            try:
                self.speaker_button.config(state="normal")
            except Exception:
                pass
            # Clear reference
            self.speaking_thread = None
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
        profile_id = self.get_active_profile_id()
        base_select = """
            SELECT f.FactID,
                   f.Content,
                   COALESCE(pf.IsFavorite, 0) AS IsFavorite,
                   COALESCE(pf.IsEasy, 0) AS IsEasy
            FROM Facts f
            LEFT JOIN ProfileFacts pf ON pf.FactID = f.FactID AND pf.ProfileID = ?
            WHERE f.CreatedBy = ?
        """

        facts = []
        if category == "All Categories":
            query = base_select + " ORDER BY NEWID()"
            facts = self.fetch_query(query, (profile_id, profile_id))
        elif category == "Favorites":
            query = base_select + " AND COALESCE(pf.IsFavorite,0) = 1 ORDER BY NEWID()"
            facts = self.fetch_query(query, (profile_id, profile_id))
        elif category == "Known":
            query = base_select + " AND COALESCE(pf.IsEasy,0) = 1 ORDER BY NEWID()"
            facts = self.fetch_query(query, (profile_id, profile_id))
        elif category == "Not Known":
            query = base_select + " AND COALESCE(pf.IsEasy,0) = 0 ORDER BY NEWID()"
            facts = self.fetch_query(query, (profile_id, profile_id))
        elif category == "Not Favorite":
            query = base_select + " AND COALESCE(pf.IsFavorite,0) = 0 ORDER BY NEWID()"
            facts = self.fetch_query(query, (profile_id, profile_id))
        else:
            query = base_select + """
                AND EXISTS (
                    SELECT 1 FROM Categories c
                    WHERE c.CategoryID = f.CategoryID
                      AND c.CategoryName = ?
                      AND c.CreatedBy = ?
                )
                ORDER BY NEWID()
            """
            facts = self.fetch_query(query, (profile_id, profile_id, category, profile_id))

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
                end_point = now
                # If currently paused, cap at pause start so paused time isn't counted
                try:
                    if getattr(self, "timer_paused", False) and self.pause_started_at:
                        end_point = self.pause_started_at
                except Exception:
                    pass
                elapsed = int((end_point - self.current_fact_start_time).total_seconds())
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
                # Award XP for the just-finished view
                try:
                    self._award_for_elapsed(elapsed)
                except Exception:
                    pass
        except Exception as _:
            pass

        # 2) Update the fact's view count and last viewed date
        self.execute_update("""
            UPDATE Facts
            SET TotalViews = TotalViews + 1
            WHERE FactID = ? AND CreatedBy = ?
        """, (fact_id, self.get_active_profile_id()))
        # Per-profile view count and last viewed
        try:
            pid = self.get_active_profile_id()
            self.execute_update(
                """
                MERGE ProfileFacts AS target
                USING (SELECT ? AS ProfileID, ? AS FactID) AS src
                ON target.ProfileID = src.ProfileID AND target.FactID = src.FactID
                WHEN MATCHED THEN
                    UPDATE SET PersonalReviewCount = ISNULL(target.PersonalReviewCount,0) + 1,
                               LastViewedByUser = GETDATE()
                WHEN NOT MATCHED THEN
                    INSERT (ProfileID, FactID, PersonalReviewCount, IsFavorite, IsEasy, LastViewedByUser)
                    VALUES (src.ProfileID, src.FactID, 1, 0, 0, GETDATE());
                """,
                (pid, fact_id)
            )
        except Exception:
            pass

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

        # Force a streak check-in now that a log exists for today
        try:
            if getattr(self, 'gamify', None):
                # Calculate new streak based on the log we just inserted
                result = self.gamify.daily_checkin()

                # Optional: Update UI feedback immediately
                prof = result.get('profile', {}) if isinstance(result, dict) else {}
                streak = prof.get('CurrentStreak', 0)
                if streak and int(streak) > 0:
                    # Update the status label briefly to show streak is active
                    if not hasattr(self, '_streak_shown_today'):
                        self.status_label.config(
                            text=f"Streak active: {streak} day(s)!",
                            fg=self.GREEN_COLOR
                        )
                        self.clear_status_after_delay(3000)
                        self._streak_shown_today = True
        except Exception as e:
            print(f"Error updating streak: {e}")

    def pause_review_timer(self):
        """Pause the current review timer (exclude time until resumed)."""
        try:
            if self.current_fact_start_time and not self.timer_paused:
                self.pause_started_at = datetime.now()
                self.timer_paused = True
        except Exception:
            pass

    def resume_review_timer(self):
        """Resume the review timer, shifting the start time forward by the paused duration."""
        try:
            if self.timer_paused:
                if self.current_fact_start_time and self.pause_started_at:
                    delta = datetime.now() - self.pause_started_at
                    # Shift start forward to exclude paused duration
                    self.current_fact_start_time = self.current_fact_start_time + delta
                self.pause_started_at = None
                self.timer_paused = False
                self.category_dropdown_open = False
        except Exception:
            pass

    def finalize_current_fact_view(self, timed_out=False):
        """Finalize timing for the current fact view, if active.
        If timed_out=True, also mark the log as ended due to inactivity.
        """
        try:
            if self.current_review_log_id and self.current_fact_start_time:
                # If timing out, cap elapsed at last activity to avoid counting idle time
                end_ts = None
                try:
                    if timed_out and getattr(self, "last_activity_time", None):
                        end_ts = self.last_activity_time
                except Exception:
                    end_ts = None
                if end_ts is None:
                    end_ts = datetime.now()
                # If paused, cap at pause start so paused time is excluded even if not resumed yet
                try:
                    if getattr(self, "timer_paused", False) and self.pause_started_at:
                        end_ts = min(end_ts, self.pause_started_at)
                except Exception:
                    pass
                elapsed = int((end_ts - self.current_fact_start_time).total_seconds())
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
                # Award XP
                try:
                    self._award_for_elapsed(elapsed)
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            self.current_review_log_id = None
            self.current_fact_start_time = None

    def start_new_session(self):
        """Start a new reviewing session and store SessionID."""
        # End any existing session first
        self.end_active_session()
        # Reset per-session duplicate guard so single-card categories track one view per session
        try:
            self._last_tracked_fact = None
        except Exception:
            pass
        self.session_start_time = datetime.now()
        profile_id = self.get_active_profile_id()
        session_id = self.execute_insert_return_id(
            """
            INSERT INTO ReviewSessions (ProfileID, StartTime)
            OUTPUT INSERTED.SessionID
            VALUES (?, GETDATE())
            """,
            (profile_id,)
        )
        self.current_session_id = session_id
        # Daily streak check-in and possible achievements
        try:
            if getattr(self, 'gamify', None):
                result = self.gamify.daily_checkin()
                unlocked = result.get('unlocked', []) if isinstance(result, dict) else []
                prof = result.get('profile', {}) if isinstance(result, dict) else {}
                if prof and isinstance(prof, dict):
                    streak = prof.get('CurrentStreak', None)
                    if streak:
                        try:
                            self.status_label.config(text=f"Daily streak: {int(streak)} day(s)", fg=self.STATUS_COLOR)
                            self.clear_status_after_delay(2500)
                        except Exception:
                            pass
                if unlocked:
                    codes = [x.get('Code') for x in unlocked if x.get('Code')]
                    try:
                        self.gamify.mark_unlocked_notified_by_codes(codes)
                    except Exception:
                        pass
                    try:
                        self.status_label.config(text=f"Achievement: {unlocked[-1]['Name']} (+{unlocked[-1]['RewardXP']} XP)", fg=self.GREEN_COLOR)
                        self.clear_status_after_delay(2500)
                    except Exception:
                        pass
                # Refresh level display
                self.update_level_progress()
        except Exception:
            pass

    def end_active_session(self, timed_out=False):
        """End the active reviewing session, if any. If timed_out=True, marks session TimedOut."""
        try:
            # Finalize any ongoing fact view first
            self.finalize_current_fact_view(timed_out=False)

            if self.current_session_id:
                # Compute duration ignoring idle time after last activity when timed out
                duration_seconds = None
                try:
                    end_marker = None
                    if timed_out and getattr(self, "last_activity_time", None):
                        end_marker = self.last_activity_time
                    if end_marker is None:
                        end_marker = datetime.now()
                    if self.session_start_time:
                        duration_seconds = int((end_marker - self.session_start_time).total_seconds())
                        if duration_seconds < 0:
                            duration_seconds = 0
                except Exception:
                    duration_seconds = None
                if duration_seconds is None:
                    try:
                        if self.session_start_time:
                            duration_seconds = int((datetime.now() - self.session_start_time).total_seconds())
                            if duration_seconds < 0:
                                duration_seconds = 0
                    except Exception:
                        duration_seconds = 0
                if duration_seconds is None:
                    duration_seconds = 0

                updated = self.execute_update(
                    """
                    UPDATE ReviewSessions
                    SET EndTime = DATEADD(second, ?, StartTime),
                        DurationSeconds = ?,
                        TimedOut = ?
                    WHERE SessionID = ?
                    """,
                    (
                        duration_seconds,
                        duration_seconds,
                        1 if timed_out else 0,
                        self.current_session_id
                    )
                )
                if not updated:
                    # Fallback without TimedOut if migration hasn't applied yet
                    self.execute_update(
                        """
                        UPDATE ReviewSessions
                        SET EndTime = DATEADD(second, ?, StartTime),
                            DurationSeconds = ?
                        WHERE SessionID = ?
                        """,
                        (
                            duration_seconds,
                            duration_seconds,
                            self.current_session_id
                        )
                    )
        except Exception as e:
            print(f"Error ending session: {e}")
        finally:
            self.current_session_id = None
            self.session_start_time = None
    
    def toggle_favorite(self):
        """Toggle the favorite status of the current fact"""
        if self.is_home_page or not self.current_fact_id:
            return
        profile_id = self.get_active_profile_id()

        # Toggle the favorite status
        new_status = not self.current_fact_is_favorite

        # Update in database (per profile)
        success = self.execute_update(
            """
            MERGE ProfileFacts AS target
            USING (SELECT ? AS ProfileID, ? AS FactID) AS src
            ON target.ProfileID = src.ProfileID AND target.FactID = src.FactID
            WHEN MATCHED THEN
                UPDATE SET IsFavorite = ?, LastViewedByUser = COALESCE(target.LastViewedByUser, GETDATE())
            WHEN NOT MATCHED THEN
                INSERT (ProfileID, FactID, PersonalReviewCount, IsFavorite, IsEasy, LastViewedByUser)
                VALUES (src.ProfileID, src.FactID, 0, ?, 0, GETDATE());
            """,
            (profile_id, self.current_fact_id, 1 if new_status else 0, 1 if new_status else 0)
        )

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
            # Gamification: award on favorite and unlock using current favorites count
            try:
                if new_status and getattr(self, 'gamify', None):
                    # Increment lifetime counter
                    _ = self.gamify.increment_counter('TotalFavorites', 1)
                    # Compute current number of favorites from Facts
                    try:
                        rows = self.fetch_query("SELECT COUNT(*) FROM ProfileFacts WHERE ProfileID = ? AND IsFavorite = 1", (profile_id,))
                        current_fav_count = int(rows[0][0]) if rows else 0
                    except Exception:
                        current_fav_count = 0
                    unlocked = self.gamify.unlock_achievements_if_needed('favorites', current_fav_count)
                    # XP for favoriting
                    fav_xp = int(config.XP_CONFIG.get('xp_favorite', 1))
                    if fav_xp:
                        self.gamify.award_xp(fav_xp)
                    if unlocked:
                        self.status_label.config(text=f"Achievement: {unlocked[-1]['Name']} (+{unlocked[-1]['RewardXP']} XP)", fg=self.GREEN_COLOR)
                        self.clear_status_after_delay(2500)
                        try:
                            self.gamify.mark_unlocked_notified_by_codes([u.get('Code') for u in unlocked if u.get('Code')])
                        except Exception:
                            pass
                    self.update_level_progress()
            except Exception:
                pass

    def toggle_easy(self):
        """Toggle the 'known/easy' status of the current fact"""
        if self.is_home_page or not self.current_fact_id:
            return
        profile_id = self.get_active_profile_id()
        new_status = not self.current_fact_is_easy
        if new_status:
            # Marking as known: set KnownSince only if not already set
            success = self.execute_update(
                """
                MERGE ProfileFacts AS target
                USING (SELECT ? AS ProfileID, ? AS FactID) AS src
                ON target.ProfileID = src.ProfileID AND target.FactID = src.FactID
                WHEN MATCHED THEN
                    UPDATE SET IsEasy = 1, LastViewedByUser = COALESCE(target.LastViewedByUser, GETDATE()),
                               KnownSince = COALESCE(target.KnownSince, GETDATE())
                WHEN NOT MATCHED THEN
                    INSERT (ProfileID, FactID, PersonalReviewCount, IsFavorite, IsEasy, LastViewedByUser, KnownSince)
                    VALUES (src.ProfileID, src.FactID, 0, 0, 1, GETDATE(), GETDATE());
                """,
                (profile_id, self.current_fact_id)
            )
        else:
            # Unmarking as known: leave KnownSince unchanged for historical tracking
            success = self.execute_update(
                """
                MERGE ProfileFacts AS target
                USING (SELECT ? AS ProfileID, ? AS FactID) AS src
                ON target.ProfileID = src.ProfileID AND target.FactID = src.FactID
                WHEN MATCHED THEN
                    UPDATE SET IsEasy = 0, LastViewedByUser = COALESCE(target.LastViewedByUser, GETDATE())
                WHEN NOT MATCHED THEN
                    INSERT (ProfileID, FactID, PersonalReviewCount, IsFavorite, IsEasy, LastViewedByUser)
                    VALUES (src.ProfileID, src.FactID, 0, 0, 0, GETDATE());
                """,
                (profile_id, self.current_fact_id)
            )
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
            # Gamification: award when marking known, unlock using current known count
            try:
                if new_status and getattr(self, 'gamify', None):
                    # Increment lifetime counter
                    _ = self.gamify.increment_counter('TotalKnown', 1)
                    # Compute current known facts from Facts
                    try:
                        rows = self.fetch_query("SELECT COUNT(*) FROM ProfileFacts WHERE ProfileID = ? AND IsEasy = 1", (profile_id,))
                        current_known_count = int(rows[0][0]) if rows else 0
                    except Exception:
                        current_known_count = 0
                    unlocked = self.gamify.unlock_achievements_if_needed('known', current_known_count)
                    known_xp = int(config.XP_CONFIG.get('xp_known', 10))
                    if known_xp:
                        self.gamify.award_xp(known_xp)
                    if unlocked:
                        self.status_label.config(text=f"Achievement: {unlocked[-1]['Name']} (+{unlocked[-1]['RewardXP']} XP)", fg=self.GREEN_COLOR)
                        self.clear_status_after_delay(2500)
                        try:
                            self.gamify.mark_unlocked_notified_by_codes([u.get('Code') for u in unlocked if u.get('Code')])
                        except Exception:
                            pass
                    self.update_level_progress()
            except Exception:
                pass
    
    def add_new_fact(self):
        """Add a new fact to the database"""
        # Pause review timer while user is adding a card
        self.pause_review_timer()
        # Create a popup window
        add_window = tk.Toplevel(self.root)
        add_window.title("Add New Fact")
        add_window.geometry(f"{self.POPUP_ADD_CARD_SIZE}{self.POPUP_POSITION}")
        add_window.configure(bg=self.BG_COLOR)
        profile_id = self.get_active_profile_id()
        
        # On close, resume timer then destroy
        def on_close_add():
            try:
                self.resume_review_timer()
            except Exception:
                pass
            add_window.destroy()
        add_window.protocol("WM_DELETE_WINDOW", on_close_add)

        # Get categories for dropdown
        categories = self.fetch_query(
            "SELECT CategoryName FROM Categories WHERE IsActive = 1 AND CreatedBy = ?",
            (profile_id,)
        )
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
        
        def save_fact(close_after=True):
            category = cat_var.get()
            content = content_text.get("1.0", "end-1c").strip()
            profile_id = self.get_active_profile_id()

            if not content:
                self.status_label.config(text="Fact content is required!", fg=self.RED_COLOR)
                self.clear_status_after_delay(3000)
                return
            
            # Get category ID
            cat_result = self.fetch_query(
                "SELECT CategoryID FROM Categories WHERE CategoryName = ? AND CreatedBy = ?",
                (category, profile_id)
            )
            if not cat_result or len(cat_result) == 0:
                self.status_label.config(text="Category not found!", fg=self.RED_COLOR)
                self.clear_status_after_delay(3000)
                return
                
            category_id = cat_result[0][0]
            
            # Duplicate check using the same normalization as ContentKey
            try:
                dup = self.fetch_query(
                    """
                    SELECT TOP 1 FactID
                    FROM dbo.Facts
                    WHERE ContentKey = CAST(LOWER(LTRIM(RTRIM(REPLACE(REPLACE(REPLACE(?, CHAR(13), ' '), CHAR(10), ' '), CHAR(9), ' ')))) AS NVARCHAR(450))
                      AND CreatedBy = ?
                    """,
                    (content, profile_id)
                )
            except Exception:
                dup = []
            if dup:
                self.status_label.config(text="Fact Already Exists!", fg=self.RED_COLOR)
                self.clear_status_after_delay(3000)
                return

            # Insert the new fact and get its ID
            new_fact_id = self.execute_insert_return_id(
                """
                INSERT INTO Facts (CategoryID, Content, DateAdded, TotalViews, CreatedBy)
                OUTPUT INSERTED.FactID
                VALUES (?, ?, GETDATE(), 0, ?)
                """,
                (category_id, content, profile_id)
            )
            
            if new_fact_id:
                # Initialize per-profile state for the active profile
                try:
                    pid = self.get_active_profile_id()
                    self.execute_update(
                        """
                        MERGE ProfileFacts AS target
                        USING (SELECT ? AS ProfileID, ? AS FactID) AS src
                        ON target.ProfileID = src.ProfileID AND target.FactID = src.FactID
                        WHEN NOT MATCHED THEN
                            INSERT (ProfileID, FactID, PersonalReviewCount, IsFavorite, IsEasy, LastViewedByUser)
                            VALUES (src.ProfileID, src.FactID, 0, 0, 0, NULL);
                        """,
                        (pid, new_fact_id)
                    )
                except Exception:
                    pass
                self.status_label.config(text="New fact added successfully!", fg=self.GREEN_COLOR)
                self.clear_status_after_delay(3000)
                self.update_fact_count()
                # Log the add action in current session (if any)
                try:
                    if self.current_session_id:
                        self.execute_update(
                            """
                            UPDATE ReviewSessions SET FactsAdded = ISNULL(FactsAdded,0) + 1 WHERE SessionID = ?
                            """,
                            (self.current_session_id,)
                        )
                        self.execute_update(
                            """
                            INSERT INTO ReviewLogs (FactID, ReviewDate, SessionID, SessionDuration, Action, FactContentSnapshot, CategoryIDSnapshot)
                            VALUES (?, GETDATE(), ?, 0, 'add', ?, ?)
                            """,
                            (new_fact_id, self.current_session_id, content, category_id)
                        )
                except Exception:
                    pass
                # Gamification: count add
                try:
                    if getattr(self, 'gamify', None):
                        total = self.gamify.increment_counter('TotalAdds', 1)
                        unlocked = self.gamify.unlock_achievements_if_needed('adds', total)
                        add_xp = int(config.XP_CONFIG.get('xp_add', 2))
                        if add_xp:
                            self.gamify.award_xp(add_xp)
                        if unlocked:
                            self.status_label.config(text=f"Achievement: {unlocked[-1]['Name']} (+{unlocked[-1]['RewardXP']} XP)", fg=self.GREEN_COLOR)
                            self.clear_status_after_delay(2500)
                            try:
                                self.gamify.mark_unlocked_notified_by_codes([u.get('Code') for u in unlocked if u.get('Code')])
                            except Exception:
                                pass
                        self.update_level_progress()
                except Exception:
                    pass
                # Do not reshuffle or navigate. Stay on current card.
                # Counts and analytics are updated separately via update_fact_count().

                # Either close or reset for adding another
                if close_after:
                    # Resume timer on close
                    try:
                        self.resume_review_timer()
                    except Exception:
                        pass
                    add_window.destroy()
                else:
                    # Keep window open: clear text and focus for next entry
                    content_text.delete('1.0', tk.END)
                    try:
                        content_text.focus_set()
                    except Exception:
                        pass
            else:
                self.status_label.config(text="Error adding new fact!", fg=self.RED_COLOR)
                self.clear_status_after_delay(3000)
        
        # Buttons row
        btn_row = tk.Frame(add_window, bg=self.BG_COLOR)
        btn_row.pack(pady=20)
        save_close_btn = tk.Button(btn_row, text="Save & Close", bg=self.GREEN_COLOR, fg=self.TEXT_COLOR,
                                    command=lambda: save_fact(True), cursor="hand2", borderwidth=0,
                                    highlightthickness=0, padx=10, pady=5,
                                    font=(self.NORMAL_FONT[0], self.NORMAL_FONT[1], 'bold'))
        save_close_btn.pack(side='left', padx=6)
        add_another_btn = tk.Button(btn_row, text="Save & Add Another", bg=self.BLUE_COLOR, fg=self.TEXT_COLOR,
                                    command=lambda: save_fact(False), cursor="hand2", borderwidth=0,
                                    highlightthickness=0, padx=10, pady=5,
                                    font=(self.NORMAL_FONT[0], self.NORMAL_FONT[1], 'bold'))
        add_another_btn.pack(side='left', padx=6)
    
    def edit_current_fact(self):
        """Edit the current fact"""
        if not self.current_fact_id:
            return
        profile_id = self.get_active_profile_id()
        
        # Pause timer while editing
        self.pause_review_timer()

        # Get current fact data
        query = """
        SELECT f.Content, c.CategoryName
        FROM Facts f
        JOIN Categories c ON f.CategoryID = c.CategoryID
        WHERE f.FactID = ? AND f.CreatedBy = ? AND c.CreatedBy = ?
        """
        result = self.fetch_query(query, (self.current_fact_id, profile_id, profile_id))
        
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

        # Resume timer when window is closed via [X]
        def on_close_edit():
            try:
                self.resume_review_timer()
            except Exception:
                pass
            edit_window.destroy()
        edit_window.protocol("WM_DELETE_WINDOW", on_close_edit)
        
        # Get categories for dropdown
        categories = self.fetch_query(
            "SELECT CategoryName FROM Categories WHERE IsActive = 1 AND CreatedBy = ?",
            (profile_id,)
        )
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
            cat_result = self.fetch_query(
                "SELECT CategoryID FROM Categories WHERE CategoryName = ? AND CreatedBy = ?",
                (category, profile_id)
            )
            if not cat_result or len(cat_result) == 0:
                self.status_label.config(text="Category not found!", fg=self.RED_COLOR)
                self.clear_status_after_delay(3000)
                return
                
            category_id = cat_result[0][0]
            
            # Prevent duplicates: check against computed ContentKey, ignoring this FactID
            try:
                dup = self.fetch_query(
                    """
                    SELECT TOP 1 FactID
                    FROM dbo.Facts
                    WHERE ContentKey = CAST(LOWER(LTRIM(RTRIM(REPLACE(REPLACE(REPLACE(?, CHAR(13), ' '), CHAR(10), ' '), CHAR(9), ' ')))) AS NVARCHAR(450))
                      AND FactID <> ?
                      AND CreatedBy = ?
                    """,
                    (content, self.current_fact_id, profile_id)
                )
            except Exception:
                dup = []
            if dup:
                self.status_label.config(text="Another fact with identical content already exists!", fg=self.RED_COLOR)
                self.clear_status_after_delay(3000)
                return

            # Update the fact
            success = self.execute_update(
                """
                UPDATE Facts
                SET CategoryID = ?, Content = ?
                WHERE FactID = ? AND CreatedBy = ?
                """,
                (category_id, content, self.current_fact_id, profile_id)
            )
            
            if success:
                # Resume timer upon closing edit
                try:
                    self.resume_review_timer()
                except Exception:
                    pass
                edit_window.destroy()
                self.status_label.config(text="Fact updated successfully!", fg=self.GREEN_COLOR)
                self.clear_status_after_delay(3000)
                # Log the edit action in current session (if any)
                try:
                    if self.current_session_id:
                        self.execute_update(
                            "UPDATE ReviewSessions SET FactsEdited = ISNULL(FactsEdited,0) + 1 WHERE SessionID = ?",
                            (self.current_session_id,)
                        )
                        self.execute_update(
                            """
                            INSERT INTO ReviewLogs (FactID, ReviewDate, SessionID, SessionDuration, Action, FactEdited, FactContentSnapshot, CategoryIDSnapshot)
                            VALUES (?, GETDATE(), ?, 0, 'edit', 1, ?, ?)
                            """,
                            (self.current_fact_id, self.current_session_id, content, category_id)
                        )
                except Exception:
                    pass
                # Gamification: count edit
                try:
                    if getattr(self, 'gamify', None):
                        total = self.gamify.increment_counter('TotalEdits', 1)
                        unlocked = self.gamify.unlock_achievements_if_needed('edits', total)
                        edit_xp = int(config.XP_CONFIG.get('xp_edit', 1))
                        if edit_xp:
                            self.gamify.award_xp(edit_xp)
                        if unlocked:
                            self.status_label.config(text=f"Achievement: {unlocked[-1]['Name']} (+{unlocked[-1]['RewardXP']} XP)", fg=self.GREEN_COLOR)
                            self.clear_status_after_delay(2500)
                            try:
                                self.gamify.mark_unlocked_notified_by_codes([u.get('Code') for u in unlocked if u.get('Code')])
                            except Exception:
                                pass
                        self.update_level_progress()
                except Exception:
                    pass
                
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
        profile_id = self.get_active_profile_id()
        
        # Pause during confirmation and deletion flow
        self.pause_review_timer()
        try:
            # Ask for confirmation
            if self.confirm_dialog("Confirm Delete", "Are you sure you want to delete this fact?"):
                # Capture snapshot before delete
                try:
                    row = self.fetch_query(
                        "SELECT Content, CategoryID FROM Facts WHERE FactID = ? AND CreatedBy = ?",
                        (self.current_fact_id, profile_id)
                    )
                    content_snapshot = row[0][0] if row else None
                    category_snapshot = row[0][1] if row else None
                except Exception:
                    content_snapshot = None
                    category_snapshot = None

                # Log the delete action in ReviewLogs (before deleting the Fact)
                try:
                    if self.current_session_id:
                        self.execute_update(
                            """
                            INSERT INTO ReviewLogs (FactID, ReviewDate, SessionID, SessionDuration, Action, FactDeleted, FactContentSnapshot, CategoryIDSnapshot)
                            VALUES (?, GETDATE(), ?, 0, 'delete', 1, ?, ?)
                            """,
                            (self.current_fact_id, self.current_session_id, content_snapshot, category_snapshot)
                        )
                        # Increment session counter
                        self.execute_update(
                            "UPDATE ReviewSessions SET FactsDeleted = ISNULL(FactsDeleted,0) + 1 WHERE SessionID = ?",
                            (self.current_session_id,)
                        )
                except Exception:
                    pass

                # Delete the fact
                success = self.execute_update(
                    "DELETE FROM Facts WHERE FactID = ? AND CreatedBy = ?",
                    (self.current_fact_id, profile_id)
                )
                if success:
                    self.status_label.config(text="Fact deleted!", fg=self.RED_COLOR)
                    self.clear_status_after_delay(3000)
                    self.update_fact_count()
                    # Gamification: count delete
                    try:
                        if getattr(self, 'gamify', None):
                            total = self.gamify.increment_counter('TotalDeletes', 1)
                            unlocked = self.gamify.unlock_achievements_if_needed('deletes', total)
                            del_xp = int(config.XP_CONFIG.get('xp_delete', 0))
                            if del_xp:
                                self.gamify.award_xp(del_xp)
                            if unlocked:
                                self.status_label.config(text=f"Achievement: {unlocked[-1]['Name']} (+{unlocked[-1]['RewardXP']} XP)", fg=self.GREEN_COLOR)
                                self.clear_status_after_delay(2500)
                                try:
                                    self.gamify.mark_unlocked_notified_by_codes([u.get('Code') for u in unlocked if u.get('Code')])
                                except Exception:
                                    pass
                            self.update_level_progress()
                    except Exception:
                        pass
                    
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
        finally:
            # Always resume after delete flow
            self.resume_review_timer()
    def _award_for_elapsed(self, elapsed_seconds: int):
        """Award XP and review counters for a completed view."""
        if not getattr(self, 'gamify', None):
            return
        # Only count reviews after grace period
        try:
            grace = int(config.XP_CONFIG.get('review_grace_seconds', 2))
        except Exception:
            grace = 2
        if elapsed_seconds < grace:
            return
        # Base XP + time bonus
        base_xp = int(config.XP_CONFIG.get('review_base_xp', 1))
        step = max(1, int(config.XP_CONFIG.get('review_bonus_step_seconds', 5)))
        cap = int(config.XP_CONFIG.get('review_bonus_cap', 5))
        extra = (max(0, elapsed_seconds - grace)) // step
        xp = base_xp + min(cap, int(extra))
        total = self.gamify.increment_counter('TotalReviews', 1)
        unlocked = self.gamify.unlock_achievements_if_needed('reviews', total)
        self.gamify.award_xp(int(xp))
        if unlocked:
            try:
                self.status_label.config(text=f"Achievement: {unlocked[-1]['Name']} (+{unlocked[-1]['RewardXP']} XP)", fg=self.GREEN_COLOR)
                self.clear_status_after_delay(2500)
            except Exception:
                pass
            try:
                self.gamify.mark_unlocked_notified_by_codes([u.get('Code') for u in unlocked if u.get('Code')])
            except Exception:
                pass
        self.update_level_progress()
    
    def manage_categories(self):
        """Open a window to manage categories"""
        try:
            self.pause_review_timer()
        except Exception:
            pass
        # Create the category management window
        cat_window = self._create_category_window()

        def on_close():
            try:
                self.resume_review_timer()
            except Exception:
                pass
            cat_window.destroy()

        cat_window.protocol("WM_DELETE_WINDOW", on_close)
        
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
        profile_id = self.get_active_profile_id()

        # Check if category already exists
        existing = self.fetch_query(
            "SELECT COUNT(*) FROM Categories WHERE CategoryName = ? AND CreatedBy = ?",
            (new_cat, profile_id)
        )
        if existing and existing[0][0] > 0:
            tk.messagebox.showinfo("Error", f"Category '{new_cat}' already exists!")
            return

        # Add the new category
        success = self.execute_update(
            "INSERT INTO Categories (CategoryName, Description, CreatedBy) VALUES (?, '', ?)",
            (new_cat, profile_id)
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
            pid = self.get_active_profile_id()
            categories = self.fetch_query(
                "SELECT CategoryName, CategoryID FROM Categories WHERE CreatedBy = ? ORDER BY CategoryName",
                (pid,)
            )
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
    
    def _rename_category(self, cat_listbox, refresh_callback):
        """Handle renaming a category"""
        selection = cat_listbox.curselection()
        if not selection:
            return
        profile_id = self.get_active_profile_id()
        
        # Extract category ID from selection text
        cat_text = cat_listbox.get(selection[0])
        cat_id = int(cat_text.split("ID: ")[1].rstrip(")"))
        
        # Get current name
        cat_result = self.fetch_query(
            "SELECT CategoryName FROM Categories WHERE CategoryID = ? AND CreatedBy = ?",
            (cat_id, profile_id)
        )
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
            "SELECT COUNT(*) FROM Categories WHERE CategoryName = ? AND CategoryID != ? AND CreatedBy = ?",
            (new_name, cat_id, profile_id)
        )
        
        if existing and existing[0][0] > 0:
            tk.messagebox.showinfo("Error", f"Category '{new_name}' already exists!")
            return
        
        # Update the category
        success = self.execute_update(
            "UPDATE Categories SET CategoryName = ? WHERE CategoryID = ? AND CreatedBy = ?",
            (new_name, cat_id, profile_id)
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
        profile_id = self.get_active_profile_id()
        
        # Extract category ID from selection text
        cat_text = cat_listbox.get(selection[0])
        cat_id = int(cat_text.split("ID: ")[1].rstrip(")"))
        cat_name = cat_text.split(" (ID:")[0]
        
        # Check if category has facts
        fact_count_result = self.fetch_query(
            "SELECT COUNT(*) FROM Facts WHERE CategoryID = ? AND CreatedBy = ?",
            (cat_id, profile_id)
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

            DELETE FROM Facts WHERE CategoryID = ? AND CreatedBy = ?;
            DELETE FROM Categories WHERE CategoryID = ? AND CreatedBy = ?;

            COMMIT TRANSACTION;
        """, (cat_id, profile_id, cat_id, profile_id))
        
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
    
    def on_category_dropdown_open(self, event=None):
        """Pause timing while the category dropdown is open."""
        try:
            self.pause_review_timer()
            self.category_dropdown_open = True
            self._dropdown_seen_open = False
            # Start polling after a tiny delay to let the popdown map
            self.root.after(100, self._poll_category_dropdown_close)
        except Exception:
            pass

    def on_category_dropdown_selected(self, event=None):
        """Resume timing once a category is chosen, then handle the change."""
        try:
            self.category_dropdown_open = False
            self.resume_review_timer()
        except Exception:
            pass
        self.on_category_change(event)

    def _poll_category_dropdown_close(self):
        """Detect when the dropdown popdown window closes to resume timing."""
        try:
            if not getattr(self, "category_dropdown_open", False):
                return
            popdown = self.category_dropdown.tk.call("ttk::combobox::PopdownWindow", self.category_dropdown)
            is_open = bool(int(self.category_dropdown.tk.call("winfo", "ismapped", popdown)))
            if is_open:
                self._dropdown_seen_open = True
                # Keep polling until it closes
                self.root.after(120, self._poll_category_dropdown_close)
                return
            # Not open right now
            if self._dropdown_seen_open:
                # Was open and now closed -> resume
                self.category_dropdown_open = False
                try:
                    self.resume_review_timer()
                except Exception:
                    pass
                return
            # Haven't seen it open yet; keep polling briefly
            self.root.after(120, self._poll_category_dropdown_close)
        except Exception:
            # If detection fails, keep polling a bit instead of resuming immediately
            try:
                if getattr(self, "category_dropdown_open", False):
                    self.root.after(150, self._poll_category_dropdown_close)
            except Exception:
                pass
        # Still open; poll again shortly
        try:
            self.root.after(150, self._poll_category_dropdown_close)
        except Exception:
            pass

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
            try:
                self.ai_button.place_forget()
            except Exception:
                pass
            # Hide level label on home page
            try:
                self.level_label.place_forget()
            except Exception:
                pass
            self.info_button.place(relx=1.0, rely=0, anchor="ne", x=-55, y=5)
            # Hide speaker on home page
            self.speaker_button.place_forget()
        except Exception:
            pass

        # Show brand header centered horizontally near the top
        try:
            self.brand_frame.place(relx=0.5, rely=0.3, anchor='center')
        except Exception:
            try:
                self.brand_frame.pack(side='top', pady=(10, 0))
            except Exception:
                pass
        # Hide the large fact label on Home to avoid overlaying the brand header
        try:
            self.fact_label.pack_forget()
        except Exception:
            pass
        
        # Show the slogan centered under the brand (optional)
        self.slogan_label.config(text="Review and remember facts effortlessly")
        try:
            # Move a bit further down from the header
            self.slogan_label.place(relx=0.5, rely=0.55, anchor='center')
        except Exception:
            self.slogan_label.pack(side="top", pady=5)
        
        # Show the start reviewing button centered
        try:
            # Move a bit further down to create spacing
            self.start_button.place(relx=0.5, rely=0.72, anchor='center')
        except Exception:
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
        try:
            self.slogan_label.place_forget()
        except Exception:
            try:
                self.slogan_label.pack_forget()
            except Exception:
                pass
        try:
            self.start_button.place_forget()
        except Exception:
            try:
                self.start_button.pack_forget()
            except Exception:
                pass
        
        # Show all fact-related UI elements
        self.category_frame.pack(side="right", padx=5, pady=3)
        self.nav_frame.pack(side="top", fill="x", pady=10)
        self.icon_buttons_frame.pack(side="top", fill="x", pady=5)
        self.stats_frame.pack(side="bottom", fill="x", padx=10, pady=3)
        # Hide brand header when reviewing
        try:
            self.brand_frame.pack_forget()
        except Exception:
            pass

        # Swap back: hide info, show star icon
        try:
            self.info_button.place_forget()
            # Show easy button before star
            self.ai_button.place(relx=1.0, rely=0, anchor="ne", x=-105, y=5)
            self.easy_button.place(relx=1.0, rely=0, anchor="ne", x=-80, y=5)
            self.star_button.place(relx=1.0, rely=0, anchor="ne", x=-55, y=5)
            # Show speaker on reviewing page
            self.speaker_button.place(relx=1.0, rely=0, anchor="ne", x=-5, y=5)
            # Show level label next to Home icon while reviewing
            self.level_label.place(x=32, y=7)
            # Hide brand header when reviewing
            try:
                self.brand_frame.place_forget()
            except Exception:
                try:
                    self.brand_frame.pack_forget()
                except Exception:
                    pass
        except Exception:
            pass
        
        # Load facts and display the first one
        self.load_all_facts()
        # Re-pack the fact label for reviewing view
        try:
            self.fact_label.pack(side="top", fill="both", expand=True, padx=10, pady=10)
        except Exception:
            pass
        if self.all_facts:
            self.display_current_fact()
        else:
            self.fact_label.config(text="No facts found. Add some facts first!")
        
        # Show shortcut hints
        self.status_label.config(text="Shortcuts: <- Previous, -> Next, Space Next", fg=self.STATUS_COLOR)

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
