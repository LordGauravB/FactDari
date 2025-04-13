import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import ctypes
from ctypes import wintypes
import pyodbc
from datetime import datetime, timedelta
import pyttsx3
from PIL import Image, ImageTk
import random

# Constants
CONN_STR = (
    r'DRIVER={SQL Server};'
    r'SERVER=GAURAVS_DESKTOP\SQLEXPRESS;'
    r'DATABASE=FactDari;'
    r'Trusted_Connection=yes;'
)

# Global variables
x_window, y_window = 0, 0
current_factcard_id = None
show_answer = False
is_home_page = True  # New flag to track if we're on the home page

def apply_rounded_corners(root, radius):
    """Apply rounded corners to the window"""
    hWnd = wintypes.HWND(int(root.frame(), 16))
    hRgn = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, root.winfo_width(), root.winfo_height(), radius, radius)
    ctypes.windll.user32.SetWindowRgn(hWnd, hRgn, True)

def execute_query(query, params=None, fetch=True):
    """Execute a SQL query with optional parameters"""
    with pyodbc.connect(CONN_STR) as conn:
        with conn.cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            if fetch:
                return cursor.fetchall()
            conn.commit()

def count_factcards():
    """Count total fact cards in the database"""
    return execute_query("SELECT COUNT(*) FROM FactCards")[0][0]

def update_ui():
    """Update UI elements periodically"""
    update_coordinates()
    if not is_home_page:
        update_factcard_count()
    root.after(100, update_ui)

def update_factcard_count():
    """Update the fact card count display"""
    num_factcards = count_factcards()
    factcard_count_label.config(text=f"Total Fact Cards: {num_factcards}")

def on_press(event):
    """Handle mouse press on title bar for dragging"""
    global x_window, y_window
    x_window, y_window = event.x, event.y

def update_coordinates():
    """Update the coordinate display"""
    x, y = root.winfo_x(), root.winfo_y()
    coordinate_label.config(text=f"Coordinates: {x}, {y}")

def on_drag(event):
    """Handle window dragging"""
    x, y = event.x_root - x_window, event.y_root - y_window
    root.geometry(f"+{x}+{y}")
    coordinate_label.config(text=f"Coordinates: {x}, {y}")

def set_static_position(event=None):
    """Set window to a static position"""
    root.geometry("-1930+7")
    update_coordinates()

def speak_text():
    """Speak the current fact card text"""
    text = factcard_label.cget("text")
    # Remove "Question: " or "Answer: " prefix if present
    if text.startswith("Question: "):
        text = text[10:]
    elif text.startswith("Answer: "):
        text = text[8:]
    
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

def get_due_factcard_count():
    """Get count of fact cards due for review today"""
    current_date = datetime.now().strftime('%Y-%m-%d')
    category = category_var.get()
    
    if category == "All Categories":
        query = "SELECT COUNT(*) FROM FactCards WHERE NextReviewDate <= ?"
        result = execute_query(query, (current_date,))
    else:
        query = """
        SELECT COUNT(*) 
        FROM FactCards f
        JOIN Categories c ON f.CategoryID = c.CategoryID
        WHERE f.NextReviewDate <= ? AND c.CategoryName = ?
        """
        result = execute_query(query, (current_date, category))
    
    return result[0][0] if result else 0

def get_next_review_info():
    """Get information about the next review date after today"""
    current_date = datetime.now().strftime('%Y-%m-%d')
    category = category_var.get()
    
    if category == "All Categories":
        query = """
            SELECT MIN(NextReviewDate)
            FROM FactCards 
            WHERE NextReviewDate > ?
        """
        result = execute_query(query, (current_date,))
    else:
        query = """
            SELECT MIN(f.NextReviewDate)
            FROM FactCards f
            JOIN Categories c ON f.CategoryID = c.CategoryID
            WHERE f.NextReviewDate > ? AND c.CategoryName = ?
        """
        result = execute_query(query, (current_date, category))
    
    if result and result[0][0]:
        next_date = result[0][0]
        # Count fact cards due on the next date
        if category == "All Categories":
            query = """
                SELECT COUNT(*)
                FROM FactCards 
                WHERE NextReviewDate = ?
            """
            count_result = execute_query(query, (next_date,))
        else:
            query = """
                SELECT COUNT(*)
                FROM FactCards f
                JOIN Categories c ON f.CategoryID = c.CategoryID
                WHERE f.NextReviewDate = ? AND c.CategoryName = ?
            """
            count_result = execute_query(query, (next_date, category))
        count = count_result[0][0] if count_result else 0
        return next_date, count
    return None, 0

def toggle_question_answer():
    """Toggle between showing question and answer"""
    global show_answer
    
    if current_factcard_id is None:
        return
    
    # Toggle between question and answer
    show_answer = not show_answer
    
    if show_answer:
        # Fetch the answer from the database
        query = "SELECT Answer FROM FactCards WHERE FactCardID = ?"
        answer = execute_query(query, (current_factcard_id,))[0][0]
        factcard_label.config(text=f"Answer: {answer}", font=("Trebuchet MS", adjust_font_size(answer)))
        show_answer_button.config(text="Show Question")
    else:
        # Show the question again
        query = "SELECT Question FROM FactCards WHERE FactCardID = ?"
        question = execute_query(query, (current_factcard_id,))[0][0]
        factcard_label.config(text=f"Question: {question}", font=("Trebuchet MS", adjust_font_size(question)))
        show_answer_button.config(text="Show Answer")
    
    # Keep mastery display updated
    update_mastery_display()

def update_mastery_display():
    """Update the visual display of the mastery level for the current card"""
    if current_factcard_id:
        query = "SELECT Mastery FROM FactCards WHERE FactCardID = ?"
        mastery = execute_query(query, (current_factcard_id,))[0][0]
        
        # Update the mastery progress in the UI
        mastery_percentage = int(mastery * 100)
        mastery_level_label.config(text=f"Mastery: {mastery_percentage}%")
        
        # Update progress bar
        mastery_progress["value"] = mastery_percentage
        
        # Change color based on mastery level
        if mastery < 0.3:
            mastery_level_label.config(fg="#F44336")  # Red for low mastery
        elif mastery < 0.7:
            mastery_level_label.config(fg="#FFC107")  # Yellow for medium mastery
        else:
            mastery_level_label.config(fg="#4CAF50")  # Green for high mastery
    else:
        # No card selected
        mastery_level_label.config(text="Mastery: N/A")
        mastery_progress["value"] = 0

def fetch_due_factcard():
    """Fetch a fact card due for review"""
    global current_factcard_id, show_answer
    category = category_var.get()
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    # Reset the show_answer state for new fact card
    show_answer = False
    
    # Get fact cards due for review today or earlier
    if category == "All Categories":
        query = """
            SELECT TOP 1 FactCardID, Question, Answer, NextReviewDate, CurrentInterval, Mastery
            FROM FactCards
            WHERE NextReviewDate <= ?
            ORDER BY NextReviewDate, NEWID()
        """
        factcard = execute_query(query, (current_date,))
    else:
        query = """
            SELECT TOP 1 f.FactCardID, f.Question, f.Answer, f.NextReviewDate, f.CurrentInterval, f.Mastery
            FROM FactCards f
            JOIN Categories c ON f.CategoryID = c.CategoryID
            WHERE c.CategoryName = ? AND f.NextReviewDate <= ?
            ORDER BY f.NextReviewDate, NEWID()
        """
        factcard = execute_query(query, (category, current_date))
    
    if factcard:
        # We have a fact card due for review
        factcard_id = factcard[0][0]
        question = factcard[0][1]
        current_factcard_id = factcard_id
        
        # Show the question
        show_review_buttons(True)
        show_answer_button.config(state="normal")
        return f"Question: {question}"
    else:
        # No fact cards due for review
        current_factcard_id = None
        next_date, count = get_next_review_info()
        show_review_buttons(False)
        show_answer_button.config(state="disabled")
        
        if next_date:
            next_date_str = next_date.strftime('%Y-%m-%d') if isinstance(next_date, datetime) else next_date
            return f"No fact cards due for review today.\n\nNext review date: {next_date_str}\nFact cards due on that day: {count}"
        else:
            return "No fact cards found. Add some fact cards first!"

def load_next_factcard():
    """Load the next due fact card"""
    factcard_text = fetch_due_factcard()
    if factcard_text:
        factcard_label.config(text=factcard_text, font=("Trebuchet MS", adjust_font_size(factcard_text)))
        update_mastery_display()  # Update the mastery display
    else:
        factcard_label.config(text="No fact cards found.", font=("Trebuchet MS", 12))
        mastery_level_label.config(text="Mastery: N/A")
        mastery_progress["value"] = 0
    update_due_count()

def update_due_count():
    """Update the count of fact cards due today"""
    due_count = get_due_factcard_count()
    due_count_label.config(text=f"Due today: {due_count}")

def show_review_buttons(show):
    """Show or hide the spaced repetition buttons"""
    state = "normal" if show else "disabled"
    hard_button.config(state=state)
    medium_button.config(state=state)
    easy_button.config(state=state)
    
    # Instead of disabling, completely hide or show the edit and delete buttons
    if show:
        # Show buttons if there's a fact card to review
        edit_icon_button.pack(side="left", padx=10)
        delete_icon_button.pack(side="left", padx=10)
    else:
        # Hide buttons if there's no fact card
        edit_icon_button.pack_forget()
        delete_icon_button.pack_forget()

def update_factcard_schedule(difficulty):
    """Update the fact card's review schedule based on difficulty rating and adjust mastery level"""
    global current_factcard_id
    if current_factcard_id:
        # Get current interval and mastery level
        query = "SELECT CurrentInterval, Mastery FROM FactCards WHERE FactCardID = ?"
        result = execute_query(query, (current_factcard_id,))[0]
        current_interval, current_mastery = result[0], result[1]
        
        # Update mastery level based on difficulty
        if difficulty == "Hard":
            # Decrease mastery when struggling (min 0.0)
            new_mastery = max(0.0, current_mastery - 0.1)
            new_interval = 1  # Reset interval
        elif difficulty == "Medium":
            # Small increase in mastery
            new_mastery = min(1.0, current_mastery + 0.05)
            # Adjust multiplier based on mastery level
            multiplier = 1.3 + (current_mastery * 0.4)  # ranges from 1.3 to 1.7
            new_interval = int(current_interval * multiplier)
        else:  # Easy
            # Larger increase in mastery
            new_mastery = min(1.0, current_mastery + 0.15)
            # Adjust multiplier based on mastery level
            multiplier = 2.0 + (current_mastery * 1.0)  # ranges from 2.0 to 3.0
            new_interval = int(current_interval * multiplier)
        
        # Calculate next review date
        if difficulty == "Hard":
            # For Hard, set the next review date to TODAY
            next_review_date = datetime.now().strftime('%Y-%m-%d')
        else:
            # For Medium and Easy, add the interval days
            next_review_date = (datetime.now() + timedelta(days=new_interval)).strftime('%Y-%m-%d')
            
        # Update the database with new values including mastery
        execute_query(
            """
            UPDATE FactCards 
            SET NextReviewDate = ?, CurrentInterval = ?, Mastery = ?, ViewCount = ViewCount + 1
            WHERE FactCardID = ?
            """, 
            (next_review_date, new_interval, new_mastery, current_factcard_id), 
            fetch=False
        )
        
        # Show feedback including mastery level
        mastery_percentage = int(new_mastery * 100)
        if difficulty == "Hard":
            feedback_text = f"Rated as {difficulty}. Next review today. Mastery: {mastery_percentage}%"
        else:
            feedback_text = f"Rated as {difficulty}. Next review in {new_interval} days. Mastery: {mastery_percentage}%"
        
        status_label.config(text=feedback_text, fg="#b66d20")
        
        # Load the next fact card
        root.after(1000, load_next_factcard)

def on_hard_click():
    update_factcard_schedule("Hard")

def on_medium_click():
    update_factcard_schedule("Medium")

def on_easy_click():
    update_factcard_schedule("Easy")

def add_new_factcard():
    """Add a new fact card to the database"""
    # Create a popup window
    add_window = tk.Toplevel(root)
    add_window.title("Add New Fact Card")
    add_window.geometry("500x350")
    add_window.configure(bg='#1e1e1e')
    
    # Get categories for dropdown
    categories = execute_query("SELECT CategoryName FROM Categories WHERE IsActive = 1")
    category_names = [cat[0] for cat in categories]
    
    # Create and place widgets
    tk.Label(add_window, text="Add New Fact Card", fg="white", bg="#1e1e1e", 
             font=("Trebuchet MS", 14, 'bold')).pack(pady=10)
    
    # Category selection
    cat_frame = tk.Frame(add_window, bg="#1e1e1e")
    cat_frame.pack(fill="x", padx=20, pady=5)
    
    tk.Label(cat_frame, text="Category:", fg="white", bg="#1e1e1e", 
             font=("Trebuchet MS", 10)).pack(side="left", padx=5)
    
    cat_var = tk.StringVar(add_window)
    cat_var.set(category_names[0] if category_names else "No Categories")
    
    cat_dropdown = ttk.Combobox(cat_frame, textvariable=cat_var, values=category_names, state="readonly", width=20)
    cat_dropdown.pack(side="left", padx=5, fill="x", expand=True)
    
    # Question
    q_frame = tk.Frame(add_window, bg="#1e1e1e")
    q_frame.pack(fill="x", padx=20, pady=5)
    
    tk.Label(q_frame, text="Question:", fg="white", bg="#1e1e1e", 
             font=("Trebuchet MS", 10)).pack(side="top", anchor="w", padx=5)
    
    question_text = tk.Text(q_frame, height=4, width=40, font=("Trebuchet MS", 10))
    question_text.pack(fill="x", padx=5, pady=5)
    
    # Answer
    a_frame = tk.Frame(add_window, bg="#1e1e1e")
    a_frame.pack(fill="x", padx=20, pady=5)
    
    tk.Label(a_frame, text="Answer:", fg="white", bg="#1e1e1e", 
             font=("Trebuchet MS", 10)).pack(side="top", anchor="w", padx=5)
    
    answer_text = tk.Text(a_frame, height=4, width=40, font=("Trebuchet MS", 10))
    answer_text.pack(fill="x", padx=5, pady=5)
    
    def save_factcard():
        category = cat_var.get()
        question = question_text.get("1.0", "end-1c").strip()
        answer = answer_text.get("1.0", "end-1c").strip()
        
        if not question or not answer:
            status_label.config(text="Question and answer are required!", fg="#ff0000")
            return
        
        # Get category ID
        category_id = execute_query("SELECT CategoryID FROM Categories WHERE CategoryName = ?", (category,))[0][0]
        
        # Insert the new fact card - now including default Mastery of 0.0
        execute_query(
            """
            INSERT INTO FactCards (CategoryID, Question, Answer, NextReviewDate, CurrentInterval, Mastery) 
            VALUES (?, ?, ?, GETDATE(), 1, 0.0)
            """, 
            (category_id, question, answer), 
            fetch=False
        )
        
        add_window.destroy()
        status_label.config(text="New fact card added successfully!", fg="#4CAF50")
        update_factcard_count()
        update_due_count()
        # If no current card is shown, load the newly added card
        if current_factcard_id is None:
            load_next_factcard()
    
    # Save button
    save_button = tk.Button(add_window, text="Save Fact Card", bg='#4CAF50', fg="white", 
                           command=save_factcard, cursor="hand2", borderwidth=0, 
                           highlightthickness=0, padx=10, pady=5,
                           font=("Trebuchet MS", 10, 'bold'))
    save_button.pack(pady=20)

def edit_current_factcard():
    """Edit the current fact card"""
    if not current_factcard_id:
        return
    
    # Get current fact card data
    query = """
    SELECT f.Question, f.Answer, c.CategoryName, f.Mastery
    FROM FactCards f 
    JOIN Categories c ON f.CategoryID = c.CategoryID
    WHERE f.FactCardID = ?
    """
    data = execute_query(query, (current_factcard_id,))[0]
    current_question, current_answer, current_category, current_mastery = data
    
    # Create a popup window
    edit_window = tk.Toplevel(root)
    edit_window.title("Edit Fact Card")
    edit_window.geometry("500x400")  # Made slightly taller for mastery slider
    edit_window.configure(bg='#1e1e1e')
    
    # Get categories for dropdown
    categories = execute_query("SELECT CategoryName FROM Categories WHERE IsActive = 1")
    category_names = [cat[0] for cat in categories]
    
    # Create and place widgets
    tk.Label(edit_window, text="Edit Fact Card", fg="white", bg="#1e1e1e", 
             font=("Trebuchet MS", 14, 'bold')).pack(pady=10)
    
    # Category selection
    cat_frame = tk.Frame(edit_window, bg="#1e1e1e")
    cat_frame.pack(fill="x", padx=20, pady=5)
    
    tk.Label(cat_frame, text="Category:", fg="white", bg="#1e1e1e", 
             font=("Trebuchet MS", 10)).pack(side="left", padx=5)
    
    cat_var = tk.StringVar(edit_window)
    cat_var.set(current_category)
    
    cat_dropdown = ttk.Combobox(cat_frame, textvariable=cat_var, values=category_names, state="readonly", width=20)
    cat_dropdown.pack(side="left", padx=5, fill="x", expand=True)
    
    # Question
    q_frame = tk.Frame(edit_window, bg="#1e1e1e")
    q_frame.pack(fill="x", padx=20, pady=5)
    
    tk.Label(q_frame, text="Question:", fg="white", bg="#1e1e1e", 
             font=("Trebuchet MS", 10)).pack(side="top", anchor="w", padx=5)
    
    question_text = tk.Text(q_frame, height=4, width=40, font=("Trebuchet MS", 10))
    question_text.insert("1.0", current_question)
    question_text.pack(fill="x", padx=5, pady=5)
    
    # Answer
    a_frame = tk.Frame(edit_window, bg="#1e1e1e")
    a_frame.pack(fill="x", padx=20, pady=5)
    
    tk.Label(a_frame, text="Answer:", fg="white", bg="#1e1e1e", 
             font=("Trebuchet MS", 10)).pack(side="top", anchor="w", padx=5)
    
    answer_text = tk.Text(a_frame, height=4, width=40, font=("Trebuchet MS", 10))
    answer_text.insert("1.0", current_answer)
    answer_text.pack(fill="x", padx=5, pady=5)
    
    # Mastery level slider
    m_frame = tk.Frame(edit_window, bg="#1e1e1e")
    m_frame.pack(fill="x", padx=20, pady=5)
    
    tk.Label(m_frame, text=f"Mastery Level: {int(current_mastery * 100)}%", fg="white", bg="#1e1e1e", 
             font=("Trebuchet MS", 10)).pack(side="top", anchor="w", padx=5)
    
    mastery_var = tk.DoubleVar(edit_window, value=current_mastery)
    
    def update_mastery_label(val):
        mastery_val = int(float(val) * 100)
        m_frame.winfo_children()[0].config(text=f"Mastery Level: {mastery_val}%")
    
    mastery_slider = ttk.Scale(m_frame, from_=0.0, to=1.0, orient="horizontal",
                             variable=mastery_var, command=update_mastery_label)
    mastery_slider.pack(fill="x", padx=5, pady=5)
    
    def update_factcard():
        category = cat_var.get()
        question = question_text.get("1.0", "end-1c").strip()
        answer = answer_text.get("1.0", "end-1c").strip()
        mastery = mastery_var.get()
        
        if not question or not answer:
            status_label.config(text="Question and answer are required!", fg="#ff0000")
            return
        
        # Get category ID
        category_id = execute_query("SELECT CategoryID FROM Categories WHERE CategoryName = ?", (category,))[0][0]
        
        # Update the fact card including mastery
        execute_query(
            """
            UPDATE FactCards 
            SET CategoryID = ?, Question = ?, Answer = ?, Mastery = ? 
            WHERE FactCardID = ?
            """, 
            (category_id, question, answer, mastery, current_factcard_id), 
            fetch=False
        )
        
        edit_window.destroy()
        status_label.config(text="Fact card updated successfully!", fg="#4CAF50")
        
        # Refresh the current card display
        global show_answer
        if show_answer:
            factcard_label.config(text=f"Answer: {answer}", font=("Trebuchet MS", adjust_font_size(answer)))
        else:
            factcard_label.config(text=f"Question: {question}", font=("Trebuchet MS", adjust_font_size(question)))
        
        # Update mastery display
        update_mastery_display()
    
    # Update button
    update_button = tk.Button(edit_window, text="Update Fact Card", bg='#2196F3', fg="white", 
                             command=update_factcard, cursor="hand2", borderwidth=0, 
                             highlightthickness=0, padx=10, pady=5,
                             font=("Trebuchet MS", 10, 'bold'))
    update_button.pack(pady=20)

def delete_current_factcard():
    """Delete the current fact card"""
    if not current_factcard_id:
        return
    
    # Ask for confirmation
    if tk.messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this fact card?"):
        # Delete the fact card
        execute_query("DELETE FROM FactCards WHERE FactCardID = ?", (current_factcard_id,), fetch=False)
        status_label.config(text="Fact card deleted!", fg="#F44336")
        update_factcard_count()
        update_due_count()
        # Load the next fact card
        load_next_factcard()

def manage_categories():
    """Open a window to manage categories"""
    # Create a popup window
    cat_window = tk.Toplevel(root)
    cat_window.title("Manage Categories")
    cat_window.geometry("400x500")
    cat_window.configure(bg='#1e1e1e')
    
    # Create and place widgets
    tk.Label(cat_window, text="Manage Categories", fg="white", bg="#1e1e1e", 
             font=("Trebuchet MS", 14, 'bold')).pack(pady=10)
    
    # Add new category frame
    add_frame = tk.Frame(cat_window, bg="#1e1e1e")
    add_frame.pack(fill="x", padx=20, pady=10)
    
    tk.Label(add_frame, text="New Category:", fg="white", bg="#1e1e1e", 
             font=("Trebuchet MS", 10)).pack(side="left", padx=5)
    
    new_cat_entry = tk.Entry(add_frame, width=20, font=("Trebuchet MS", 10))
    new_cat_entry.pack(side="left", padx=5, fill="x", expand=True)
    
    def add_category():
        new_cat = new_cat_entry.get().strip()
        if not new_cat:
            return
        
        # Check if category already exists
        existing = execute_query("SELECT COUNT(*) FROM Categories WHERE CategoryName = ?", (new_cat,))[0][0]
        if existing > 0:
            tk.messagebox.showinfo("Error", f"Category '{new_cat}' already exists!")
            return
        
        # Add the new category
        execute_query(
            "INSERT INTO Categories (CategoryName, Description) VALUES (?, '')", 
            (new_cat,), 
            fetch=False
        )
        
        new_cat_entry.delete(0, tk.END)
        refresh_category_list()
        update_category_dropdown()
    
    add_button = tk.Button(add_frame, text="Add", bg='#4CAF50', fg="white", 
                         command=add_category, cursor="hand2", borderwidth=0, 
                         highlightthickness=0, padx=10)
    add_button.pack(side="left", padx=5)
    
    # Category list frame
    list_frame = tk.Frame(cat_window, bg="#1e1e1e")
    list_frame.pack(fill="both", expand=True, padx=20, pady=10)
    
    tk.Label(list_frame, text="Existing Categories:", fg="white", bg="#1e1e1e", 
             font=("Trebuchet MS", 10, 'bold')).pack(anchor="w", pady=5)
    
    # Scrollable list frame
    scroll_frame = tk.Frame(list_frame, bg="#1e1e1e")
    scroll_frame.pack(fill="both", expand=True)
    
    scrollbar = tk.Scrollbar(scroll_frame)
    scrollbar.pack(side="right", fill="y")
    
    cat_listbox = tk.Listbox(scroll_frame, height=15, width=30, font=("Trebuchet MS", 10),
                           yscrollcommand=scrollbar.set, bg="#2a2a2a", fg="white",
                           selectbackground="#4CAF50", selectforeground="white")
    cat_listbox.pack(side="left", fill="both", expand=True)
    
    scrollbar.config(command=cat_listbox.yview)
    
    def refresh_category_list():
        cat_listbox.delete(0, tk.END)
        categories = execute_query("SELECT CategoryName, CategoryID FROM Categories ORDER BY CategoryName")
        for cat in categories:
            cat_listbox.insert(tk.END, f"{cat[0]} (ID: {cat[1]})")
    
    refresh_category_list()
    
    # Action buttons frame
    action_frame = tk.Frame(cat_window, bg="#1e1e1e")
    action_frame.pack(fill="x", padx=20, pady=10)
    
    def rename_selected_category():
        selection = cat_listbox.curselection()
        if not selection:
            return
        
        # Extract category ID from selection text
        cat_text = cat_listbox.get(selection[0])
        cat_id = int(cat_text.split("ID: ")[1].strip(")"))
        
        # Get current name
        cat_name = execute_query("SELECT CategoryName FROM Categories WHERE CategoryID = ?", (cat_id,))[0][0]
        
        # Ask for new name
        new_name = simpledialog.askstring("Rename Category", f"New name for '{cat_name}':", initialvalue=cat_name)
        if not new_name or new_name == cat_name:
            return
        
        # Check if the new name already exists
        existing = execute_query("SELECT COUNT(*) FROM Categories WHERE CategoryName = ? AND CategoryID != ?", 
                              (new_name, cat_id))[0][0]
        if existing > 0:
            tk.messagebox.showinfo("Error", f"Category '{new_name}' already exists!")
            return
        
        # Update the category
        execute_query("UPDATE Categories SET CategoryName = ? WHERE CategoryID = ?", (new_name, cat_id), fetch=False)
        refresh_category_list()
        update_category_dropdown()
    
    def delete_selected_category():
        selection = cat_listbox.curselection()
        if not selection:
            return
        
        # Extract category ID from selection text
        cat_text = cat_listbox.get(selection[0])
        cat_id = int(cat_text.split("ID: ")[1].strip(")"))
        cat_name = cat_text.split(" (ID:")[0]
        
        # Check if category has fact cards
        card_count = execute_query("SELECT COUNT(*) FROM FactCards WHERE CategoryID = ?", (cat_id,))[0][0]
        
        if card_count > 0:
            if not tk.messagebox.askyesno("Warning", 
                                       f"Category '{cat_name}' has {card_count} fact cards. " +
                                       "Deleting it will also delete all associated fact cards. Continue?"):
                return
        
        # Delete the category and its fact cards
        execute_query("""
            BEGIN TRANSACTION;
            
            DELETE FROM FactCardTags WHERE FactCardID IN (SELECT FactCardID FROM FactCards WHERE CategoryID = ?);
            DELETE FROM FactCards WHERE CategoryID = ?;
            DELETE FROM Categories WHERE CategoryID = ?;
            
            COMMIT TRANSACTION;
        """, (cat_id, cat_id, cat_id), fetch=False)
        
        refresh_category_list()
        update_category_dropdown()
        update_factcard_count()
        update_due_count()
    
    rename_button = tk.Button(action_frame, text="Rename", bg='#2196F3', fg="white", 
                            command=rename_selected_category, cursor="hand2", borderwidth=0, 
                            highlightthickness=0, padx=10, pady=5)
    rename_button.pack(side="left", padx=5)
    
    delete_button_cat = tk.Button(action_frame, text="Delete", bg='#F44336', fg="white", 
                                command=delete_selected_category, cursor="hand2", borderwidth=0, 
                                highlightthickness=0, padx=10, pady=5)
    delete_button_cat.pack(side="left", padx=5)
    
    # Close button
    close_button = tk.Button(cat_window, text="Close", bg='#607D8B', fg="white", 
                           command=cat_window.destroy, cursor="hand2", borderwidth=0, 
                           highlightthickness=0, padx=20, pady=5,
                           font=("Trebuchet MS", 10, 'bold'))
    close_button.pack(pady=15)

def load_categories():
    """Load categories for the dropdown"""
    query = "SELECT DISTINCT CategoryName FROM Categories WHERE IsActive = 1 ORDER BY CategoryName"
    categories = execute_query(query)
    category_names = [category[0] for category in categories] if categories else []
    category_names.insert(0, "All Categories")  # Add All Categories option
    return category_names

def update_category_dropdown():
    """Update the category dropdown with current categories"""
    categories = load_categories()
    category_dropdown['values'] = categories
    # Keep current selection if it exists in new list, otherwise reset
    current_category = category_var.get()
    if current_category in categories:
        category_var.set(current_category)
    else:
        category_var.set("All Categories")

def adjust_font_size(text):
    """Dynamically adjust font size based on text length"""
    return max(8, min(12, int(12 - (len(text) / 150))))

def create_label(parent, text, fg="white", cursor=None, font=("Trebuchet MS", 7), side='left'):
    """Create a styled label"""
    label = tk.Label(parent, text=text, fg=fg, bg="#1e1e1e", font=font)
    if cursor:
        label.configure(cursor=cursor)
    label.pack(side=side)
    return label

def on_category_change(event=None):
    """Handle category dropdown change"""
    load_next_factcard()

def reset_to_welcome():
    """Reset to welcome screen"""
    factcard_label.config(text="Welcome to FactDari!", 
                          font=("Trebuchet MS", adjust_font_size("Welcome to FactDari!")))
    status_label.config(text="")
    show_review_buttons(False)
    show_answer_button.config(state="disabled")
    mastery_level_label.config(text="Mastery: N/A")
    mastery_progress["value"] = 0
    update_due_count()

def show_home_page():
    """Show the home page with welcome message and start button"""
    global is_home_page
    is_home_page = True
    
    # Hide all fact card-related UI elements
    stats_frame.pack_forget()
    icon_buttons_frame.pack_forget()
    sr_frame.pack_forget()
    answer_mastery_frame.pack_forget()
    category_frame.pack_forget()
    
    # Update the welcome message
    factcard_label.config(text="Welcome to FactDari!\n\nYour Personal Knowledge Companion", 
                         font=("Trebuchet MS", 16, 'bold'),
                         wraplength=450, justify="center")
    
    # Show the slogan
    slogan_label.config(text="Strengthen your knowledge one fact at a time")
    slogan_label.pack(side="top", pady=5)
    
    # Show the start learning button
    start_button.pack(pady=20)
    
    # Apply rounded corners again after UI changes
    root.update_idletasks()
    apply_rounded_corners(root, 15)

def start_learning():
    """Switch from home page to learning interface"""
    global is_home_page
    is_home_page = False
    
    # Hide home page elements
    slogan_label.pack_forget()
    start_button.pack_forget()
    
    # Show all fact card-related UI elements
    category_frame.pack(side="right", padx=5, pady=3)
    answer_mastery_frame.pack(side="top", fill="x", pady=0)
    sr_frame.pack(side="top", fill="x", pady=5)
    icon_buttons_frame.pack(side="top", fill="x", pady=5)
    stats_frame.pack(side="bottom", fill="x", padx=10, pady=3)
    
    # Load the first fact card
    load_next_factcard()
    
    # Apply rounded corners again after UI changes
    root.update_idletasks()
    apply_rounded_corners(root, 15)

# Main window setup
root = tk.Tk()
root.geometry("500x380")  # Made slightly taller to accommodate mastery display
root.overrideredirect(True)
root.configure(bg='#1e1e1e')

# Title bar
title_bar = tk.Frame(root, bg='#000000', height=30, relief='raised')
title_bar.pack(side="top", fill="x")
title_bar.bind("<Button-1>", on_press)
title_bar.bind("<B1-Motion>", on_drag)

tk.Label(title_bar, text="FactDari", fg="white", bg='#000000', 
         font=("Trebuchet MS", 12, 'bold')).pack(side="left", padx=5, pady=5)

# Category selection - create but don't pack yet
category_frame = tk.Frame(title_bar, bg='#000000')
tk.Label(category_frame, text="Category:", fg="white", bg='#000000', 
         font=("Trebuchet MS", 8)).pack(side="left", padx=5)

category_var = tk.StringVar(root, value="All Categories")
category_dropdown = ttk.Combobox(category_frame, textvariable=category_var, state="readonly", width=15)
category_dropdown['values'] = load_categories()
category_dropdown.pack(side="left")
category_dropdown.bind("<<ComboboxSelected>>", on_category_change)

# Main content area
content_frame = tk.Frame(root, bg="#1e1e1e")
content_frame.pack(side="top", fill="both", expand=True, padx=10, pady=5)

# Fact card display
factcard_frame = tk.Frame(content_frame, bg="#1e1e1e")
factcard_frame.pack(side="top", fill="both", expand=True, pady=5)

# Add top padding to push content down
padding_frame = tk.Frame(factcard_frame, bg="#1e1e1e", height=30)  # Adjust height as needed
padding_frame.pack(side="top", fill="x")

factcard_label = tk.Label(factcard_frame, text="Welcome to FactDari!", fg="white", bg="#1e1e1e", 
                          font=("Trebuchet MS", 16, 'bold'), wraplength=450, justify="center")
factcard_label.pack(side="top", fill="both", expand=True, padx=10, pady=10)

# Create slogan label (will be packed in show_home_page)
slogan_label = tk.Label(content_frame, text="Strengthen your knowledge one fact at a time", 
                      fg="#4CAF50", bg="#1e1e1e", font=("Trebuchet MS", 12, 'italic'))

# Create start learning button (will be packed in show_home_page)
start_button = tk.Button(content_frame, text="Start Learning", command=start_learning, 
                      bg='#4CAF50', fg="white", cursor="hand2", borderwidth=0, 
                      highlightthickness=0, padx=20, pady=10,
                      font=("Trebuchet MS", 14, 'bold'))

# Create a new frame for Show Answer and Mastery info that will keep them together - don't pack yet
answer_mastery_frame = tk.Frame(content_frame, bg="#1e1e1e")

# Show Answer button in the combined frame
show_answer_button = tk.Button(answer_mastery_frame, text="Show Answer", command=toggle_question_answer, 
                              bg='#2196F3', fg="white", cursor="hand2", borderwidth=0, 
                              highlightthickness=0, padx=10, pady=5, state="disabled")
show_answer_button.pack(fill="x", padx=100, pady=2)

# Mastery level display in the combined frame
mastery_level_label = tk.Label(answer_mastery_frame, text="Mastery: N/A", fg="white", bg="#1e1e1e", 
                             font=("Trebuchet MS", 10, 'bold'))
mastery_level_label.pack(side="top", pady=2)

# Add a progress bar to visualize mastery in the combined frame
mastery_progress = ttk.Progressbar(answer_mastery_frame, orient="horizontal", length=280, mode="determinate")
mastery_progress.pack(side="top", pady=2)

# Style the progress bar
style = ttk.Style()
style.theme_use('default')
style.configure("TProgressbar", thickness=8, troughcolor='#333333', background='#4CAF50')

# Spaced repetition buttons - create but don't pack yet
sr_frame = tk.Frame(content_frame, bg="#1e1e1e")

sr_buttons = tk.Frame(sr_frame, bg="#1e1e1e")
sr_buttons.pack(side="top", fill="x")

hard_button = tk.Button(sr_buttons, text="Hard", command=on_hard_click, bg='#F44336', fg="white", 
                      cursor="hand2", borderwidth=0, highlightthickness=0, padx=10, pady=5)
hard_button.pack(side="left", expand=True, fill="x", padx=(0, 5))

medium_button = tk.Button(sr_buttons, text="Medium", command=on_medium_click, bg='#FFC107', fg="white", 
                        cursor="hand2", borderwidth=0, highlightthickness=0, padx=10, pady=5)
medium_button.pack(side="left", expand=True, fill="x", padx=(0, 5))

easy_button = tk.Button(sr_buttons, text="Easy", command=on_easy_click, bg='#4CAF50', fg="white", 
                       cursor="hand2", borderwidth=0, highlightthickness=0, padx=10, pady=5)
easy_button.pack(side="left", expand=True, fill="x")

# Load icons
home_icon = ImageTk.PhotoImage(Image.open("C:/Users/gaura/OneDrive/PC-Desktop/GitHubDesktop/Random-Facts-Generator/Resources/Images/home.png").resize((20, 20), Image.Resampling.LANCZOS))
speaker_icon = ImageTk.PhotoImage(Image.open("C:/Users/gaura/OneDrive/PC-Desktop/GitHubDesktop/Random-Facts-Generator/Resources/Images/speaker_icon.png").resize((20, 20), Image.Resampling.LANCZOS))
# Load action icons
add_icon = ImageTk.PhotoImage(Image.open("C:/Users/gaura/OneDrive/PC-Desktop/GitHubDesktop/Random-Facts-Generator/Resources/Images/add.png").resize((20, 20), Image.Resampling.LANCZOS))
edit_icon = ImageTk.PhotoImage(Image.open("C:/Users/gaura/OneDrive/PC-Desktop/GitHubDesktop/Random-Facts-Generator/Resources/Images/edit.png").resize((20, 20), Image.Resampling.LANCZOS))
delete_icon = ImageTk.PhotoImage(Image.open("C:/Users/gaura/OneDrive/PC-Desktop/GitHubDesktop/Random-Facts-Generator/Resources/Images/delete.png").resize((20, 20), Image.Resampling.LANCZOS))

# Icon buttons frame - create but don't pack yet
icon_buttons_frame = tk.Frame(content_frame, bg="#1e1e1e")

# Add button
add_icon_button = tk.Button(icon_buttons_frame, image=add_icon, bg='#1e1e1e', command=add_new_factcard,
                         cursor="hand2", borderwidth=0, highlightthickness=0)
add_icon_button.pack(side="left", padx=10)
add_icon_button.image = add_icon  # Keep a reference

# Create edit button but don't pack it initially
edit_icon_button = tk.Button(icon_buttons_frame, image=edit_icon, bg='#1e1e1e', command=edit_current_factcard,
                          cursor="hand2", borderwidth=0, highlightthickness=0)
edit_icon_button.image = edit_icon  # Keep a reference

# Create delete button but don't pack it initially
delete_icon_button = tk.Button(icon_buttons_frame, image=delete_icon, bg='#1e1e1e', command=delete_current_factcard,
                            cursor="hand2", borderwidth=0, highlightthickness=0)
delete_icon_button.image = delete_icon  # Keep a reference

# Status label - always visible
status_label = create_label(icon_buttons_frame, "", fg="#b66d20", 
                         font=("Trebuchet MS", 10), side='right')
status_label.pack_configure(pady=5, padx=10)

# Add home and speaker buttons
home_button = tk.Button(factcard_frame, image=home_icon, bg='#1e1e1e', bd=0, highlightthickness=0, 
                       cursor="hand2", activebackground='#1e1e1e', command=show_home_page)
home_button.place(relx=0, rely=0, anchor="nw", x=5, y=5)

speaker_button = tk.Button(factcard_frame, image=speaker_icon, bg='#1e1e1e', command=speak_text, 
                          cursor="hand2", borderwidth=0, highlightthickness=0)
speaker_button.image = speaker_icon  # Keep a reference
speaker_button.place(relx=1.0, rely=0, anchor="ne", x=-5, y=5)

# Bottom stats frame - create but don't pack yet
stats_frame = tk.Frame(root, bg="#1e1e1e")

# Stats labels - all with the same font size
factcard_count_label = create_label(stats_frame, "Total Fact Cards: 0", 
                                  font=("Trebuchet MS", 9), side='left')
factcard_count_label.pack_configure(padx=10)

due_count_label = create_label(stats_frame, "Due today: 0", 
                             font=("Trebuchet MS", 9), side='left')
due_count_label.pack_configure(padx=10)

coordinate_label = create_label(stats_frame, "Coordinates: ", 
                              font=("Trebuchet MS", 9), side='right')
coordinate_label.pack_configure(padx=10)

# Initially disable the review buttons
show_review_buttons(False)

# Set initial transparency
root.attributes('-alpha', 0.9)

# Bind focus events to the root window
root.bind("<FocusIn>", lambda event: root.attributes('-alpha', 1.0))
root.bind("<FocusOut>", lambda event: root.attributes('-alpha', 0.7))

# Final setup
root.update_idletasks()
apply_rounded_corners(root, 15)
set_static_position()
root.bind("<s>", set_static_position)
update_coordinates()
root.after(100, update_ui)

# Show the home page instead of loading the first fact card
show_home_page()

root.mainloop()