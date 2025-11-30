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
        query = "SELECT DISTINCT CategoryName FROM Categories WHERE IsActive = 1 ORDER BY CategoryName"
        categories = self.fetch_query(query)
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
            ToolTip(self.ai_button, "AI explain fact")
            ToolTip(self.graph_button, "Analytics (g)")
            ToolTip(self.info_button, "Show shortcuts")
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

    def show_achievements_window(self):
        """Display achievements, status, and progress."""
        if not getattr(self, 'gamify', None):
            try:
                self.status_label.config(text="Gamification unavailable", fg=self.STATUS_COLOR)
                self.clear_status_after_delay(2000)
            except Exception:
                pass
            return
        win = tk.Toplevel(self.root)
        win.title("Achievements")
        try:
            win.geometry(f"{self.POPUP_ACHIEVEMENTS_SIZE}{self.POPUP_POSITION}")
        except Exception:
            win.geometry(self.POPUP_ACHIEVEMENTS_SIZE)
        win.configure(bg=self.BG_COLOR)

        header = tk.Label(win, text="Achievements", fg=self.TEXT_COLOR, bg=self.BG_COLOR, font=self.TITLE_FONT)
        header.pack(pady=(10, 4))
        sub = tk.Label(win, text="Click a column to resize. New (unseen) unlocks show green.", fg=self.STATUS_COLOR, bg=self.BG_COLOR, font=self.SMALL_FONT)
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
        for row in data:
            unlocked = row.get('Unlocked')
            notified = bool(row.get('Notified'))
            name = row.get('Name')
            category = row.get('Category')
            threshold = int(row.get('Threshold', 0))
            reward = int(row.get('RewardXP', 0))
            progress = int(row.get('ProgressCurrent', 0))
            status_text = "Unlocked" if unlocked else "Locked"
            prog_text = f"{min(progress, threshold)}/{threshold}"
            vals = (status_text, name, category, prog_text, f"{reward} XP")
            iid = tree.insert('', 'end', values=vals)
            # Color only new (unseen) unlocks
            try:
                if unlocked and not notified:
                    tree.item(iid, tags=('new_unlock',))
            except Exception:
                pass
        try:
            tree.tag_configure('new_unlock', foreground=self.GREEN_COLOR)
        except Exception:
            pass

        # Buttons
        btns = tk.Frame(win, bg=self.BG_COLOR)
        btns.pack(pady=(0, 10))

        def mark_seen():
            try:
                self.gamify.mark_all_unnotified_as_notified()
                self.status_label.config(text="Marked new unlocks as seen", fg=self.STATUS_COLOR)
                self.clear_status_after_delay(2000)
            except Exception:
                pass

        tk.Button(btns, text="Mark New Unlocks Seen", command=mark_seen,
                  bg=self.BLUE_COLOR, fg=self.TEXT_COLOR, cursor="hand2", borderwidth=0, highlightthickness=0, padx=10, pady=5).pack(side='left', padx=6)
        tk.Button(btns, text="Close", command=win.destroy,
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
        """Create missing tables/columns for sessions and per-view durations."""
        ddl = """
        /* Create GamificationProfile if missing (user identity) */
        IF OBJECT_ID('dbo.GamificationProfile','U') IS NULL
        BEGIN
            CREATE TABLE dbo.GamificationProfile (
                ProfileID INT IDENTITY(1,1) PRIMARY KEY,
                XP INT NOT NULL CONSTRAINT DF_GamificationProfile_XP DEFAULT 0,
                Level INT NOT NULL CONSTRAINT DF_GamificationProfile_Level DEFAULT 1,
                TotalReviews INT NOT NULL CONSTRAINT DF_GamificationProfile_TotalReviews DEFAULT 0,
                TotalKnown INT NOT NULL CONSTRAINT DF_GamificationProfile_TotalKnown DEFAULT 0,
                TotalFavorites INT NOT NULL CONSTRAINT DF_GamificationProfile_TotalFavorites DEFAULT 0,
                TotalAdds INT NOT NULL CONSTRAINT DF_GamificationProfile_TotalAdds DEFAULT 0,
                TotalEdits INT NOT NULL CONSTRAINT DF_GamificationProfile_TotalEdits DEFAULT 0,
                TotalDeletes INT NOT NULL CONSTRAINT DF_GamificationProfile_TotalDeletes DEFAULT 0,
                TotalAITokens INT NOT NULL CONSTRAINT DF_GamificationProfile_TotalAITokens DEFAULT 0,
                TotalAICost DECIMAL(19,9) NOT NULL CONSTRAINT DF_GamificationProfile_TotalAICost DEFAULT 0,
                CurrentStreak INT NOT NULL CONSTRAINT DF_GamificationProfile_CurrentStreak DEFAULT 0,
                LongestStreak INT NOT NULL CONSTRAINT DF_GamificationProfile_LongestStreak DEFAULT 0,
                LastCheckinDate DATE NULL
            );
        END;

        /* Backfill AI totals on existing GamificationProfile tables */
        IF COL_LENGTH('dbo.GamificationProfile','TotalAITokens') IS NULL
        BEGIN
            ALTER TABLE dbo.GamificationProfile ADD TotalAITokens INT NOT NULL CONSTRAINT DF_GamificationProfile_TotalAITokens DEFAULT 0;
        END;
        IF COL_LENGTH('dbo.GamificationProfile','TotalAICost') IS NULL
        BEGIN
            ALTER TABLE dbo.GamificationProfile ADD TotalAICost DECIMAL(19,9) NOT NULL CONSTRAINT DF_GamificationProfile_TotalAICost DEFAULT 0;
        END;

        /* ProfileFacts: per-profile state for facts (favorites, difficulty, personal counts) */
        IF OBJECT_ID('dbo.ProfileFacts','U') IS NULL
        BEGIN
            CREATE TABLE dbo.ProfileFacts (
                ProfileFactID INT IDENTITY(1,1) PRIMARY KEY,
                ProfileID INT NOT NULL
                    CONSTRAINT FK_ProfileFacts_Profile
                    REFERENCES dbo.GamificationProfile(ProfileID),
                FactID INT NOT NULL
                    CONSTRAINT FK_ProfileFacts_Fact
                    REFERENCES dbo.Facts(FactID) ON DELETE CASCADE,
                PersonalReviewCount INT NOT NULL CONSTRAINT DF_ProfileFacts_PersonalReviewCount DEFAULT 0,
                IsFavorite BIT NOT NULL CONSTRAINT DF_ProfileFacts_IsFavorite DEFAULT 0,
                IsEasy BIT NOT NULL CONSTRAINT DF_ProfileFacts_IsEasy DEFAULT 0,
                LastViewedByUser DATETIME NULL,
                CONSTRAINT UX_ProfileFacts_Profile_Fact UNIQUE (ProfileID, FactID)
            );
            CREATE INDEX IX_ProfileFacts_ProfileID ON dbo.ProfileFacts(ProfileID);
            CREATE INDEX IX_ProfileFacts_FactID ON dbo.ProfileFacts(FactID);
        END;
        ELSE
        BEGIN
            IF COL_LENGTH('dbo.ProfileFacts','PersonalReviewCount') IS NULL
            BEGIN
                ALTER TABLE dbo.ProfileFacts ADD PersonalReviewCount INT NOT NULL CONSTRAINT DF_ProfileFacts_PersonalReviewCount DEFAULT 0;
            END;
            IF COL_LENGTH('dbo.ProfileFacts','IsFavorite') IS NULL
            BEGIN
                ALTER TABLE dbo.ProfileFacts ADD IsFavorite BIT NOT NULL CONSTRAINT DF_ProfileFacts_IsFavorite DEFAULT 0;
            END;
            IF COL_LENGTH('dbo.ProfileFacts','IsEasy') IS NULL
            BEGIN
                ALTER TABLE dbo.ProfileFacts ADD IsEasy BIT NOT NULL CONSTRAINT DF_ProfileFacts_IsEasy DEFAULT 0;
            END;
            IF COL_LENGTH('dbo.ProfileFacts','LastViewedByUser') IS NULL
            BEGIN
                ALTER TABLE dbo.ProfileFacts ADD LastViewedByUser DATETIME NULL;
            END;
            IF OBJECT_ID('dbo.UX_ProfileFacts_Profile_Fact','UQ') IS NULL
               AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UX_ProfileFacts_Profile_Fact' AND object_id = OBJECT_ID('dbo.ProfileFacts'))
            BEGIN
                ALTER TABLE dbo.ProfileFacts
                ADD CONSTRAINT UX_ProfileFacts_Profile_Fact UNIQUE (ProfileID, FactID);
            END;
            IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_ProfileFacts_ProfileID' AND object_id = OBJECT_ID('dbo.ProfileFacts'))
            BEGIN
                CREATE INDEX IX_ProfileFacts_ProfileID ON dbo.ProfileFacts(ProfileID);
            END;
            IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_ProfileFacts_FactID' AND object_id = OBJECT_ID('dbo.ProfileFacts'))
            BEGIN
                CREATE INDEX IX_ProfileFacts_FactID ON dbo.ProfileFacts(FactID);
            END;
        END;

        /* Backfill ProfileFacts for default profile using any existing global columns */
        IF NOT EXISTS (SELECT 1 FROM dbo.ProfileFacts WHERE ProfileID = 1)
        BEGIN
            DECLARE @hasFav BIT = CASE WHEN COL_LENGTH('dbo.Facts','IsFavorite') IS NOT NULL THEN 1 ELSE 0 END;
            DECLARE @hasEasy BIT = CASE WHEN COL_LENGTH('dbo.Facts','IsEasy') IS NOT NULL THEN 1 ELSE 0 END;
            DECLARE @merge_sql NVARCHAR(MAX) = '
                MERGE dbo.ProfileFacts AS target
                USING (
                    SELECT
                        1 AS ProfileID,
                        f.FactID,
                        0 AS PersonalReviewCount,
                        ' + CASE WHEN @hasFav = 1 THEN 'ISNULL(f.IsFavorite,0)' ELSE 'CAST(0 AS BIT)' END + ' AS IsFavorite,
                        ' + CASE WHEN @hasEasy = 1 THEN 'ISNULL(f.IsEasy,0)' ELSE 'CAST(0 AS BIT)' END + ' AS IsEasy,
                        NULL AS LastViewedByUser
                    FROM dbo.Facts f
                ) AS src
                ON target.ProfileID = src.ProfileID AND target.FactID = src.FactID
                WHEN NOT MATCHED THEN
                    INSERT (ProfileID, FactID, PersonalReviewCount, IsFavorite, IsEasy, LastViewedByUser)
                    VALUES (src.ProfileID, src.FactID, src.PersonalReviewCount, src.IsFavorite, src.IsEasy, src.LastViewedByUser);';
            EXEC(@merge_sql);
        END;

        /* Drop obsolete ReviewCount column from Facts (now tracked per-profile + TotalViews) */
        IF COL_LENGTH('dbo.Facts','ReviewCount') IS NOT NULL
        BEGIN
            DECLARE @df NVARCHAR(128);
            SELECT @df = dc.name
            FROM sys.default_constraints dc
            JOIN sys.columns c ON c.column_id = dc.parent_column_id AND c.object_id = dc.parent_object_id
            WHERE dc.parent_object_id = OBJECT_ID('dbo.Facts') AND c.name = 'ReviewCount';
            IF @df IS NOT NULL 
            BEGIN
                DECLARE @cmd_drop_df NVARCHAR(400);
                SET @cmd_drop_df = 'ALTER TABLE dbo.Facts DROP CONSTRAINT ' + QUOTENAME(@df);
                EXEC(@cmd_drop_df);
            END;
            ALTER TABLE dbo.Facts DROP COLUMN ReviewCount;
        END;
        /* Drop obsolete LastViewedDate column from Facts (now per-profile in ProfileFacts) */
        IF COL_LENGTH('dbo.Facts','LastViewedDate') IS NOT NULL
        BEGIN
            DECLARE @df2 NVARCHAR(128);
            SELECT @df2 = dc.name
            FROM sys.default_constraints dc
            JOIN sys.columns c ON c.column_id = dc.parent_column_id AND c.object_id = dc.parent_object_id
            WHERE dc.parent_object_id = OBJECT_ID('dbo.Facts') AND c.name = 'LastViewedDate';
            IF @df2 IS NOT NULL 
            BEGIN
                DECLARE @cmd_drop_df2 NVARCHAR(400);
                SET @cmd_drop_df2 = 'ALTER TABLE dbo.Facts DROP CONSTRAINT ' + QUOTENAME(@df2);
                EXEC(@cmd_drop_df2);
            END;
            ALTER TABLE dbo.Facts DROP COLUMN LastViewedDate;
        END;

        /* Ensure CreatedBy columns on Categories and Facts (default profile 1) */
        IF COL_LENGTH('dbo.Categories','CreatedBy') IS NULL
        BEGIN
            ALTER TABLE dbo.Categories ADD CreatedBy INT NOT NULL CONSTRAINT DF_Categories_CreatedBy DEFAULT 1;
            UPDATE dbo.Categories SET CreatedBy = 1 WHERE CreatedBy IS NULL;
            ALTER TABLE dbo.Categories
            ADD CONSTRAINT FK_Categories_CreatedBy FOREIGN KEY (CreatedBy) REFERENCES dbo.GamificationProfile(ProfileID);
        END;
        IF COL_LENGTH('dbo.Facts','CreatedBy') IS NULL
        BEGIN
            ALTER TABLE dbo.Facts ADD CreatedBy INT NOT NULL CONSTRAINT DF_Facts_CreatedBy DEFAULT 1;
            UPDATE dbo.Facts SET CreatedBy = 1 WHERE CreatedBy IS NULL;
            ALTER TABLE dbo.Facts
            ADD CONSTRAINT FK_Facts_CreatedBy FOREIGN KEY (CreatedBy) REFERENCES dbo.GamificationProfile(ProfileID);
        END;

        /* Create ReviewSessions if missing */
        IF OBJECT_ID('dbo.ReviewSessions','U') IS NULL
        BEGIN
            CREATE TABLE dbo.ReviewSessions (
                SessionID INT IDENTITY(1,1) PRIMARY KEY,
                ProfileID INT NOT NULL CONSTRAINT DF_ReviewSessions_ProfileID DEFAULT 1,
                StartTime DATETIME NOT NULL,
                EndTime DATETIME NULL,
                DurationSeconds INT NULL,
                TimedOut BIT NOT NULL CONSTRAINT DF_ReviewSessions_TimedOut DEFAULT 0,
                FactsAdded INT NOT NULL CONSTRAINT DF_ReviewSessions_FactsAdded DEFAULT 0,
                FactsEdited INT NOT NULL CONSTRAINT DF_ReviewSessions_FactsEdited DEFAULT 0,
                FactsDeleted INT NOT NULL CONSTRAINT DF_ReviewSessions_FactsDeleted DEFAULT 0
            );
        END;

        /* Ensure ReviewLogs table exists */
        IF OBJECT_ID('dbo.ReviewLogs','U') IS NULL
        BEGIN
            -- Create minimal ReviewLogs table if missing (defensive)
            CREATE TABLE dbo.ReviewLogs (
                ReviewLogID INT IDENTITY(1,1) PRIMARY KEY,
                FactID INT NULL,
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

        /* Add action tracking columns to ReviewLogs */
        IF COL_LENGTH('dbo.ReviewLogs','Action') IS NULL
        BEGIN
            ALTER TABLE dbo.ReviewLogs ADD Action NVARCHAR(16) NOT NULL CONSTRAINT DF_ReviewLogs_Action DEFAULT 'view';
        END;
        IF COL_LENGTH('dbo.ReviewLogs','FactEdited') IS NULL
        BEGIN
            ALTER TABLE dbo.ReviewLogs ADD FactEdited BIT NOT NULL CONSTRAINT DF_ReviewLogs_FactEdited DEFAULT 0;
        END;
        IF COL_LENGTH('dbo.ReviewLogs','FactDeleted') IS NULL
        BEGIN
            ALTER TABLE dbo.ReviewLogs ADD FactDeleted BIT NOT NULL CONSTRAINT DF_ReviewLogs_FactDeleted DEFAULT 0;
        END;
        IF COL_LENGTH('dbo.ReviewLogs','FactContentSnapshot') IS NULL
        BEGIN
            ALTER TABLE dbo.ReviewLogs ADD FactContentSnapshot NVARCHAR(MAX) NULL;
        END;
        IF COL_LENGTH('dbo.ReviewLogs','CategoryIDSnapshot') IS NULL
        BEGIN
            ALTER TABLE dbo.ReviewLogs ADD CategoryIDSnapshot INT NULL;
        END;

        /* Add per-session action counters */
        IF COL_LENGTH('dbo.ReviewSessions','FactsAdded') IS NULL
        BEGIN
            ALTER TABLE dbo.ReviewSessions ADD FactsAdded INT NOT NULL CONSTRAINT DF_ReviewSessions_FactsAdded DEFAULT 0;
        END;
        IF COL_LENGTH('dbo.ReviewSessions','FactsEdited') IS NULL
        BEGIN
            ALTER TABLE dbo.ReviewSessions ADD FactsEdited INT NOT NULL CONSTRAINT DF_ReviewSessions_FactsEdited DEFAULT 0;
        END;
        IF COL_LENGTH('dbo.ReviewSessions','FactsDeleted') IS NULL
        BEGIN
            ALTER TABLE dbo.ReviewSessions ADD FactsDeleted INT NOT NULL CONSTRAINT DF_ReviewSessions_FactsDeleted DEFAULT 0;
        END;

        /* Attach ProfileID to ReviewSessions */
        IF COL_LENGTH('dbo.ReviewSessions','ProfileID') IS NULL
        BEGIN
            ALTER TABLE dbo.ReviewSessions ADD ProfileID INT NULL CONSTRAINT DF_ReviewSessions_ProfileID DEFAULT 1;
            UPDATE dbo.ReviewSessions SET ProfileID = 1 WHERE ProfileID IS NULL;
            ALTER TABLE dbo.ReviewSessions ALTER COLUMN ProfileID INT NOT NULL;
        END;
        IF OBJECT_ID('dbo.FK_ReviewSessions_Profile','F') IS NULL
        BEGIN
            ALTER TABLE dbo.ReviewSessions
            ADD CONSTRAINT FK_ReviewSessions_Profile
            FOREIGN KEY (ProfileID) REFERENCES dbo.GamificationProfile(ProfileID);
        END;
        IF NOT EXISTS (
            SELECT 1 FROM sys.indexes 
            WHERE name = 'IX_ReviewSessions_ProfileID' AND object_id = OBJECT_ID('dbo.ReviewSessions')
        )
        BEGIN
            CREATE INDEX IX_ReviewSessions_ProfileID ON dbo.ReviewSessions(ProfileID);
        END;

        /* Ensure FK from ReviewLogs(FactID) to Facts is ON DELETE SET NULL (to preserve logs for deleted cards) */
        IF EXISTS (
            SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_ReviewLogs_Facts'
        )
        BEGIN
            ALTER TABLE dbo.ReviewLogs DROP CONSTRAINT FK_ReviewLogs_Facts;
        END;
        /* Make FactID nullable to support SET NULL */
        IF EXISTS (
            SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.ReviewLogs') AND name = 'FactID' AND is_nullable = 0
        )
        BEGIN
            ALTER TABLE dbo.ReviewLogs ALTER COLUMN FactID INT NULL;
        END;
        /* Recreate FK with SET NULL if not exists */
        IF NOT EXISTS (
            SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_ReviewLogs_Facts'
        )
        BEGIN
            ALTER TABLE dbo.ReviewLogs WITH NOCHECK
            ADD CONSTRAINT FK_ReviewLogs_Facts FOREIGN KEY (FactID)
            REFERENCES dbo.Facts(FactID) ON DELETE SET NULL;
        END;

        /* AI usage logging */
        IF OBJECT_ID('dbo.AIUsageLogs','U') IS NULL
        BEGIN
            CREATE TABLE dbo.AIUsageLogs (
                AIUsageID INT IDENTITY(1,1) PRIMARY KEY,
                FactID INT NULL,
                SessionID INT NULL,
                ProfileID INT NOT NULL CONSTRAINT DF_AIUsageLogs_ProfileID DEFAULT 1,
                OperationType NVARCHAR(32) NOT NULL CONSTRAINT DF_AIUsageLogs_OperationType DEFAULT 'EXPLANATION',
                Status NVARCHAR(16) NOT NULL CONSTRAINT DF_AIUsageLogs_Status DEFAULT 'SUCCESS',
                ModelName NVARCHAR(200) NULL,
                Provider NVARCHAR(100) NULL,
                InputTokens INT NULL,
                OutputTokens INT NULL,
                TotalTokens AS (ISNULL(InputTokens, 0) + ISNULL(OutputTokens, 0)) PERSISTED,
                Cost DECIMAL(19,9) NULL,
                CurrencyCode CHAR(3) NOT NULL CONSTRAINT DF_AIUsageLogs_CurrencyCode DEFAULT 'USD',
                LatencyMs INT NULL,
                CreatedAt DATETIME NOT NULL CONSTRAINT DF_AIUsageLogs_CreatedAt DEFAULT GETDATE(),
                CONSTRAINT FK_AIUsageLogs_Facts FOREIGN KEY (FactID) REFERENCES dbo.Facts(FactID) ON DELETE SET NULL,
                CONSTRAINT FK_AIUsageLogs_Profile FOREIGN KEY (ProfileID) REFERENCES dbo.GamificationProfile(ProfileID),
                CONSTRAINT FK_AIUsageLogs_ReviewSessions FOREIGN KEY (SessionID) REFERENCES dbo.ReviewSessions(SessionID) ON DELETE SET NULL
            );
            CREATE INDEX IX_AIUsageLogs_FactID ON dbo.AIUsageLogs(FactID);
            CREATE INDEX IX_AIUsageLogs_SessionID ON dbo.AIUsageLogs(SessionID);
            CREATE INDEX IX_AIUsageLogs_ProfileID ON dbo.AIUsageLogs(ProfileID);
            CREATE INDEX IX_AIUsageLogs_CreatedAt ON dbo.AIUsageLogs(CreatedAt);
        END;
        IF COL_LENGTH('dbo.AIUsageLogs','ProfileID') IS NULL
        BEGIN
            ALTER TABLE dbo.AIUsageLogs ADD ProfileID INT NULL CONSTRAINT DF_AIUsageLogs_ProfileID DEFAULT 1;
            UPDATE dbo.AIUsageLogs SET ProfileID = 1 WHERE ProfileID IS NULL;
            ALTER TABLE dbo.AIUsageLogs ALTER COLUMN ProfileID INT NOT NULL;
        END;
        IF COL_LENGTH('dbo.AIUsageLogs','Status') IS NULL
        BEGIN
            ALTER TABLE dbo.AIUsageLogs ADD Status NVARCHAR(16) NULL CONSTRAINT DF_AIUsageLogs_Status DEFAULT 'SUCCESS';
            UPDATE dbo.AIUsageLogs SET Status = 'SUCCESS' WHERE Status IS NULL;
            ALTER TABLE dbo.AIUsageLogs ALTER COLUMN Status NVARCHAR(16) NOT NULL;
        END;
        IF OBJECT_ID('dbo.FK_AIUsageLogs_Profile','F') IS NULL
        BEGIN
            ALTER TABLE dbo.AIUsageLogs
            ADD CONSTRAINT FK_AIUsageLogs_Profile FOREIGN KEY (ProfileID) REFERENCES dbo.GamificationProfile(ProfileID);
        END;
        IF NOT EXISTS (
            SELECT 1 FROM sys.indexes 
            WHERE name = 'IX_AIUsageLogs_ProfileID' AND object_id = OBJECT_ID('dbo.AIUsageLogs')
        )
        BEGIN
            CREATE INDEX IX_AIUsageLogs_ProfileID ON dbo.AIUsageLogs(ProfileID);
        END;

        IF OBJECT_ID('dbo.Achievements','U') IS NULL
        BEGIN
            CREATE TABLE dbo.Achievements (
                AchievementID INT IDENTITY(1,1) PRIMARY KEY,
                Code NVARCHAR(64) NOT NULL UNIQUE,
                Name NVARCHAR(200) NOT NULL,
                Category NVARCHAR(32) NOT NULL,
                Threshold INT NOT NULL,
                RewardXP INT NOT NULL,
                CreatedDate DATETIME NOT NULL CONSTRAINT DF_Achievements_CreatedDate DEFAULT GETDATE()
            );
        END;
        ELSE
        BEGIN
            /* Drop IsHidden if it exists (unused) */
            IF COL_LENGTH('dbo.Achievements','IsHidden') IS NOT NULL
            BEGIN
                DECLARE @df_ach NVARCHAR(128);
                SELECT @df_ach = dc.name
                FROM sys.default_constraints dc
                JOIN sys.columns c ON c.column_id = dc.parent_column_id AND c.object_id = dc.parent_object_id
                WHERE dc.parent_object_id = OBJECT_ID('dbo.Achievements') AND c.name = 'IsHidden';
                IF @df_ach IS NOT NULL 
                BEGIN
                    DECLARE @cmd_drop_df_ach NVARCHAR(400);
                    SET @cmd_drop_df_ach = 'ALTER TABLE dbo.Achievements DROP CONSTRAINT ' + QUOTENAME(@df_ach);
                    EXEC(@cmd_drop_df_ach);
                END;
                ALTER TABLE dbo.Achievements DROP COLUMN IsHidden;
            END;
        END;

        IF OBJECT_ID('dbo.AchievementUnlocks','U') IS NULL
        BEGIN
            CREATE TABLE dbo.AchievementUnlocks (
                UnlockID INT IDENTITY(1,1) PRIMARY KEY,
                AchievementID INT NOT NULL
                    CONSTRAINT FK_AchievementUnlocks_Achievements
                    REFERENCES dbo.Achievements(AchievementID),
                ProfileID INT NOT NULL CONSTRAINT DF_AchievementUnlocks_ProfileID DEFAULT 1,
                UnlockDate DATETIME NOT NULL CONSTRAINT DF_AchievementUnlocks_UnlockDate DEFAULT GETDATE(),
                Notified BIT NOT NULL CONSTRAINT DF_AchievementUnlocks_Notified DEFAULT 0,
                CONSTRAINT FK_AchievementUnlocks_Profile FOREIGN KEY (ProfileID) REFERENCES dbo.GamificationProfile(ProfileID)
            );
            CREATE UNIQUE INDEX UX_AchievementUnlocks_Profile_Achievement ON dbo.AchievementUnlocks(ProfileID, AchievementID);
        END;
        ELSE
        BEGIN
            IF COL_LENGTH('dbo.AchievementUnlocks','ProfileID') IS NULL
            BEGIN
                ALTER TABLE dbo.AchievementUnlocks ADD ProfileID INT NULL CONSTRAINT DF_AchievementUnlocks_ProfileID DEFAULT 1;
                UPDATE dbo.AchievementUnlocks SET ProfileID = 1 WHERE ProfileID IS NULL;
                ALTER TABLE dbo.AchievementUnlocks ALTER COLUMN ProfileID INT NOT NULL;
            END;
            IF OBJECT_ID('dbo.FK_AchievementUnlocks_Profile','F') IS NULL
            BEGIN
                ALTER TABLE dbo.AchievementUnlocks
                ADD CONSTRAINT FK_AchievementUnlocks_Profile FOREIGN KEY (ProfileID) REFERENCES dbo.GamificationProfile(ProfileID);
            END;
            IF EXISTS (SELECT * FROM sys.indexes WHERE name = 'UX_AchievementUnlocks_AchievementID' AND object_id = OBJECT_ID('dbo.AchievementUnlocks'))
            BEGIN
                DROP INDEX UX_AchievementUnlocks_AchievementID ON dbo.AchievementUnlocks;
            END;
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UX_AchievementUnlocks_Profile_Achievement' AND object_id = OBJECT_ID('dbo.AchievementUnlocks'))
            BEGIN
                CREATE UNIQUE INDEX UX_AchievementUnlocks_Profile_Achievement ON dbo.AchievementUnlocks(ProfileID, AchievementID);
            END;
        END;

        /* Seed Achievements (insert any missing by Code) */
            ;WITH Seeds (Code, Name, Category, Threshold, RewardXP) AS (
                SELECT 'KNOWN_5','Know 5 facts','known',5,10 UNION ALL
                SELECT 'KNOWN_10','Know 10 facts','known',10,15 UNION ALL
                SELECT 'KNOWN_50','Know 50 facts','known',50,25 UNION ALL
                SELECT 'KNOWN_100','Know 100 facts','known',100,50 UNION ALL
                SELECT 'KNOWN_300','Know 300 facts','known',300,100 UNION ALL
                SELECT 'KNOWN_500','Know 500 facts','known',500,150 UNION ALL
                SELECT 'KNOWN_1000','Know 1000 facts','known',1000,250 UNION ALL
                SELECT 'KNOWN_5000','Know 5000 facts','known',5000,600 UNION ALL
                SELECT 'KNOWN_10000','Know 10000 facts','known',10000,1000 UNION ALL
                SELECT 'KNOWN_30000','Know 30000 facts','known',30000,2500 UNION ALL
                SELECT 'KNOWN_50000','Know 50000 facts','known',50000,4000 UNION ALL
                SELECT 'KNOWN_100000','Know 100000 facts','known',100000,7000 UNION ALL

                SELECT 'FAV_5','Favorite 5 facts','favorites',5,5 UNION ALL
                SELECT 'FAV_10','Favorite 10 facts','favorites',10,10 UNION ALL
                SELECT 'FAV_50','Favorite 50 facts','favorites',50,20 UNION ALL
                SELECT 'FAV_100','Favorite 100 facts','favorites',100,40 UNION ALL
                SELECT 'FAV_300','Favorite 300 facts','favorites',300,80 UNION ALL
                SELECT 'FAV_500','Favorite 500 facts','favorites',500,120 UNION ALL
                SELECT 'FAV_1000','Favorite 1000 facts','favorites',1000,200 UNION ALL
                SELECT 'FAV_5000','Favorite 5000 facts','favorites',5000,500 UNION ALL
                SELECT 'FAV_10000','Favorite 10000 facts','favorites',10000,900 UNION ALL
                SELECT 'FAV_30000','Favorite 30000 facts','favorites',30000,2200 UNION ALL
                SELECT 'FAV_50000','Favorite 50000 facts','favorites',50000,3500 UNION ALL
                SELECT 'FAV_100000','Favorite 100000 facts','favorites',100000,6000 UNION ALL

                SELECT 'REV_5','Review 5 times','reviews',5,10 UNION ALL
                SELECT 'REV_10','Review 10 times','reviews',10,15 UNION ALL
                SELECT 'REV_50','Review 50 times','reviews',50,25 UNION ALL
                SELECT 'REV_100','Review 100 times','reviews',100,50 UNION ALL
                SELECT 'REV_300','Review 300 times','reviews',300,100 UNION ALL
                SELECT 'REV_500','Review 500 times','reviews',500,150 UNION ALL
                SELECT 'REV_1000','Review 1000 times','reviews',1000,250 UNION ALL
                SELECT 'REV_5000','Review 5000 times','reviews',5000,600 UNION ALL
                SELECT 'REV_10000','Review 10000 times','reviews',10000,1000 UNION ALL
                SELECT 'REV_30000','Review 30000 times','reviews',30000,2500 UNION ALL
                SELECT 'REV_50000','Review 50000 times','reviews',50000,4000 UNION ALL
                SELECT 'REV_100000','Review 100000 times','reviews',100000,7000 UNION ALL

                SELECT 'ADD_5','Add 5 facts','adds',5,10 UNION ALL
                SELECT 'ADD_10','Add 10 facts','adds',10,15 UNION ALL
                SELECT 'ADD_50','Add 50 facts','adds',50,25 UNION ALL
                SELECT 'ADD_100','Add 100 facts','adds',100,50 UNION ALL
                SELECT 'ADD_300','Add 300 facts','adds',300,100 UNION ALL
                SELECT 'ADD_500','Add 500 facts','adds',500,150 UNION ALL
                SELECT 'ADD_1000','Add 1000 facts','adds',1000,250 UNION ALL
                SELECT 'ADD_5000','Add 5000 facts','adds',5000,600 UNION ALL
                SELECT 'ADD_10000','Add 10000 facts','adds',10000,1000 UNION ALL
                SELECT 'ADD_30000','Add 30000 facts','adds',30000,2500 UNION ALL
                SELECT 'ADD_50000','Add 50000 facts','adds',50000,4000 UNION ALL
                SELECT 'ADD_100000','Add 100000 facts','adds',100000,7000 UNION ALL

                SELECT 'EDIT_5','Edit 5 facts','edits',5,10 UNION ALL
                SELECT 'EDIT_10','Edit 10 facts','edits',10,15 UNION ALL
                SELECT 'EDIT_50','Edit 50 facts','edits',50,25 UNION ALL
                SELECT 'EDIT_100','Edit 100 facts','edits',100,50 UNION ALL
                SELECT 'EDIT_300','Edit 300 facts','edits',300,100 UNION ALL
                SELECT 'EDIT_500','Edit 500 facts','edits',500,150 UNION ALL
                SELECT 'EDIT_1000','Edit 1000 facts','edits',1000,250 UNION ALL
                SELECT 'EDIT_5000','Edit 5000 facts','edits',5000,600 UNION ALL
                SELECT 'EDIT_10000','Edit 10000 facts','edits',10000,1000 UNION ALL
                SELECT 'EDIT_30000','Edit 30000 facts','edits',30000,2500 UNION ALL
                SELECT 'EDIT_50000','Edit 50000 facts','edits',50000,4000 UNION ALL
                SELECT 'EDIT_100000','Edit 100000 facts','edits',100000,7000 UNION ALL

                SELECT 'DEL_5','Delete 5 facts','deletes',5,10 UNION ALL
                SELECT 'DEL_10','Delete 10 facts','deletes',10,15 UNION ALL
                SELECT 'DEL_50','Delete 50 facts','deletes',50,25 UNION ALL
                SELECT 'DEL_100','Delete 100 facts','deletes',100,50 UNION ALL
                SELECT 'DEL_300','Delete 300 facts','deletes',300,100 UNION ALL
                SELECT 'DEL_500','Delete 500 facts','deletes',500,150 UNION ALL
                SELECT 'DEL_1000','Delete 1000 facts','deletes',1000,250 UNION ALL
                SELECT 'DEL_5000','Delete 5000 facts','deletes',5000,600 UNION ALL
                SELECT 'DEL_10000','Delete 10000 facts','deletes',10000,1000 UNION ALL
                SELECT 'DEL_30000','Delete 30000 facts','deletes',30000,2500 UNION ALL
                SELECT 'DEL_50000','Delete 50000 facts','deletes',50000,4000 UNION ALL
                SELECT 'DEL_100000','Delete 100000 facts','deletes',100000,7000 UNION ALL

                /* Streaks */
                SELECT 'STREAK_3','3-day review streak','streak',3,10 UNION ALL
                SELECT 'STREAK_7','7-day review streak','streak',7,20 UNION ALL
                SELECT 'STREAK_14','14-day review streak','streak',14,35 UNION ALL
                SELECT 'STREAK_30','30-day review streak','streak',30,75 UNION ALL
                SELECT 'STREAK_60','60-day review streak','streak',60,150 UNION ALL
                SELECT 'STREAK_90','90-day review streak','streak',90,250 UNION ALL
                SELECT 'STREAK_180','180-day review streak','streak',180,500 UNION ALL
                SELECT 'STREAK_365','365-day review streak','streak',365,1000
            )
            INSERT INTO dbo.Achievements (Code, Name, Category, Threshold, RewardXP, CreatedDate)
            SELECT s.Code, s.Name, s.Category, s.Threshold, s.RewardXP, GETDATE()
            FROM Seeds s
            LEFT JOIN dbo.Achievements a ON a.Code = s.Code
            WHERE a.AchievementID IS NULL;
        

        /* Ensure a single GamificationProfile row exists */
        IF NOT EXISTS (SELECT 1 FROM dbo.GamificationProfile)
        BEGIN
            INSERT INTO dbo.GamificationProfile (XP, Level)
            VALUES (0, 1);
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

        win = tk.Toplevel(self.root)
        win.title("AI Fact Explanation")
        try:
            win.geometry(f"{self.POPUP_EDIT_CARD_SIZE}{self.POPUP_POSITION}")
        except Exception:
            win.geometry(self.POPUP_EDIT_CARD_SIZE)
        win.configure(bg=self.BG_COLOR)

        def on_close():
            try:
                self.resume_review_timer()
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

        def update_text(text):
            explain_box.config(state="normal")
            explain_box.delete("1.0", "end")
            explain_box.insert("1.0", text.strip())
            explain_box.config(state="disabled")

        def worker():
            # Disable button so you can't click it twice while waiting
            self.root.after(0, lambda: self.ai_button.config(state="disabled")) 
            
            result_text, usage_info = self._call_together_ai(fact_text, api_key)

            try:
                self._record_ai_usage(usage_info, fact_id=fact_id, session_id=session_id)
            except Exception as exc:
                print(f"AI usage logging error: {exc}")
            
            self.root.after(0, lambda: update_text(result_text))
            # Re-enable button
            self.root.after(0, lambda: self.ai_button.config(state="normal"))

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
        try:
            payload = {
                "model": usage_info["model"],
                "messages": [
                    {
                        "role": "system",
                        "content": "You explain short facts clearly in simple language. Keep it concise: 2 short paragraphs max."
                    },
                    {
                        "role": "user",
                        "content": f"Explain this fact in simple words and briefly elaborate:\n\n{fact_text}"
                    }
                ],
                "max_tokens": 320,
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
            latency_ms = int((time.perf_counter() - started) * 1000)
            usage_info["latency_ms"] = latency_ms
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
        except Exception as exc:
            try:
                usage_info["latency_ms"] = int((time.perf_counter() - started) * 1000)
            except Exception:
                pass
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

    def _record_ai_usage(self, usage_info: dict, fact_id: int, session_id=None):
        """Persist AI usage row and roll totals into gamification profile."""
        if not usage_info:
            return
        if fact_id is None:
            return
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

        status = usage_info.get("status") or "SUCCESS"
        try:
            status = str(status).upper()
        except Exception:
            status = "SUCCESS"
        if status not in ("SUCCESS", "FAILED"):
            status = "SUCCESS"

        resolved_session_id = session_id if session_id is not None else getattr(self, 'current_session_id', None)

        self._log_ai_usage(
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
        )

    def _log_ai_usage(self, fact_id, session_id, operation_type, status, model_name, provider, input_tokens, output_tokens, total_tokens, cost, latency_ms):
        """Insert into AIUsageLogs and roll totals into GamificationProfile."""
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

        profile_id = self.get_active_profile_id()
        try:
            self.execute_update(
                """
                INSERT INTO AIUsageLogs (FactID, SessionID, ProfileID, OperationType, Status, ModelName, Provider, InputTokens, OutputTokens, Cost, CurrencyCode, LatencyMs)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                ),
            )
        except Exception as exc:
            print(f"Database error in _log_ai_usage: {exc}")

        try:
            if self.gamify and (total_for_profile is not None or (cost_val is not None and cost_val != 0)):
                self.gamify.add_ai_usage(total_for_profile or 0, cost_val or 0.0)
        except Exception as exc:
            print(f"Gamification error in _log_ai_usage: {exc}")

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
        """

        facts = []
        if category == "All Categories":
            query = base_select + " ORDER BY NEWID()"
            facts = self.fetch_query(query, (profile_id,))
        elif category == "Favorites":
            query = base_select + " WHERE COALESCE(pf.IsFavorite,0) = 1 ORDER BY NEWID()"
            facts = self.fetch_query(query, (profile_id,))
        elif category == "Known":
            query = base_select + " WHERE COALESCE(pf.IsEasy,0) = 1 ORDER BY NEWID()"
            facts = self.fetch_query(query, (profile_id,))
        elif category == "Not Known":
            query = base_select + " WHERE COALESCE(pf.IsEasy,0) = 0 ORDER BY NEWID()"
            facts = self.fetch_query(query, (profile_id,))
        elif category == "Not Favorite":
            query = base_select + " WHERE COALESCE(pf.IsFavorite,0) = 0 ORDER BY NEWID()"
            facts = self.fetch_query(query, (profile_id,))
        else:
            query = base_select + """
                JOIN Categories c ON f.CategoryID = c.CategoryID
                WHERE c.CategoryName = ?
                ORDER BY NEWID()
            """
            facts = self.fetch_query(query, (profile_id, category))

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
            WHERE FactID = ?
        """, (fact_id,))
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
        except Exception:
            pass

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
        if not self.current_fact_id:
            return
        profile_id = self.get_active_profile_id()
        new_status = not self.current_fact_is_easy
        success = self.execute_update(
            """
            MERGE ProfileFacts AS target
            USING (SELECT ? AS ProfileID, ? AS FactID) AS src
            ON target.ProfileID = src.ProfileID AND target.FactID = src.FactID
            WHEN MATCHED THEN
                UPDATE SET IsEasy = ?, LastViewedByUser = COALESCE(target.LastViewedByUser, GETDATE())
            WHEN NOT MATCHED THEN
                INSERT (ProfileID, FactID, PersonalReviewCount, IsFavorite, IsEasy, LastViewedByUser)
                VALUES (src.ProfileID, src.FactID, 0, 0, ?, GETDATE());
            """,
            (profile_id, self.current_fact_id, 1 if new_status else 0, 1 if new_status else 0)
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
        
        # On close, resume timer then destroy
        def on_close_add():
            try:
                self.resume_review_timer()
            except Exception:
                pass
            add_window.destroy()
        add_window.protocol("WM_DELETE_WINDOW", on_close_add)
        
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
        
        def save_fact(close_after=True):
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
            
            # Duplicate check using the same normalization as ContentKey
            try:
                dup = self.fetch_query(
                    """
                    SELECT TOP 1 FactID
                    FROM dbo.Facts
                    WHERE ContentKey = CAST(LOWER(LTRIM(RTRIM(REPLACE(REPLACE(REPLACE(?, CHAR(13), ' '), CHAR(10), ' '), CHAR(9), ' ')))) AS NVARCHAR(450))
                    """,
                    (content,)
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
                INSERT INTO Facts (CategoryID, Content, DateAdded, TotalViews)
                OUTPUT INSERTED.FactID
                VALUES (?, ?, GETDATE(), 0)
                """,
                (category_id, content)
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
        
        # Pause timer while editing
        self.pause_review_timer()

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

        # Resume timer when window is closed via [X]
        def on_close_edit():
            try:
                self.resume_review_timer()
            except Exception:
                pass
            edit_window.destroy()
        edit_window.protocol("WM_DELETE_WINDOW", on_close_edit)
        
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
            
            # Prevent duplicates: check against computed ContentKey, ignoring this FactID
            try:
                dup = self.fetch_query(
                    """
                    SELECT TOP 1 FactID
                    FROM dbo.Facts
                    WHERE ContentKey = CAST(LOWER(LTRIM(RTRIM(REPLACE(REPLACE(REPLACE(?, CHAR(13), ' '), CHAR(10), ' '), CHAR(9), ' ')))) AS NVARCHAR(450))
                      AND FactID <> ?
                    """,
                    (content, self.current_fact_id)
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
                WHERE FactID = ?
                """, 
                (category_id, content, self.current_fact_id)
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
        
        # Pause during confirmation and deletion flow
        self.pause_review_timer()
        try:
            # Ask for confirmation
            if self.confirm_dialog("Confirm Delete", "Are you sure you want to delete this fact?"):
                # Capture snapshot before delete
                try:
                    row = self.fetch_query(
                        "SELECT Content, CategoryID FROM Facts WHERE FactID = ?",
                        (self.current_fact_id,)
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
                success = self.execute_update("DELETE FROM Facts WHERE FactID = ?", (self.current_fact_id,))
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
