#MemoDari.py
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
import json
from ctypes import wintypes
from PIL import Image, ImageTk
from datetime import datetime, timedelta, timezone
from tkinter import ttk, simpledialog, messagebox
from fsrs_engine import FSRSEngine

class MemoDariApp:
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
        self.AGAIN_COLOR = config.UI_CONFIG.get('again_color', "#FF0000")  # Use config or default
        
        # Fonts
        self.TITLE_FONT = config.get_font('title')
        self.NORMAL_FONT = config.get_font('normal')
        self.SMALL_FONT = config.get_font('small')
        self.LARGE_FONT = config.get_font('large')
        self.STATS_FONT = config.get_font('stats')
        
        # Instance variables (replacing globals)
        self.x_window = 0
        self.y_window = 0
        self.current_factcard_id = None
        self.show_answer = False
        self.is_home_page = True
        
        # Initialize FSRS Engine with weights file from config 
        self.fsrs_engine = FSRSEngine(config.WEIGHTS_FILE)
        
        # Create main window
        self.root = tk.Tk()
        self.root.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}")
        self.root.overrideredirect(True)
        self.root.configure(bg=self.BG_COLOR)
        
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
        self.root.after(100, self.update_ui)
        
        # Show the home page
        self.show_home_page()
    
    def load_categories(self):
        """Load categories for the dropdown"""
        query = "SELECT DISTINCT CategoryName FROM Categories WHERE IsActive = 1 ORDER BY CategoryName"
        categories = self.fetch_query(query)
        category_names = [category[0] for category in categories] if categories else []
        category_names.insert(0, "All Categories")  # Add All Categories option
        return category_names

    def setup_ui(self):
        """Set up all UI elements"""
        # Title bar
        self.title_bar = tk.Frame(self.root, bg=self.TITLE_BG_COLOR, height=30, relief='raised')
        self.title_bar.pack(side="top", fill="x")
        
        tk.Label(self.title_bar, text="MemoDari", fg=self.TEXT_COLOR, bg=self.TITLE_BG_COLOR, 
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
        
        # Apply additional styling classes from CSS
        self.category_dropdown.pack(side="left")
        
        # Use option_add to style dropdown items
        self.root.option_add('*TCombobox*Listbox*Background', '#333333')
        self.root.option_add('*TCombobox*Listbox*Foreground', self.TEXT_COLOR)
        self.root.option_add('*TCombobox*Listbox*selectBackground', self.GREEN_COLOR)
        
        # Main content area
        self.content_frame = tk.Frame(self.root, bg=self.BG_COLOR)
        self.content_frame.pack(side="top", fill="both", expand=True, padx=10, pady=5)
        
        # Fact card display
        self.factcard_frame = tk.Frame(self.content_frame, bg=self.BG_COLOR)
        self.factcard_frame.pack(side="top", fill="both", expand=True, pady=5)
        
        # Add top padding to push content down
        self.padding_frame = tk.Frame(self.factcard_frame, bg=self.BG_COLOR, height=30)
        self.padding_frame.pack(side="top", fill="x")
        
        self.factcard_label = tk.Label(self.factcard_frame, text="Welcome to MemoDari!", fg=self.TEXT_COLOR, bg=self.BG_COLOR, 
                                  font=self.LARGE_FONT, wraplength=450, justify="center")
        self.factcard_label.pack(side="top", fill="both", expand=True, padx=10, pady=10)
        
        # Create slogan label
        self.slogan_label = tk.Label(self.content_frame, text="Strengthen your knowledge one fact at a time", 
                              fg=self.GREEN_COLOR, bg=self.BG_COLOR, font=(self.NORMAL_FONT[0], 12, 'italic'))
        
        # Create start learning button
        self.start_button = tk.Button(self.content_frame, text="Start Learning", command=self.start_learning, 
                              bg=self.GREEN_COLOR, fg=self.TEXT_COLOR, cursor="hand2", borderwidth=0, 
                              highlightthickness=0, padx=20, pady=10,
                              font=self.LARGE_FONT)
        
        # Create a frame for Show Answer and Mastery info
        self.answer_mastery_frame = tk.Frame(self.content_frame, bg=self.BG_COLOR)
        
        # Show Answer button in the combined frame
        self.show_answer_button = tk.Button(self.answer_mastery_frame, text="Show Answer", command=self.toggle_question_answer, 
                                      bg=self.BLUE_COLOR, fg=self.TEXT_COLOR, cursor="hand2", borderwidth=0, 
                                      highlightthickness=0, padx=10, pady=5, state="disabled")
        self.show_answer_button.pack(fill="x", padx=100, pady=2)
        
        # Stability level display (renamed from Mastery)
        self.mastery_level_label = tk.Label(self.answer_mastery_frame, text="Stability: N/A", fg=self.TEXT_COLOR, bg=self.BG_COLOR, 
                                     font=self.NORMAL_FONT)
        self.mastery_level_label.pack(side="top", pady=2)
        
        # Add progress bar for stability
        self.mastery_progress = ttk.Progressbar(self.answer_mastery_frame, orient="horizontal", length=280, mode="determinate")
        self.mastery_progress.pack(side="top", pady=2)
        
        # Style the progress bar
        style = ttk.Style()
        style.theme_use('default')
        style.configure("TProgressbar", thickness=8, troughcolor='#333333', background=self.GREEN_COLOR)
        
        # Spaced repetition buttons - UPDATED FOR FSRS
        self.sr_frame = tk.Frame(self.content_frame, bg=self.BG_COLOR)
        
        sr_buttons = tk.Frame(self.sr_frame, bg=self.BG_COLOR)
        sr_buttons.pack(side="top", fill="x")
        
        # Add the "Again" button for FSRS rating 0
        self.again_button = tk.Button(sr_buttons, text="Again", command=lambda: self.update_factcard_schedule("Again"), 
                           bg=self.AGAIN_COLOR, fg=self.TEXT_COLOR,  # Bright red to distinguish from "Hard" 
                           cursor="hand2", borderwidth=0, highlightthickness=0, padx=10, pady=5)
        self.again_button.pack(side="left", expand=True, fill="x", padx=(0, 5))
        
        # Existing buttons but updated for FSRS
        self.hard_button = tk.Button(sr_buttons, text="Hard", command=lambda: self.update_factcard_schedule("Hard"), 
                              bg=self.RED_COLOR, fg=self.TEXT_COLOR, cursor="hand2", borderwidth=0, 
                              highlightthickness=0, padx=10, pady=5)
        self.hard_button.pack(side="left", expand=True, fill="x", padx=(0, 5))
        
        self.medium_button = tk.Button(sr_buttons, text="Good", command=lambda: self.update_factcard_schedule("Medium"), 
                                cursor="hand2", borderwidth=0, highlightthickness=0, padx=10, pady=5,
                                bg=self.YELLOW_COLOR, fg=self.TEXT_COLOR)
        self.medium_button.pack(side="left", expand=True, fill="x", padx=(0, 5))
        
        self.easy_button = tk.Button(sr_buttons, text="Easy", command=lambda: self.update_factcard_schedule("Easy"), 
                               bg=self.GREEN_COLOR, fg=self.TEXT_COLOR, cursor="hand2", borderwidth=0, 
                               highlightthickness=0, padx=10, pady=5)
        self.easy_button.pack(side="left", expand=True, fill="x")
        
        # Load icons
        self.load_icons()
        
        # Icon buttons frame
        self.icon_buttons_frame = tk.Frame(self.content_frame, bg=self.BG_COLOR)
        
        # Add button
        self.add_icon_button = tk.Button(self.icon_buttons_frame, image=self.add_icon, bg=self.BG_COLOR, command=self.add_new_factcard,
                                 cursor="hand2", borderwidth=0, highlightthickness=0)
        self.add_icon_button.pack(side="left", padx=10)
        
        # Create edit button but don't pack it initially
        self.edit_icon_button = tk.Button(self.icon_buttons_frame, image=self.edit_icon, bg=self.BG_COLOR, command=self.edit_current_factcard,
                                  cursor="hand2", borderwidth=0, highlightthickness=0)
        
        # Create delete button but don't pack it initially
        self.delete_icon_button = tk.Button(self.icon_buttons_frame, image=self.delete_icon, bg=self.BG_COLOR, command=self.delete_current_factcard,
                                    cursor="hand2", borderwidth=0, highlightthickness=0)
        
        # Status label - always visible
        self.status_label = self.create_label(self.icon_buttons_frame, "", fg=self.STATUS_COLOR, 
                                        font=self.NORMAL_FONT, side='right')
        self.status_label.pack_configure(pady=5, padx=10)
        
        # Add home and speaker buttons
        self.home_button = tk.Button(self.factcard_frame, image=self.home_icon, bg=self.BG_COLOR, bd=0, highlightthickness=0, 
                               cursor="hand2", activebackground=self.BG_COLOR, command=self.show_home_page)
        self.home_button.place(relx=0, rely=0, anchor="nw", x=5, y=5)
        
        self.speaker_button = tk.Button(self.factcard_frame, image=self.speaker_icon, bg=self.BG_COLOR, command=self.speak_text, 
                                  cursor="hand2", borderwidth=0, highlightthickness=0)
        self.speaker_button.place(relx=1.0, rely=0, anchor="ne", x=-5, y=5)
        
        # Add graph button
        self.graph_button = tk.Button(self.factcard_frame, image=self.graph_icon, bg=self.BG_COLOR, command=self.show_analytics, 
                                cursor="hand2", borderwidth=0, highlightthickness=0)
        self.graph_button.place(relx=1.0, rely=0, anchor="ne", x=-30, y=5)  # Position it to the left of speaker button
        
        # Bottom stats frame
        self.stats_frame = tk.Frame(self.root, bg=self.BG_COLOR)
        
        # Stats labels
        self.factcard_count_label = self.create_label(self.stats_frame, "Total Fact Cards: 0", 
                                            font=self.STATS_FONT, side='left')
        self.factcard_count_label.pack_configure(padx=10)
        
        self.due_count_label = self.create_label(self.stats_frame, "Due today: 0", 
                                       font=self.STATS_FONT, side='left')
        self.due_count_label.pack_configure(padx=10)
        
        self.coordinate_label = self.create_label(self.stats_frame, "Coordinates: ", 
                                        font=self.STATS_FONT, side='right')
        self.coordinate_label.pack_configure(padx=10)
        
        # Initially disable the review buttons
        self.show_review_buttons(False)
    
    def load_icons(self):
        """Load all icons used in the application using the config module"""
        self.home_icon = ImageTk.PhotoImage(Image.open(config.get_icon_path("Home.png")).resize((20, 20), Image.Resampling.LANCZOS))
        self.speaker_icon = ImageTk.PhotoImage(Image.open(config.get_icon_path("speaker_icon.png")).resize((20, 20), Image.Resampling.LANCZOS))
        self.add_icon = ImageTk.PhotoImage(Image.open(config.get_icon_path("add.png")).resize((20, 20), Image.Resampling.LANCZOS))
        self.edit_icon = ImageTk.PhotoImage(Image.open(config.get_icon_path("edit.png")).resize((20, 20), Image.Resampling.LANCZOS))
        self.delete_icon = ImageTk.PhotoImage(Image.open(config.get_icon_path("delete.png")).resize((20, 20), Image.Resampling.LANCZOS))
        self.graph_icon = ImageTk.PhotoImage(Image.open(config.get_icon_path("graph.png")).resize((20, 20), Image.Resampling.LANCZOS))
    
    def bind_events(self):
        """Bind all event handlers"""
        self.title_bar.bind("<Button-1>", self.on_press)
        self.title_bar.bind("<B1-Motion>", self.on_drag)
        self.root.bind("<FocusIn>", lambda event: self.root.attributes('-alpha', 1.0))
        self.root.bind("<FocusOut>", lambda event: self.root.attributes('-alpha', 0.7))
        self.root.bind("<s>", self.set_static_position)
        self.category_dropdown.bind("<<ComboboxSelected>>", self.on_category_change)
    
    def apply_rounded_corners(self, radius=None):
        """Apply rounded corners to the window"""
        if radius is None:
            radius = self.CORNER_RADIUS
            
        hWnd = wintypes.HWND(int(self.root.frame(), 16))
        hRgn = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, self.root.winfo_width(), self.root.winfo_height(), radius, radius)
        ctypes.windll.user32.SetWindowRgn(hWnd, hRgn, True)
    
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
    
    def execute_query(self, query, params=None, fetch=True):
        """Legacy method for backward compatibility"""
        if fetch:
            return self.fetch_query(query, params)
        else:
            return self.execute_update(query, params)
    
    def count_factcards(self):
        """Count total fact cards in the database"""
        result = self.fetch_query("SELECT COUNT(*) FROM FactCards")
        return result[0][0] if result and len(result) > 0 else 0
    
    def update_ui(self):
        """Update UI elements periodically"""
        self.update_coordinates()
        if not self.is_home_page:
            self.update_factcard_count()
        self.root.after(100, self.update_ui)
    
    def update_factcard_count(self):
        """Update the fact card count display"""
        num_factcards = self.count_factcards()
        self.factcard_count_label.config(text=f"Total Fact Cards: {num_factcards}")
    
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
        """Speak the current fact card text"""
        # Disable the speaker button while speaking
        self.speaker_button.config(state="disabled")
        
        text = self.factcard_label.cget("text")
        # Remove "Question: " or "Answer: " prefix if present
        if text.startswith("Question: "):
            text = text[10:]
        elif text.startswith("Answer: "):
            text = text[8:]
        
        engine = pyttsx3.init()
        engine.say(text)
        
        # Define a callback to re-enable the button when speech is done
        def on_speech_done():
            self.speaker_button.config(state="normal")
        
        # Schedule the button to be re-enabled after speech is complete
        engine.connect('finished-utterance', lambda name, completed: self.root.after(100, on_speech_done))
        engine.runAndWait()
    
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
        flask_app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "analytics.py")
        
        # Start Flask server
        if sys.platform.startswith('win'):
            self.flask_process = subprocess.Popen(["python", flask_app_path], 
                                               creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        else:
            # Linux/Mac
            self.flask_process = subprocess.Popen(["python3", flask_app_path], 
                                               preexec_fn=os.setsid)
        
        # Register exit handler to close Flask server when the main app exits
        atexit.register(self.close_flask_server)

    def close_flask_server(self):
        """Close the Flask server when the main application exits"""
        if hasattr(self, 'flask_process') and self.flask_process.poll() is None:
            if sys.platform.startswith('win'):
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(self.flask_process.pid)])
            else:
                # Linux/Mac
                os.killpg(os.getpgid(self.flask_process.pid), signal.SIGTERM)
    
    def get_due_factcard_count(self):
        """Get count of fact cards due for review today"""
        current_date = datetime.now().strftime('%Y-%m-%d')
        category = self.category_var.get()
        
        if category == "All Categories":
            query = """
            SELECT COUNT(*) 
            FROM FactCards 
            WHERE CONVERT(date, NextReviewDate) <= CONVERT(date, ?)
            """
            result = self.fetch_query(query, (current_date,))
        else:
            query = """
            SELECT COUNT(*) 
            FROM FactCards f
            JOIN Categories c ON f.CategoryID = c.CategoryID
            WHERE CONVERT(date, f.NextReviewDate) <= CONVERT(date, ?) 
            AND c.CategoryName = ?
            """
            result = self.fetch_query(query, (current_date, category))
        
        return result[0][0] if result and len(result) > 0 else 0
    
    def get_next_review_info(self):
        """Get information about the next review date after today"""
        current_date = datetime.now().strftime('%Y-%m-%d')
        category = self.category_var.get()
        
        if category == "All Categories":
            query = """
                SELECT MIN(NextReviewDate)
                FROM FactCards 
                WHERE NextReviewDate > ?
            """
            result = self.fetch_query(query, (current_date,))
        else:
            query = """
                SELECT MIN(f.NextReviewDate)
                FROM FactCards f
                JOIN Categories c ON f.CategoryID = c.CategoryID
                WHERE f.NextReviewDate > ? AND c.CategoryName = ?
            """
            result = self.fetch_query(query, (current_date, category))
        
        if result and len(result) > 0 and result[0][0]:
            next_date = result[0][0]
            # Count fact cards due on the next date
            if category == "All Categories":
                query = """
                    SELECT COUNT(*)
                    FROM FactCards 
                    WHERE NextReviewDate = ?
                """
                count_result = self.fetch_query(query, (next_date,))
            else:
                query = """
                    SELECT COUNT(*)
                    FROM FactCards f
                    JOIN Categories c ON f.CategoryID = c.CategoryID
                    WHERE f.NextReviewDate = ? AND c.CategoryName = ?
                """
                count_result = self.fetch_query(query, (next_date, category))
            count = count_result[0][0] if count_result and len(count_result) > 0 else 0
            return next_date, count
        return None, 0
    
    def toggle_question_answer(self):
        """Toggle between showing question and answer"""
        if self.current_factcard_id is None:
            return
        
        # Toggle between question and answer
        self.show_answer = not self.show_answer
        
        if self.show_answer:
            # Fetch the answer from the database
            query = "SELECT Answer FROM FactCards WHERE FactCardID = ?"
            result = self.fetch_query(query, (self.current_factcard_id,))
            if result and len(result) > 0:
                answer = result[0][0]
                self.factcard_label.config(text=f"Answer: {answer}", font=(self.NORMAL_FONT[0], self.adjust_font_size(answer)))
                self.show_answer_button.config(text="Show Question")
            else:
                self.status_label.config(text="Error: Could not retrieve answer", fg=self.RED_COLOR)
                self.clear_status_after_delay()
        else:
            # Show the question again
            query = "SELECT Question FROM FactCards WHERE FactCardID = ?"
            result = self.fetch_query(query, (self.current_factcard_id,))
            if result and len(result) > 0:
                question = result[0][0]
                self.factcard_label.config(text=f"Question: {question}", font=(self.NORMAL_FONT[0], self.adjust_font_size(question)))
                self.show_answer_button.config(text="Show Answer")
            else:
                self.status_label.config(text="Error: Could not retrieve question", fg=self.RED_COLOR)
                self.clear_status_after_delay()
        
        # Keep stability display updated
        self.update_stability_display()
    
    def update_stability_display(self):
        """Update the visual display of the stability level for the current card"""
        if self.current_factcard_id:
            query = "SELECT Stability, Difficulty FROM FactCards WHERE FactCardID = ?"
            result = self.fetch_query(query, (self.current_factcard_id,))
            
            if result and len(result) > 0:
                stability = result[0][0]
                difficulty = result[0][1]
                
                if stability is not None:
                    # Cap stability display at 100%
                    stability_percentage = min(100, int(stability))
                    
                    # Update the stability progress in the UI
                    self.mastery_level_label.config(text=f"Memory Strength: {stability_percentage}%")
                    
                    # Update progress bar
                    self.mastery_progress["value"] = stability_percentage
                    
                    # Change color based on stability level
                    if stability_percentage < 30:
                        self.mastery_level_label.config(fg=self.RED_COLOR)  # Red for low stability
                    elif stability_percentage < 70:
                        self.mastery_level_label.config(fg=self.YELLOW_COLOR)  # Yellow for medium stability
                    else:
                        self.mastery_level_label.config(fg=self.GREEN_COLOR)  # Green for high stability
                else:
                    # No stability data
                    self.mastery_level_label.config(text="Stability: N/A")
                    self.mastery_progress["value"] = 0
            else:
                # Error retrieving data
                self.mastery_level_label.config(text="Stability: Error")
                self.mastery_progress["value"] = 0
        else:
            # No card selected
            self.mastery_level_label.config(text="Stability: N/A")
            self.mastery_progress["value"] = 0
    
    def clear_status_after_delay(self, delay_ms=3000):
        """Clear the status message after a specified delay"""
        self.root.after(delay_ms, lambda: self.status_label.config(text=""))
    
    def fetch_due_factcard(self):
        """Fetch a fact card due for review"""
        category = self.category_var.get()
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Reset the show_answer state for new fact card
        self.show_answer = False
        
        # Get fact cards due for review today or earlier
        if category == "All Categories":
            query = """
                SELECT TOP 1 FactCardID, Question, Answer, NextReviewDate, CurrentInterval, Stability
                FROM FactCards
                WHERE NextReviewDate <= ?
                ORDER BY NextReviewDate, NEWID()
            """
            factcard = self.fetch_query(query, (current_date,))
        else:
            query = """
                SELECT TOP 1 f.FactCardID, f.Question, f.Answer, f.NextReviewDate, f.CurrentInterval, f.Stability
                FROM FactCards f
                JOIN Categories c ON f.CategoryID = c.CategoryID
                WHERE c.CategoryName = ? AND f.NextReviewDate <= ?
                ORDER BY f.NextReviewDate, NEWID()
            """
            factcard = self.fetch_query(query, (category, current_date))
        
        if factcard and len(factcard) > 0:
            # We have a fact card due for review
            factcard_id = factcard[0][0]
            question = factcard[0][1]
            self.current_factcard_id = factcard_id
            
            # Show the question
            self.show_review_buttons(True)
            self.show_answer_button.config(state="normal")
            return f"Question: {question}"
        else:
            # No fact cards due for review
            self.current_factcard_id = None
            next_date, count = self.get_next_review_info()
            self.show_review_buttons(False)
            self.show_answer_button.config(state="disabled")
            
            # Get the current category
            category = self.category_var.get()
            category_msg = f"for {category}" if category != "All Categories" else "for all Categories"
            
            if next_date:
                next_date_str = next_date.strftime('%Y-%m-%d') if isinstance(next_date, datetime) else next_date
                return f"No fact cards due for review today {category_msg}.\n\nNext review date: {next_date_str}\nFact cards due on that day: {count}"
            else:
                if category != "All Categories":
                    return f"No fact cards found {category_msg}. Add some fact cards first!"
                else:
                    return "No fact cards found. Add some fact cards first!"
    
    def load_next_factcard(self):
        """Load the next due fact card"""
        factcard_text = self.fetch_due_factcard()
        if factcard_text:
            self.factcard_label.config(text=factcard_text, font=(self.NORMAL_FONT[0], self.adjust_font_size(factcard_text)))
            self.update_stability_display()  # Update the stability display
        else:
            self.factcard_label.config(text="No fact cards found.", font=(self.NORMAL_FONT[0], 12))
            self.mastery_level_label.config(text="Stability: N/A")
            self.mastery_progress["value"] = 0
        self.update_due_count()
    
    def update_due_count(self):
        """Update the count of fact cards due today"""
        due_count = self.get_due_factcard_count()
        self.due_count_label.config(text=f"Due today: {due_count}")
    
    def show_review_buttons(self, show):
        """Show or hide the spaced repetition buttons"""
        state = "normal" if show else "disabled"
        self.again_button.config(state=state)
        self.hard_button.config(state=state)
        self.medium_button.config(state=state)
        self.easy_button.config(state=state)
        
        # Instead of disabling, completely hide or show the edit and delete buttons
        if show:
            # Show buttons if there's a fact card to review
            self.edit_icon_button.pack(side="left", padx=10)
            self.delete_icon_button.pack(side="left", padx=10)
        else:
            # Hide buttons if there's no fact card
            self.edit_icon_button.pack_forget()
            self.delete_icon_button.pack_forget()

    def update_factcard_schedule(self, rating_label):
        """Update the fact card's review schedule using FSRS"""
        if not self.current_factcard_id:
            return
        
        # FIXED: Map UI labels to FSRS v5 ratings (which are 1-based)
        rating_map = {"Again": 1, "Hard": 2, "Medium": 3, "Easy": 4}
        fsrs_rating = rating_map[rating_label]
        
        # Disable buttons immediately to prevent multiple clicks
        self.show_review_buttons(False)
        
        # 1. Get current card state
        query = """
            SELECT 
                Stability, Difficulty, State, NextReviewDate as due,
                DATEDIFF(day, LastReviewDate, GETDATE()) AS elapsed_days,
                CurrentInterval
            FROM FactCards
            WHERE FactCardID = ?
        """
        result = self.fetch_query(query, (self.current_factcard_id,))
        
        if not result or len(result) == 0:
            self.status_label.config(text="Error: Failed to retrieve card data", fg=self.RED_COLOR)
            self.clear_status_after_delay()
            return
        
        # Extract data from query result
        row = result[0]
        current_interval = row[5] or 1  # Current interval or default to 1
        
        # Prepare the row data for FSRS review
        db_row = {
            "stability": row[0],    # Stability
            "difficulty": row[1],   # Difficulty
            "state": row[2] or 2,   # State (default to 2=Review if NULL)
        }
        
        # Handle the due date - convert it to a proper datetime object
        due_date = row[3]
        if due_date:
            # If the due date is a string, convert it to datetime
            if isinstance(due_date, str):
                try:
                    # Try to parse the date string - adjust format as needed
                    due_date = datetime.strptime(due_date, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    try:
                        # Try another common format
                        due_date = datetime.strptime(due_date, '%Y-%m-%d')
                    except ValueError:
                        print(f"Could not parse due date: {due_date}")
                        # Use current date as fallback
                        due_date = datetime.now()
        
        db_row["due"] = due_date
        
        # 2. Log the review
        # Use comprehensive field list compatible with both schema versions
        log_success = self.execute_update("""
            INSERT INTO ReviewLogs (
                FactCardID, ReviewDate, 
                UserRating, Rating, 
                IntervalBeforeReview, Interval,
                StabilityBefore, DifficultyBefore
            )
            VALUES (?, GETDATE(), ?, ?, ?, ?, ?, ?)
        """, (
            self.current_factcard_id, 
            fsrs_rating, fsrs_rating,  # Store in both UserRating and Rating fields
            current_interval, current_interval,  # Store in both IntervalBeforeReview and Interval fields
            row[0] if row[0] is not None else 0.0,  # StabilityBefore from current card
            row[1] if row[1] is not None else 0.3   # DifficultyBefore from current card
        ))
        
        if not log_success:
            print(f"Warning: Failed to log review for card {self.current_factcard_id}")
        
        # 3. Calculate new schedule with FSRS
        try:
            # Get the updated fields from FSRS
            fsrs_result = self.fsrs_engine.review(db_row, fsrs_rating)
            
            # For UI display - use a simple linear calculation from stability
            # Standard FSRS doesn't have a mastery concept, so we derive it
            mastery_value = min(1.0, fsrs_result["stability"] / 100.0)
            
            # For debugging - print the values from FSRS that will be used to update the database
            print(f"FSRS Result: stability={fsrs_result['stability']}, " +
                  f"difficulty={fsrs_result['difficulty']}, " +
                  f"state={fsrs_result['state']}, " +
                  f"interval={fsrs_result['interval']}, " +
                  f"is_lapse={fsrs_result['is_lapse']}")
            
            # 4. Update the database - FIXED to use a parameterized date that SQL Server can handle properly
            update_success = self.execute_update(
                """
                UPDATE FactCards 
                SET Stability = ?, 
                    Difficulty = ?, 
                    State = ?,
                    NextReviewDate = DATEADD(day, ?, GETDATE()), 
                    CurrentInterval = ?, 
                    Mastery = ?,  
                    Lapses = Lapses + ?,
                    ViewCount = ViewCount + 1, 
                    LastReviewDate = GETDATE()
                WHERE FactCardID = ?
                """, 
                (
                    fsrs_result["stability"], 
                    fsrs_result["difficulty"],
                    fsrs_result["state"],
                    fsrs_result["interval"],  # Use interval directly for DATEADD
                    fsrs_result["interval"],
                    mastery_value,  
                    1 if fsrs_result["is_lapse"] else 0,
                    self.current_factcard_id
                )
            )
            
            if not update_success:
                self.status_label.config(text="Error updating card schedule", fg=self.RED_COLOR)
                self.clear_status_after_delay()
                return
                
            # 5. Show feedback to the user
            self._show_fsrs_schedule_feedback(rating_label, fsrs_result["interval"], fsrs_result["stability"])
            
        except Exception as e:
            print(f"FSRS scheduling error: {e}")
            self.status_label.config(text=f"Scheduling error: {str(e)[:50]}", fg=self.RED_COLOR)
            self.clear_status_after_delay()
            return
        
        # 6. Load the next fact card after a short delay
        self.root.after(1000, self.load_next_factcard)
        
    def _show_fsrs_schedule_feedback(self, rating, interval, stability):
        """Show feedback to the user about FSRS scheduling"""
        stability_percent = min(100, int(stability))
        
        # Customize feedback based on rating
        if rating == "Again":
            feedback_text = f"Card reset. Next review today. Stability: {stability_percent}%"
        elif rating == "Hard":
            feedback_text = f"Rated as {rating}. Next review in {interval} days. Stability: {stability_percent}%"
        elif rating == "Medium":
            feedback_text = f"Rated as Good. Next review in {interval} days. Stability: {stability_percent}%"
        else:  # Easy
            feedback_text = f"Rated as {rating}. Next review in {interval} days. Stability: {stability_percent}%"
        
        self.status_label.config(text=feedback_text, fg=self.STATUS_COLOR)
        
        # Schedule clearing the status after 3 seconds
        self.clear_status_after_delay(3000)
    
    def add_new_factcard(self):
        """Add a new fact card to the database"""
        # Create a popup window
        add_window = tk.Toplevel(self.root)
        add_window.title("Add New Fact Card")
        add_window.geometry(f"{self.POPUP_ADD_CARD_SIZE}{self.POPUP_POSITION}")
        add_window.configure(bg=self.BG_COLOR)
        
        # Get categories for dropdown
        categories = self.fetch_query("SELECT CategoryName FROM Categories WHERE IsActive = 1")
        category_names = [cat[0] for cat in categories] if categories else []
        
        # Create and place widgets
        tk.Label(add_window, text="Add New Fact Card", fg=self.TEXT_COLOR, bg=self.BG_COLOR, 
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
        
        # Question
        q_frame = tk.Frame(add_window, bg=self.BG_COLOR)
        q_frame.pack(fill="x", padx=20, pady=5)
        
        tk.Label(q_frame, text="Question:", fg=self.TEXT_COLOR, bg=self.BG_COLOR, 
                font=self.NORMAL_FONT).pack(side="top", anchor="w", padx=5)
        
        question_text = tk.Text(q_frame, height=4, width=40, font=self.NORMAL_FONT)
        question_text.pack(fill="x", padx=5, pady=5)
        
        # Answer
        a_frame = tk.Frame(add_window, bg=self.BG_COLOR)
        a_frame.pack(fill="x", padx=20, pady=5)
        
        tk.Label(a_frame, text="Answer:", fg=self.TEXT_COLOR, bg=self.BG_COLOR, 
                font=self.NORMAL_FONT).pack(side="top", anchor="w", padx=5)
        
        answer_text = tk.Text(a_frame, height=4, width=40, font=self.NORMAL_FONT)
        answer_text.pack(fill="x", padx=5, pady=5)
        
        def save_factcard():
            category = cat_var.get()
            question = question_text.get("1.0", "end-1c").strip()
            answer = answer_text.get("1.0", "end-1c").strip()
            
            if not question or not answer:
                self.status_label.config(text="Question and answer are required!", fg=self.RED_COLOR)
                self.clear_status_after_delay(3000)
                return
            
            # Get category ID
            cat_result = self.fetch_query("SELECT CategoryID FROM Categories WHERE CategoryName = ?", (category,))
            if not cat_result or len(cat_result) == 0:
                self.status_label.config(text="Category not found!", fg=self.RED_COLOR)
                self.clear_status_after_delay(3000)
                return
                
            category_id = cat_result[0][0]
            
            # Insert the new fact card - now including FSRS initial values
            success = self.execute_update(
                """
                INSERT INTO FactCards (
                    CategoryID, Question, Answer, NextReviewDate, CurrentInterval, 
                    Mastery, DateAdded, Stability, Difficulty, State, Lapses
                ) 
                VALUES (?, ?, ?, GETDATE(), 1, 0.0, GETDATE(), 0.0, 0.3, 1, 0)
                """, 
                (category_id, question, answer)
            )
            
            if success:
                add_window.destroy()
                self.status_label.config(text="New fact card added successfully!", fg=self.GREEN_COLOR)
                self.clear_status_after_delay(3000)
                self.update_factcard_count()
                self.update_due_count()
                # If no current card is shown, load the newly added card
                if self.current_factcard_id is None:
                    self.load_next_factcard()
            else:
                self.status_label.config(text="Error adding new fact card!", fg=self.RED_COLOR)
                self.clear_status_after_delay(3000)
        
        # Save button
        save_button = tk.Button(add_window, text="Save Fact Card", bg=self.GREEN_COLOR, fg=self.TEXT_COLOR, 
                              command=save_factcard, cursor="hand2", borderwidth=0, 
                              highlightthickness=0, padx=10, pady=5,
                              font=(self.NORMAL_FONT[0], self.NORMAL_FONT[1], 'bold'))
        save_button.pack(pady=20)
    
    def edit_current_factcard(self):
        """Edit the current fact card"""
        if not self.current_factcard_id:
            return
        
        # Get current fact card data
        query = """
        SELECT f.Question, f.Answer, c.CategoryName, f.Stability, f.Difficulty, f.State
        FROM FactCards f 
        JOIN Categories c ON f.CategoryID = c.CategoryID
        WHERE f.FactCardID = ?
        """
        result = self.fetch_query(query, (self.current_factcard_id,))
        
        if not result or len(result) == 0:
            self.status_label.config(text="Error: Could not retrieve fact card data", fg=self.RED_COLOR)
            self.clear_status_after_delay()
            return
            
        current_question, current_answer, current_category, current_stability, current_difficulty, current_state = result[0]
        
        # Create a popup window
        edit_window = tk.Toplevel(self.root)
        edit_window.title("Edit Fact Card")
        edit_window.geometry(f"{self.POPUP_EDIT_CARD_SIZE}{self.POPUP_POSITION}")
        edit_window.configure(bg=self.BG_COLOR)
        
        # Get categories for dropdown
        categories = self.fetch_query("SELECT CategoryName FROM Categories WHERE IsActive = 1")
        category_names = [cat[0] for cat in categories] if categories else []
        
        # Create and place widgets
        tk.Label(edit_window, text="Edit Fact Card", fg=self.TEXT_COLOR, bg=self.BG_COLOR, 
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
        
        # Question
        q_frame = tk.Frame(edit_window, bg=self.BG_COLOR)
        q_frame.pack(fill="x", padx=20, pady=5)
        
        tk.Label(q_frame, text="Question:", fg=self.TEXT_COLOR, bg=self.BG_COLOR, 
                font=self.NORMAL_FONT).pack(side="top", anchor="w", padx=5)
        
        question_text = tk.Text(q_frame, height=4, width=40, font=self.NORMAL_FONT)
        question_text.insert("1.0", current_question)
        question_text.pack(fill="x", padx=5, pady=5)
        
        # Answer
        a_frame = tk.Frame(edit_window, bg=self.BG_COLOR)
        a_frame.pack(fill="x", padx=20, pady=5)
        
        tk.Label(a_frame, text="Answer:", fg=self.TEXT_COLOR, bg=self.BG_COLOR, 
                font=self.NORMAL_FONT).pack(side="top", anchor="w", padx=5)
        
        answer_text = tk.Text(a_frame, height=4, width=40, font=self.NORMAL_FONT)
        answer_text.insert("1.0", current_answer)
        answer_text.pack(fill="x", padx=5, pady=5)
        
        # Stability level slider (instead of mastery)
        s_frame = tk.Frame(edit_window, bg=self.BG_COLOR)
        s_frame.pack(fill="x", padx=20, pady=5)
        
        # Use stability for display if available
        stability_value = 0.0
        if current_stability is not None:
            stability_value = min(100, current_stability) / 100  # Convert to 0-1 range for slider
        
        stability_percent = int(stability_value * 100)
        
        tk.Label(s_frame, text=f"Stability Level: {stability_percent}%", fg=self.TEXT_COLOR, bg=self.BG_COLOR, 
                font=self.NORMAL_FONT).pack(side="top", anchor="w", padx=5)
        
        stability_var = tk.DoubleVar(edit_window, value=stability_value)
        
        def update_stability_label(val):
            stability_val = int(float(val) * 100)
            s_frame.winfo_children()[0].config(text=f"Stability Level: {stability_val}%")
        
        stability_slider = ttk.Scale(s_frame, from_=0.0, to=1.0, orient="horizontal",
                                variable=stability_var, command=update_stability_label)
        stability_slider.pack(fill="x", padx=5, pady=5)
        
        # Add difficulty slider for FSRS
        d_frame = tk.Frame(edit_window, bg=self.BG_COLOR)
        d_frame.pack(fill="x", padx=20, pady=5)
        
        difficulty_value = current_difficulty or 0.3  # Default FSRS difficulty
        ease_value = 1 - difficulty_value  # Invert so higher = easier for UI
        ease_percent = int(ease_value * 100)
        
        tk.Label(d_frame, text=f"Ease Factor: {ease_percent}%", fg=self.TEXT_COLOR, bg=self.BG_COLOR, 
                font=self.NORMAL_FONT).pack(side="top", anchor="w", padx=5)
        
        difficulty_var = tk.DoubleVar(edit_window, value=ease_value)  # Invert for display
        
        def update_difficulty_label(val):
            ease_val = int(float(val) * 100)
            d_frame.winfo_children()[0].config(text=f"Ease Factor: {ease_val}%")
        
        difficulty_slider = ttk.Scale(d_frame, from_=0.0, to=1.0, orient="horizontal",
                                    variable=difficulty_var, command=update_difficulty_label)
        difficulty_slider.pack(fill="x", padx=5, pady=5)
        
        # Hidden state variable (removed from UI)
        state_var = tk.IntVar(edit_window, value=current_state or 2)  # Default to Review (2)
        
        def update_factcard():
            category = cat_var.get()
            question = question_text.get("1.0", "end-1c").strip()
            answer = answer_text.get("1.0", "end-1c").strip()
            stability = stability_var.get() * 100  # Convert back to 0-100 range
            difficulty = 1 - difficulty_var.get()   # Invert back
            state = state_var.get()
            
            if not question or not answer:
                self.status_label.config(text="Question and answer are required!", fg=self.RED_COLOR)
                self.clear_status_after_delay(3000)
                return
            
            # Get category ID
            cat_result = self.fetch_query("SELECT CategoryID FROM Categories WHERE CategoryName = ?", (category,))
            if not cat_result or len(cat_result) == 0:
                self.status_label.config(text="Category not found!", fg=self.RED_COLOR)
                self.clear_status_after_delay(3000)
                return
                
            category_id = cat_result[0][0]
            
            # Update the fact card including FSRS parameters
            success = self.execute_update(
                """
                    UPDATE FactCards 
                    SET CategoryID = ?, Question = ?, Answer = ?, 
                        Stability = ?, Difficulty = ?, State = ?,
                        Mastery = ?
                    WHERE FactCardID = ?
                    """, 
                    (
                        category_id, question, answer, 
                        stability, difficulty, state,
                        min(1.0, stability / 100.0),  # Keep mastery in sync with stability
                        self.current_factcard_id
                    )
            )
            
            if success:
                edit_window.destroy()
                self.status_label.config(text="Fact card updated successfully!", fg=self.GREEN_COLOR)
                self.clear_status_after_delay(3000)
                
                # Refresh the current card display
                if self.show_answer:
                    self.factcard_label.config(text=f"Answer: {answer}", font=(self.NORMAL_FONT[0], self.adjust_font_size(answer)))
                else:
                    self.factcard_label.config(text=f"Question: {question}", font=(self.NORMAL_FONT[0], self.adjust_font_size(question)))
                
                # Update stability display
                self.update_stability_display()
            else:
                self.status_label.config(text="Error updating fact card!", fg=self.RED_COLOR)
                self.clear_status_after_delay(3000)
        
        # Update button
        update_button = tk.Button(edit_window, text="Update Fact Card", bg=self.BLUE_COLOR, fg=self.TEXT_COLOR, 
                                command=update_factcard, cursor="hand2", borderwidth=0, 
                                highlightthickness=0, padx=10, pady=5,
                                font=(self.NORMAL_FONT[0], self.NORMAL_FONT[1], 'bold'))
        update_button.pack(pady=20)
    
    def delete_current_factcard(self):
        """Delete the current fact card"""
        if not self.current_factcard_id:
            return
        
        # Ask for confirmation
        if tk.messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this fact card?"):
            # Delete related review logs first
            self.execute_update("DELETE FROM ReviewLogs WHERE FactCardID = ?", (self.current_factcard_id,))
            
            # Delete the fact card
            success = self.execute_update("DELETE FROM FactCards WHERE FactCardID = ?", (self.current_factcard_id,))
            if success:
                self.status_label.config(text="Fact card deleted!", fg=self.RED_COLOR)
                self.clear_status_after_delay(3000)
                self.update_factcard_count()
                self.update_due_count()
                # Load the next fact card
                self.load_next_factcard()
            else:
                self.status_label.config(text="Error deleting fact card!", fg=self.RED_COLOR)
                self.clear_status_after_delay(3000)
    
    def manage_categories(self):
        """Open a window to manage categories"""
        # Create the category management window
        cat_window = self._create_category_window()
        
        # Create the UI components
        add_frame, new_cat_entry = self._create_add_category_ui(cat_window)
        list_frame, cat_listbox, refresh_category_list = self._create_category_list_ui(cat_window)
        self._create_category_action_buttons(cat_window, cat_listbox, refresh_category_list)
        
        # Initialize the category list
        refresh_category_list()
    
    def _create_category_window(self):
        """Create the main category management window"""
        cat_window = tk.Toplevel(self.root)
        cat_window.title("Manage Categories")
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
        
        return add_frame, new_cat_entry
    
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
            return True  # Indicate success for refresh_category_list callback
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
        cat_id = int(cat_text.split("ID: ")[1].strip(")"))
        
        # Get current name
        cat_result = self.fetch_query("SELECT CategoryName FROM Categories WHERE CategoryID = ?", (cat_id,))
        if not cat_result or len(cat_result) == 0:
            tk.messagebox.showinfo("Error", "Category not found!")
            return
            
        cat_name = cat_result[0][0]
        
        # Ask for new name
        new_name = simpledialog.askstring("Rename Category", f"New name for '{cat_name}':", initialvalue=cat_name)
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
        cat_id = int(cat_text.split("ID: ")[1].strip(")"))
        cat_name = cat_text.split(" (ID:")[0]
        
        # Check if category has fact cards
        card_count_result = self.fetch_query(
            "SELECT COUNT(*) FROM FactCards WHERE CategoryID = ?", 
            (cat_id,)
        )
        
        if not card_count_result:
            tk.messagebox.showinfo("Error", "Failed to check category content!")
            return
            
        card_count = card_count_result[0][0]
        
        if card_count > 0:
            if not tk.messagebox.askyesno(
                "Warning", 
                f"Category '{cat_name}' has {card_count} fact cards. " +
                "Deleting it will also delete all associated fact cards. Continue?"
            ):
                return
        
        # Delete the category and its fact cards
        success = self.execute_update("""
            BEGIN TRANSACTION;
            
            DELETE FROM FactCardTags WHERE FactCardID IN (SELECT FactCardID FROM FactCards WHERE CategoryID = ?);
            DELETE FROM ReviewLogs WHERE FactCardID IN (SELECT FactCardID FROM FactCards WHERE CategoryID = ?);
            DELETE FROM FactCards WHERE CategoryID = ?;
            DELETE FROM Categories WHERE CategoryID = ?;
            
            COMMIT TRANSACTION;
        """, (cat_id, cat_id, cat_id, cat_id))
        
        if success:
            refresh_callback()
            self.update_category_dropdown()
            self.update_factcard_count()
            self.update_due_count()
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
        self.load_next_factcard()
    
    def reset_to_welcome(self):
        """Reset to welcome screen"""
        self.factcard_label.config(text="Welcome to MemoDari!", 
                              font=(self.NORMAL_FONT[0], self.adjust_font_size("Welcome to MemoDari!")))
        self.status_label.config(text="")
        self.show_review_buttons(False)
        self.show_answer_button.config(state="disabled")
        self.mastery_level_label.config(text="Stability: N/A")
        self.mastery_progress["value"] = 0
        self.update_due_count()
    
    def show_home_page(self):
        """Show the home page with welcome message and start button"""
        self.is_home_page = True
        
        # Hide all fact card-related UI elements
        self.stats_frame.pack_forget()
        self.icon_buttons_frame.pack_forget()
        self.sr_frame.pack_forget()
        self.answer_mastery_frame.pack_forget()
        self.category_frame.pack_forget()
        
        # Update the welcome message
        self.factcard_label.config(text="Welcome to MemoDari!\n\nYour Personal Knowledge Companion", 
                             font=self.LARGE_FONT,
                             wraplength=450, justify="center")
        
        # Show the slogan
        self.slogan_label.config(text="Strengthen your knowledge one fact at a time")
        self.slogan_label.pack(side="top", pady=5)
        
        # Show the start learning button
        self.start_button.pack(pady=20)
        
        # Apply rounded corners again after UI changes
        self.root.update_idletasks()
        self.apply_rounded_corners()
    
    def start_learning(self):
        """Switch from home page to learning interface"""
        self.is_home_page = False
        
        # Hide home page elements
        self.slogan_label.pack_forget()
        self.start_button.pack_forget()
        
        # Show all fact card-related UI elements
        self.category_frame.pack(side="right", padx=5, pady=3)
        self.answer_mastery_frame.pack(side="top", fill="x", pady=0)
        self.sr_frame.pack(side="top", fill="x", pady=5)
        self.icon_buttons_frame.pack(side="top", fill="x", pady=5)
        self.stats_frame.pack(side="bottom", fill="x", padx=10, pady=3)
        
        # Load the first fact card
        self.load_next_factcard()
        
        # Apply rounded corners again after UI changes
        self.root.update_idletasks()
        self.apply_rounded_corners()
    
    def run(self):
        """Start the application mainloop"""
        self.root.mainloop()


# Usage example
if __name__ == "__main__":
    app = MemoDariApp()
    app.run()