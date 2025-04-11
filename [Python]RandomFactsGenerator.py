import tkinter as tk
from tkinter import ttk
import ctypes
from ctypes import wintypes
import requests
import webbrowser
import pyttsx3
from PIL import Image, ImageTk
import pyodbc
from datetime import datetime, timedelta

# Constants
CONN_STR = (
    r'DRIVER={SQL Server};'
    r'SERVER=GAURAVS_DESKTOP\SQLEXPRESS;'
    r'DATABASE=FactsGenerator;'
    r'Trusted_Connection=yes;'
)
MODES = ["API", "New Random", "Saved"]

# Global variables
fact_saved = False
x_window, y_window = 0, 0
current_fact_id = None
current_saved_fact_id = None

def apply_rounded_corners(root, radius):
    hWnd = wintypes.HWND(int(root.frame(), 16))
    hRgn = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, root.winfo_width(), root.winfo_height(), radius, radius)
    ctypes.windll.user32.SetWindowRgn(hWnd, hRgn, True)

def execute_query(query, params=None, fetch=True):
    with pyodbc.connect(CONN_STR) as conn:
        with conn.cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            if fetch:
                return cursor.fetchall()
            conn.commit()

def count_saved_facts():
    return execute_query("SELECT COUNT(*) FROM SavedFacts")[0][0]

def update_ui():
    update_coordinates()
    update_fact_count()
    root.after(100, update_ui)

def update_fact_count():
    num_facts = count_saved_facts()
    fact_count_label.config(text=f"Number of Saved Facts: {num_facts}")

def open_github(event=None):
    webbrowser.open('https://github.com/LordGauravB')

def on_press(event):
    global x_window, y_window
    x_window, y_window = event.x, event.y

def update_coordinates():
    x, y = root.winfo_x(), root.winfo_y()
    coordinate_label.config(text=f"Coordinates: {x}, {y}")

def on_drag(event):
    x, y = event.x_root - x_window, event.y_root - y_window
    root.geometry(f"+{x}+{y}")
    coordinate_label.config(text=f"Coordinates: {x}, {y}")

def set_static_position(event=None):
    root.geometry("-1930+7")
    update_coordinates()

def open_fact_file(event=None):
    facts = execute_query("SELECT TOP 10 f.FactText FROM SavedFacts sf JOIN Facts f ON sf.FactID = f.FactID ORDER BY sf.DateSaved DESC")
    if facts:
        fact_window = tk.Toplevel(root)
        fact_window.title("Recent Saved Facts")
        fact_window.geometry("400x300")
        for fact in facts:
            tk.Label(fact_window, text=fact[0], wraplength=380).pack(pady=5)
    else:
        save_status_label.config(text="No saved facts found.", fg="#ff0000")

def fetch_api_fact():
    global current_api_fact, fact_saved
    try:
        response = requests.get("https://uselessfacts.jsph.pl/random.json?language=en", timeout=10)
        if response.status_code == 200:
            fact_text = response.json()['text']
            current_api_fact = fact_text  # Store the API fact
            fact_saved = False  # Reset saved status
            return fact_text
        else:
            return "Failed to fetch a random fact from API"
    except requests.RequestException as e:
        return f"Error: {str(e)}"

def fetch_db_fact(category="Random"):
    global current_fact_id
    if category == "Random":
        query = "SELECT FactID, FactText FROM Facts ORDER BY NEWID()"
    else:
        query = """
        SELECT f.FactID, f.FactText 
        FROM Facts f
        JOIN Categories c ON f.CategoryID = c.CategoryID
        WHERE c.CategoryName = ?
        ORDER BY NEWID()
        """
    facts = execute_query(query, (category,) if category != "Random" else None)
    if facts:
        fact = facts[0]
        current_fact_id = fact[0]
        execute_query("UPDATE Facts SET ViewCount = ViewCount + 1 WHERE FactID = ?", (fact[0],), fetch=False)
        return fact[1]
    return "No fact found for the selected category."

def is_fact_saved(fact_id, fact_text=None):
    if fact_id:
        query = "SELECT COUNT(*) FROM SavedFacts WHERE FactID = ?"
        result = execute_query(query, (fact_id,))
        return result[0][0] > 0
    elif fact_text:
        query = """
        SELECT COUNT(*) 
        FROM SavedFacts sf
        JOIN Facts f ON sf.FactID = f.FactID
        WHERE f.FactText = ?
        """
        result = execute_query(query, (fact_text,))
        return result[0][0] > 0
    return False

def update_star_icon():
    global fact_saved
    current_mode = mode_var.get()
    current_fact = fact_label.cget("text")
    
    if (current_mode == "Saved" or
        current_fact == "Welcome to Fact Generator!" or
        current_fact.startswith("No fact found")):
        star_button.config(image=black_star_icon)
    elif current_mode == "API":
        fact_saved = is_fact_saved(None, current_fact)
        if fact_saved:
            star_button.config(image=gold_star_icon)
        else:
            star_button.config(image=white_star_icon)
    elif current_fact_id:
        fact_saved = is_fact_saved(current_fact_id)
        if fact_saved:
            star_button.config(image=gold_star_icon)
        else:
            star_button.config(image=white_star_icon)
    else:
        star_button.config(image=white_star_icon)

def toggle_save_fact():
    global fact_saved, current_fact_id, current_api_fact
    current_mode = mode_var.get()
    current_fact = fact_label.cget("text")
    
    if (current_mode == "Saved" or
        current_fact == "Welcome to Fact Generator!" or
        current_fact.startswith("No fact found")):
        return  # Do nothing in these cases
    
    if not fact_saved:
        if current_mode == "API" and current_api_fact:
            # For new API facts that aren't in the database yet
            api_category_id = execute_query("SELECT CategoryID FROM Categories WHERE CategoryName = 'API'")[0][0]
            current_fact_id = execute_query(
                "INSERT INTO Facts (FactText, CategoryID, IsVerified) OUTPUT INSERTED.FactID VALUES (?, ?, 0)",
                (current_api_fact, api_category_id)
            )[0][0]
        elif not current_fact_id:
            # For other modes, if somehow the fact isn't in the database (shouldn't happen, but just in case)
            return
        
        # Insert into SavedFacts
        execute_query("INSERT INTO SavedFacts (FactID, NextReviewDate, CurrentInterval) VALUES (?, GETDATE(), 1)", 
                     (current_fact_id,), fetch=False)
        
        # Call the stored procedure to populate tags
        execute_query("EXEC AutoPopulateSpecificFactTags @FactID=?", (current_fact_id,), fetch=False)
        
        save_status_label.config(text="Fact Saved!", fg="#b66d20")
        fact_saved = True
    else:
        if current_mode == "API":
            # Use a single query to delete from all related tables for API mode
            delete_query = """
            BEGIN TRANSACTION;
            
            DECLARE @fact_id INT;
            SELECT @fact_id = FactID FROM Facts WHERE FactText = ?;
            
            IF @fact_id IS NOT NULL
            BEGIN
                DELETE FROM FactTags WHERE FactID = @fact_id;
                DELETE FROM SavedFacts WHERE FactID = @fact_id;
                DELETE FROM Facts WHERE FactID = @fact_id;
            END
            
            COMMIT TRANSACTION;
            """
            execute_query(delete_query, (current_fact,), fetch=False)
            current_fact_id = None  # Reset current_fact_id after deletion
        else:
            # For other modes, only delete from SavedFacts
            execute_query("DELETE FROM SavedFacts WHERE FactID = ?", (current_fact_id,), fetch=False)
        
        save_status_label.config(text="Fact Unsaved!", fg="#b66d20")
        fact_saved = False
    
    update_star_icon()
    update_fact_count()

def get_next_review_info():
    """
    Get information about the next review date and count of facts due on that date.
    This version first retrieves the minimum (earliest) NextReviewDate that is greater than the current date,
    then counts only the facts that have that exact NextReviewDate.
    """
    current_date = datetime.now().strftime('%Y-%m-%d')
    category = category_var.get()
    
    if category == "Random":
        query_min = """
            SELECT MIN(NextReviewDate)
            FROM SavedFacts 
            WHERE NextReviewDate > ?
        """
        result = execute_query(query_min, (current_date,))
    else:
        query_min = """
            SELECT MIN(sf.NextReviewDate)
            FROM SavedFacts sf
            JOIN Facts f ON sf.FactID = f.FactID
            JOIN Categories c ON f.CategoryID = c.CategoryID
            WHERE sf.NextReviewDate > ? AND c.CategoryName = ?
        """
        result = execute_query(query_min, (current_date, category))
    
    if result and result[0][0]:
        next_date = result[0][0]
        # Count only the facts due exactly on the minimum next_date
        if category == "Random":
            query_count = """
                SELECT COUNT(*)
                FROM SavedFacts 
                WHERE NextReviewDate = ?
            """
            count_result = execute_query(query_count, (next_date,))
        else:
            query_count = """
                SELECT COUNT(*)
                FROM SavedFacts sf
                JOIN Facts f ON sf.FactID = f.FactID
                JOIN Categories c ON f.CategoryID = c.CategoryID
                WHERE sf.NextReviewDate = ? AND c.CategoryName = ?
            """
            count_result = execute_query(query_count, (next_date, category))
        count = count_result[0][0] if count_result else 0
        return next_date, count
    return None, 0

def hide_review_buttons():
    """Disable only the spaced repetition buttons (do not disable the 'Generate/Next Fact' button)"""
    hard_button.config(state="disabled")
    medium_button.config(state="disabled")
    easy_button.config(state="disabled")

def show_review_buttons():
    """Enable only the spaced repetition buttons (do not affect the 'Generate/Next Fact' button)"""
    hard_button.config(state="normal")
    medium_button.config(state="normal")
    easy_button.config(state="normal")

def fetch_saved_fact():
    """Fetch a fact due for review, or display next review date if none due"""
    global current_saved_fact_id
    category = category_var.get()
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    # Query for facts due today or overdue
    if category == "Random":
        query = """
            SELECT TOP 1 sf.SavedFactID, f.FactText, sf.NextReviewDate, sf.CurrentInterval
            FROM SavedFacts sf 
            JOIN Facts f ON sf.FactID = f.FactID 
            WHERE sf.NextReviewDate <= ?
            ORDER BY sf.NextReviewDate, NEWID()
        """
        fact = execute_query(query, (current_date,))
    else:
        query = """
            SELECT TOP 1 sf.SavedFactID, f.FactText, sf.NextReviewDate, sf.CurrentInterval
            FROM SavedFacts sf 
            JOIN Facts f ON sf.FactID = f.FactID 
            JOIN Categories c ON f.CategoryID = c.CategoryID
            WHERE c.CategoryName = ? AND sf.NextReviewDate <= ?
            ORDER BY sf.NextReviewDate, NEWID()
        """
        fact = execute_query(query, (category, current_date))
    
    if fact:
        # We have a fact due for review
        current_saved_fact_id, fact_text, next_review, interval = fact[0]
        update_review_info(next_review, interval)
        show_review_buttons()
        return fact_text
    else:
        # No facts due for review
        current_saved_fact_id = None
        next_date, count = get_next_review_info()
        hide_review_buttons()
        
        if next_date:
            next_date_str = next_date.strftime('%Y-%m-%d') if isinstance(next_date, datetime) else next_date
            review_info_label.config(text=f"No facts due today. Next review: {next_date_str} ({count} facts)")
            return f"No facts due for review today.\n\nNext review date: {next_date_str}\nFacts due on that day: {count}"
        else:
            review_info_label.config(text="No facts saved for review.")
            return "No facts saved for review. Add some facts first!"

def generate_new_fact():
    global fact_saved, current_fact_id, current_api_fact
    current_mode = mode_var.get()
    current_category = category_var.get()
    
    # Clear existing fact
    fact_label.config(text="")
    save_status_label.config(text="")
    
    if current_mode == "API":
        new_fact_text = fetch_api_fact()
        current_fact_id = None
        fact_saved = False
        hide_spaced_repetition_frame()
    elif current_mode == "New Random":
        new_fact_text = fetch_db_fact(current_category)
        fact_saved = is_fact_saved(current_fact_id)
        hide_spaced_repetition_frame()
    else:  # Saved mode
        new_fact_text = fetch_saved_fact()
        fact_saved = True
        show_spaced_repetition_frame()
        
        # For Saved mode, check if we have a current fact_id to determine if buttons should be shown
        if current_saved_fact_id is None:
            hide_review_buttons()
        else:
            show_review_buttons()

    if new_fact_text:
        fact_label.config(text=new_fact_text, font=("Trebuchet MS", adjust_font_size(new_fact_text)))
    else:
        fact_label.config(text="No fact found. Try a different category or mode.", font=("Trebuchet MS", 12))
    
    update_star_icon()
    root.update_idletasks()

def load_categories(mode):
    global CATEGORIES
    if mode == "New Random":
        query = "SELECT DISTINCT CategoryName FROM Categories WHERE IsActive = 1"
    elif mode == "Saved":
        query = """
        SELECT DISTINCT c.CategoryName
        FROM SavedFacts sf
        JOIN Facts f ON sf.FactID = f.FactID
        JOIN Categories c ON f.CategoryID = c.CategoryID
        WHERE c.IsActive = 1
        """
    else:  # API mode
        CATEGORIES = ["API"]
        return
    
    categories = execute_query(query)
    CATEGORIES = [category[0] for category in categories] if categories else ["No Categories Available"]
    CATEGORIES.insert(0, "Random")  # Add "Random" as the first option

def adjust_font_size(text):
    return max(8, min(13, int(13 - (len(text.split()) - 15) * 0.2)))

def speak_fact():
    engine = pyttsx3.init()
    engine.say(fact_label.cget("text"))
    engine.runAndWait()

def create_button(parent, text, command, bg='#007bff', side='left'):
    button = tk.Button(parent, text=text, bg=bg, fg="white", command=command, 
                     cursor="hand2", borderwidth=0, highlightthickness=0, padx=10, pady=5)
    button.pack(side=side, padx=10, pady=0.5)
    return button

global generate_button


def create_label(parent, text, fg="white", cursor=None, font=("Trebuchet MS", 7), side='left'):
    label = tk.Label(parent, text=text, fg=fg, bg="#1e1e1e", font=font)
    if cursor:
        label.configure(cursor=cursor)
    label.pack(side=side)
    return label

def update_category_dropdown(event=None):
    current_mode = mode_var.get()
    load_categories(current_mode)
    
    if current_mode == "API":
        category_var.set("API")
        category_dropdown.config(state="disabled")
    else:
        category_dropdown['values'] = CATEGORIES
        category_var.set("Random")
        category_dropdown.config(state="readonly")

def toggle_mode(event=None):
    global generate_button
    current_index = MODES.index(mode_var.get())
    next_mode = MODES[(current_index + 1) % len(MODES)]
    
    # Immediately hide all elements
    fact_label.pack_forget()
    spaced_repetition_frame.pack_forget()
    
    mode_var.set(next_mode)
    mode_button.config(text=f"Mode: {next_mode}")
    
    # Generate new fact
    generate_new_fact()
    # Force update
    root.update_idletasks()
    
    # Update category dropdown
    update_category_dropdown()
    
    # Show elements based on new mode
    fact_label.pack(side="top", fill="both", expand=True)
    if next_mode == "Saved":
        show_spaced_repetition_frame()
        # Hide the Generate/Next Fact button in Saved mode
        generate_button.pack_forget()
    else:
        # Show the Generate/Next Fact button in other modes
        generate_button.pack(side='left', padx=10, pady=0.5)
        root.geometry("400x270")
    
    root.after(10, lambda: apply_rounded_corners(root, 15))

def show_spaced_repetition_frame():
    """Show the spaced repetition frame but don't automatically show buttons"""
    spaced_repetition_frame.pack(side="bottom", fill="x", padx=10, pady=5)
    root.geometry("400x350")
    
    # Only enable buttons if there's a current fact to review
    if current_saved_fact_id is not None:
        show_review_buttons()
    else:
        hide_review_buttons()

def hide_spaced_repetition_frame():
    """Hide the entire spaced repetition frame"""
    spaced_repetition_frame.pack_forget()
    root.geometry("400x270")
    root.update_idletasks()
    apply_rounded_corners(root, 15)

def reset_to_welcome():
    fact_label.config(text="Welcome to Fact Generator!", 
                      font=("Trebuchet MS", adjust_font_size("Welcome to Fact Generator!")))
    save_status_label.config(text="")
    update_star_icon()
    mode_var.set("New Random")  # Reset to default mode
    category_var.set("Random")  # Reset to default category
    update_category_dropdown()
    hide_spaced_repetition_frame()  # Hide spaced repetition frame on welcome screen

def update_review_info(next_review_date, interval):
    """Updates the next review date information"""
    if isinstance(next_review_date, str):
        try:
            next_review_date = datetime.strptime(next_review_date, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            try:
                next_review_date = datetime.strptime(next_review_date, '%Y-%m-%d')
            except ValueError:
                next_review_date = datetime.now()
    
    current_date = datetime.now()
    days_until_review = (next_review_date - current_date).days if next_review_date > current_date else 0
    
    if days_until_review <= 0:
        review_status = "Due today"
    else:
        review_status = f"Next review in {days_until_review} days"
    
    review_info_label.config(text=f"Status: {review_status} (Interval: {interval} days)")

def calculate_next_interval(current_interval, difficulty):
    """Calculate the next interval based on difficulty rating"""
    if difficulty == "Hard":
        return max(1, current_interval)  # Reset to 1 or keep current interval
    elif difficulty == "Medium":
        return current_interval * 1.5  # Increase by 50%
    else:  # Easy
        return current_interval * 2.5  # Increase by 150%

def update_fact_schedule(difficulty):
    """Updates the fact's review schedule based on difficulty rating"""
    global current_saved_fact_id
    if current_saved_fact_id:
        # Get current interval
        current_interval = execute_query(
            "SELECT CurrentInterval FROM SavedFacts WHERE SavedFactID = ?", 
            (current_saved_fact_id,)
        )[0][0]
        
        # Calculate new interval
        new_interval = int(calculate_next_interval(current_interval, difficulty))
        
        # Calculate next review date
        if difficulty == "Hard":
            # For Hard difficulty, keep the due date as today
            next_review_date = datetime.now().strftime('%Y-%m-%d')
            feedback_text = f"Rated as {difficulty}. Next review today."
        else:
            # For Medium and Easy, use the calculated interval
            next_review_date = (datetime.now() + timedelta(days=new_interval)).strftime('%Y-%m-%d')
            feedback_text = f"Rated as {difficulty}. Next review in {new_interval} days."
        
        # Update the database
        execute_query(
            """
            UPDATE SavedFacts 
            SET NextReviewDate = ?, CurrentInterval = ? 
            WHERE SavedFactID = ?
            """, 
            (next_review_date, new_interval, current_saved_fact_id), 
            fetch=False
        )
        
        # Show feedback
        save_status_label.config(
            text=feedback_text, 
            fg="#b66d20"
        )
        
        # Generate the next fact
        generate_new_fact()

def on_hard_click():
    update_fact_schedule("Hard")
    # Explicitly move to next fact
    root.after(100, generate_new_fact)

def on_medium_click():
    update_fact_schedule("Medium")
    # Explicitly move to next fact
    root.after(100, generate_new_fact)

def on_easy_click():
    update_fact_schedule("Easy")
    # Explicitly move to next fact
    root.after(100, generate_new_fact)

# Main window setup
root = tk.Tk()
root.geometry("400x270")
root.overrideredirect(True)
root.configure(bg='#1e1e1e')

# Load icons
white_star_icon = ImageTk.PhotoImage(Image.open("C:/Users/gaura/OneDrive/PC-Desktop/GitHubDesktop/Random-Facts-Generator/Resources/Images/White-Star.png").resize((20, 20), Image.Resampling.LANCZOS))
gold_star_icon = ImageTk.PhotoImage(Image.open("C:/Users/gaura/OneDrive/PC-Desktop/GitHubDesktop/Random-Facts-Generator/Resources/Images/Gold-Star.png").resize((20, 20), Image.Resampling.LANCZOS))
black_star_icon = ImageTk.PhotoImage(Image.open("C:/Users/gaura/OneDrive/PC-Desktop/GitHubDesktop/Random-Facts-Generator/Resources/Images/Black-Star.png").resize((20, 20), Image.Resampling.LANCZOS))
home_icon = ImageTk.PhotoImage(Image.open("C:/Users/gaura/OneDrive/PC-Desktop/GitHubDesktop/Random-Facts-Generator/Resources/Images/home.png").resize((20, 20), Image.Resampling.LANCZOS))
speaker_icon = ImageTk.PhotoImage(Image.open("C:/Users/gaura/OneDrive/PC-Desktop/GitHubDesktop/Random-Facts-Generator/Resources/Images/speaker_icon.png").resize((20, 20), Image.Resampling.LANCZOS))

# Title bar
title_bar = tk.Frame(root, bg='#000000', height=30, relief='raised')
title_bar.pack(side="top", fill="x")
title_bar.bind("<Button-1>", on_press)
title_bar.bind("<B1-Motion>", on_drag)

tk.Label(title_bar, text="Facts", fg="white", bg='#000000', font=("Trebuchet MS", 12, 'bold')).pack(side="left", padx=5, pady=5)

# Mode button and category dropdown
mode_var = tk.StringVar(root, value=MODES[1])
mode_button = tk.Button(title_bar, text=f"Mode: {mode_var.get()}", bg='#2196F3', fg="white", command=toggle_mode, 
                        cursor="hand2", borderwidth=0, highlightthickness=0, padx=5, pady=2,
                        font=("Trebuchet MS", 8, 'bold'))
mode_button.pack(side="right", padx=5, pady=3)

category_frame = tk.Frame(title_bar, bg='#2196F3')
category_frame.pack(side="right", padx=5, pady=3)

category_var = tk.StringVar(root, value="Random")
category_dropdown = ttk.Combobox(category_frame, textvariable=category_var, state="readonly", width=15)
category_dropdown.bind("<<ComboboxSelected>>", lambda event: generate_new_fact())
category_dropdown.pack()

# Fact display
fact_frame = tk.Frame(root, bg="#1e1e1e")
fact_frame.pack(side="top", fill="both", expand=True)

fact_label = tk.Label(fact_frame, text="Welcome to Fact Generator!", fg="white", bg="#1e1e1e", 
                      font=("Trebuchet MS", adjust_font_size("Welcome to Fact Generator!")), wraplength=350)
fact_label.pack(side="top", fill="both", expand=True)

# Star button
star_button = tk.Button(fact_frame, image=white_star_icon, bg='#1e1e1e', command=toggle_save_fact, 
                        cursor="hand2", borderwidth=0, highlightthickness=0)
star_button.place(relx=1.0, rely=0, anchor="ne", x=-30, y=5)

# Speaker button
speaker_button = tk.Button(fact_frame, image=speaker_icon, bg='#1e1e1e', command=speak_fact, 
                           cursor="hand2", borderwidth=0, highlightthickness=0)
speaker_button.image = speaker_icon
speaker_button.place(relx=1.0, rely=0, anchor="ne", x=-5, y=5)

# Home button (repositioned)
home_button = tk.Button(fact_frame, image=home_icon, bg='#1e1e1e', bd=0, highlightthickness=0, 
                        cursor="hand2", activebackground='#1e1e1e', command=reset_to_welcome)
home_button.place(relx=0, rely=0, anchor="nw", x=5, y=5)

# Bottom frame
bottom_frame = tk.Frame(root, bg="#1e1e1e")
bottom_frame.pack(side="bottom", fill="x", padx=10, pady=0)

create_label(bottom_frame, "Created by - Gaurav Bhandari", cursor="hand2", side='right').bind("<Button-1>", open_github)
coordinate_label = create_label(bottom_frame, "Coordinates: ", side='right')
coordinate_label.pack_configure(padx=20)

fact_count_label = create_label(bottom_frame, "Number of Saved Facts: 0", cursor="hand2", side='left')
fact_count_label.bind("<Button-1>", open_fact_file)

# Control frame
control_frame = tk.Frame(root, bg="#1e1e1e")
control_frame.pack(side="bottom", fill="x")

button_frame = tk.Frame(control_frame, bg="#1e1e1e")
button_frame.pack(expand=True)

generate_button = create_button(button_frame, "Generate/Next Fact", generate_new_fact, bg='#b66d20')

save_status_label = create_label(control_frame, "", fg="#b66d20", font=("Trebuchet MS", 10), side='bottom')

# Spaced Repetition frame (replacing mastery frame)
spaced_repetition_frame = tk.Frame(root, bg="#1e1e1e")

# Create a sub-frame for the buttons
sr_button_frame = tk.Frame(spaced_repetition_frame, bg="#1e1e1e")
sr_button_frame.pack(side="top", fill="x", expand=True)

# Update the buttons for spaced repetition
hard_button = tk.Button(sr_button_frame, text="Hard", command=on_hard_click, bg='#F44336', fg="white", 
                      cursor="hand2", borderwidth=0, highlightthickness=0, padx=10, pady=5)
hard_button.pack(side="left", expand=True, fill="x", padx=(0, 5))

medium_button = tk.Button(sr_button_frame, text="Medium", command=on_medium_click, bg='#FFC107', fg="white", 
                        cursor="hand2", borderwidth=0, highlightthickness=0, padx=10, pady=5)
medium_button.pack(side="left", expand=True, fill="x", padx=(0, 5))

easy_button = tk.Button(sr_button_frame, text="Easy", command=on_easy_click, bg='#4CAF50', fg="white", 
                       cursor="hand2", borderwidth=0, highlightthickness=0, padx=10, pady=5)
easy_button.pack(side="left", expand=True, fill="x")

# Review information label
review_info_label = tk.Label(spaced_repetition_frame, text="Status: Due today (Interval: 1 day)", 
                            fg="white", bg="#1e1e1e", font=("Trebuchet MS", 10))
review_info_label.pack(side="top", pady=(5, 0))

# Set initial transparency
root.attributes('-alpha', 0.65)

# Bind focus events to the root window
root.bind("<FocusIn>", lambda event: root.attributes('-alpha', 1.0))
root.bind("<FocusOut>", lambda event: root.attributes('-alpha', 0.65))

# Final setup
root.update_idletasks()
apply_rounded_corners(root, 15)
set_static_position()
root.bind("<s>", set_static_position)
update_star_icon()
update_category_dropdown()
hide_spaced_repetition_frame()  # Initially hide the spaced repetition frame
root.after(100, update_ui)
root.mainloop()
