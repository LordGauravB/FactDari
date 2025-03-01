import tkinter as tk
from tkinter import ttk
import ctypes
from ctypes import wintypes
import requests
import webbrowser
import os
import random
import pyttsx3
from PIL import Image, ImageTk
import pyodbc

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

def on_focus_in(event):
    root.attributes('-alpha', 1.0)

def on_focus_out(event):
    root.attributes('-alpha', 0.65)

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

def update_ui_elements():
    update_coordinates()
    update_fact_count()

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
    update_coordinates()

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
        execute_query("INSERT INTO SavedFacts (FactID) VALUES (?)", (current_fact_id,), fetch=False)
        
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
        
        save_status_label.config(text="Fact Unsaved", fg="#b66d20")
        fact_saved = False
    
    update_star_icon()
    update_fact_count()

def fetch_saved_fact():
    category = category_var.get()
    if category == "Random":
        query = """
            SELECT TOP 1 f.FactText 
            FROM SavedFacts sf 
            JOIN Facts f ON sf.FactID = f.FactID 
            ORDER BY NEWID()
        """
        fact = execute_query(query)
    else:
        query = """
            SELECT TOP 1 f.FactText 
            FROM SavedFacts sf 
            JOIN Facts f ON sf.FactID = f.FactID 
            JOIN Categories c ON f.CategoryID = c.CategoryID
            WHERE c.CategoryName = ?
            ORDER BY NEWID()
        """
        fact = execute_query(query, (category,))
    
    return fact[0][0] if fact else "No saved facts found for the selected category."

def generate_new_fact():
    global fact_saved, current_fact_id, current_api_fact
    current_mode = mode_var.get()
    current_category = category_var.get()
    
    if current_mode == "API":
        new_fact_text = fetch_api_fact()
        current_fact_id = None  # Reset current_fact_id for API facts
        fact_saved = False
    elif current_mode == "New Random":
        new_fact_text = fetch_db_fact(current_category)
        fact_saved = is_fact_saved(current_fact_id)
    else:  # Saved mode
        new_fact_text = fetch_saved_fact()
        fact_saved = True

    if new_fact_text:
        fact_label.config(text=new_fact_text, font=("Trebuchet MS", adjust_font_size(new_fact_text)))
        fade_out_saved_message()
    else:
        fact_label.config(text="No fact found. Try a different category or mode.", font=("Trebuchet MS", 12))
    
    update_star_icon()

def toggle_mode(event=None):
    current_index = MODES.index(mode_var.get())
    next_mode = MODES[(current_index + 1) % len(MODES)]
    mode_var.set(next_mode)
    mode_button.config(text=f"Mode: {next_mode}")
    update_category_dropdown()
    generate_new_fact()

    if next_mode == "API":
        category_var.set("Unavailable")
        category_dropdown.config(state="disabled")
    else:
        load_categories(next_mode)
        category_var.set("Random")
        category_dropdown.config(state="readonly")

    generate_new_fact()
    update_category_dropdown()

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

def fade_out_saved_message():
    save_status_label.config(text="", fg="#1e1e1e")

def adjust_font_size(text):
    return max(8, min(13, int(13 - (len(text.split()) - 15) * 0.2)))

def speak_fact():
    engine = pyttsx3.init()
    engine.say(fact_label.cget("text"))
    engine.runAndWait()

def create_button(parent, text, command, bg='#007bff', side='left'):
    return tk.Button(parent, text=text, bg=bg, fg="white", command=command, 
                     cursor="hand2", borderwidth=0, highlightthickness=0, padx=10, pady=5).pack(side=side, padx=10, pady=0.5)

def create_label(parent, text, fg="white", cursor=None, font=("Trebuchet MS", 7), side='left'):
    label = tk.Label(parent, text=text, fg=fg, bg="#1e1e1e", font=font)
    if cursor:
        label.configure(cursor=cursor)
    label.pack(side=side)
    return label


def create_button(parent, text, command, bg='#007bff', side='left'):
    return tk.Button(parent, text=text, bg=bg, fg="white", command=command, 
                     cursor="hand2", borderwidth=0, highlightthickness=0, padx=10, pady=5).pack(side=side, padx=10, pady=0.5)

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

# Assume 'root' is your main Tkinter window
root = tk.Tk()
root.geometry("400x270")
root.overrideredirect(True)
root.configure(bg='#1e1e1e')

# Load star icons
white_star_icon = ImageTk.PhotoImage(Image.open("C:/Users/gaura/OneDrive/PC-Desktop/PythonRunningApps/RandomFactsGenerator/Resources/White-Star.png").resize((20, 20), Image.Resampling.LANCZOS))
gold_star_icon = ImageTk.PhotoImage(Image.open("C:/Users/gaura/OneDrive/PC-Desktop/PythonRunningApps/RandomFactsGenerator/Resources/Gold-Star.png").resize((20, 20), Image.Resampling.LANCZOS))
black_star_icon = ImageTk.PhotoImage(Image.open("C:/Users/gaura/OneDrive/PC-Desktop/PythonRunningApps/RandomFactsGenerator/Resources/Black-Star.png").resize((20, 20), Image.Resampling.LANCZOS))

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


# In the UI setup section, replace the category_dropdown creation with:
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
speaker_icon = ImageTk.PhotoImage(Image.open("C:/Users/gaura/OneDrive/PC-Desktop/PythonRunningApps/RandomFactsGenerator/Resources/speaker_icon.png").resize((20, 20), Image.Resampling.LANCZOS))
speaker_button = tk.Button(fact_frame, image=speaker_icon, bg='#1e1e1e', command=speak_fact, 
                           cursor="hand2", borderwidth=0, highlightthickness=0)
speaker_button.image = speaker_icon
speaker_button.place(relx=1.0, rely=0, anchor="ne", x=-5, y=5)

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

create_button(button_frame, "Generate/Next Fact", generate_new_fact, bg='#b66d20')

save_status_label = create_label(control_frame, "", fg="#b66d20", font=("Trebuchet MS", 10), side='bottom')

# Set initial transparency
root.attributes('-alpha', 0.65)

# Bind focus events to the root window
root.bind("<FocusIn>", on_focus_in)
root.bind("<FocusOut>", on_focus_out)

# Final setup
root.update_idletasks()
apply_rounded_corners(root, 15)
set_static_position()
root.bind("<s>", set_static_position)
update_ui_elements()
update_star_icon()
update_category_dropdown()

root.mainloop()