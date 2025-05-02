"""
Test script for reviewing a specific card from the database 5 times with Easy rating
CAUTION: This script WILL UPDATE the database
"""

import pyodbc
import config
from fsrs_engine import FSRSEngine
from datetime import datetime, timezone, timedelta
import sys
import time

def print_divider():
    print("=" * 70)

def fetch_card(card_id):
    """Fetch card from the database"""
    try:
        conn_str = config.get_connection_string()
        with pyodbc.connect(conn_str) as conn:
            with conn.cursor() as cursor:
                query = """
                SELECT 
                    FactCardID, Question, Answer, CategoryID,
                    Stability, Difficulty, State, 
                    NextReviewDate, CurrentInterval, 
                    Mastery, ViewCount, LastReviewDate,
                    Lapses
                FROM FactCards
                WHERE FactCardID = ?
                """
                cursor.execute(query, (card_id,))
                columns = [column[0] for column in cursor.description]
                result = cursor.fetchone()
                
                if result:
                    # Convert to dictionary
                    card_data = dict(zip(columns, result))
                    return card_data
                else:
                    print(f"Card ID {card_id} not found in database")
                    return None
    except Exception as e:
        print(f"Database error: {e}")
        return None

def format_date(dt):
    """Format datetime nicely for display"""
    if dt is None:
        return "None"
    elif isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d")
    else:
        return str(dt)

def simulate_review(card_data, rating_name):
    """Simulate a review with the given rating"""
    # Map rating name to integer
    rating_map = {"Again": 1, "Hard": 2, "Medium": 3, "Good": 3, "Easy": 4}
    
    if rating_name not in rating_map:
        print(f"Invalid rating: {rating_name}")
        return None
    
    rating_int = rating_map[rating_name]
    
    # Create FSRS engine
    fsrs_engine = FSRSEngine()
    
    # Prepare data for FSRS
    db_row = {
        "stability": card_data['Stability'],
        "difficulty": card_data['Difficulty'],
        "state": card_data['State'],
    }
    
    # Handle the due date conversion properly
    due_date = card_data['NextReviewDate']
    if due_date:
        # If due_date is already a datetime object
        if isinstance(due_date, datetime):
            if due_date.tzinfo is None:
                due_date = due_date.replace(tzinfo=timezone.utc)
        # If due_date is a string, parse it into a datetime
        elif isinstance(due_date, str):
            try:
                # Try to parse with different formats
                try:
                    due_date = datetime.strptime(due_date, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    try:
                        due_date = datetime.strptime(due_date, '%Y-%m-%d')
                    except ValueError:
                        print(f"Could not parse due date: {due_date}")
                        # Use current date as fallback
                        due_date = datetime.now()
                
                # Add timezone
                due_date = due_date.replace(tzinfo=timezone.utc)
            except Exception as e:
                print(f"Error parsing due date: {e}")
                due_date = datetime.now(timezone.utc)
    else:
        # No due date, use current time
        due_date = datetime.now(timezone.utc)
    
    db_row["due"] = due_date
    
    # Process the review
    result = fsrs_engine.review(db_row, rating_int)
    
    # Calculate mastery value (as done in the app)
    mastery_value = min(1.0, result["stability"] / 100.0)
    
    # Return results
    return {
        "original": card_data,
        "new_values": {
            "stability": result["stability"],
            "difficulty": result["difficulty"],
            "state": result["state"],
            "interval": result["interval"],
            "due_date": result["due"],
            "mastery": mastery_value,
            "is_lapse": result["is_lapse"],
            "rating": rating_int
        }
    }

def display_results(review_number, card_data, new_values):
    """Display the review results"""
    print_divider()
    print(f"REVIEW #{review_number} - CARD ID {card_data['FactCardID']}")
    print_divider()
    
    if review_number == 1:
        # Show card question on first review
        print(f"Question: {card_data['Question']}")
        print_divider()
    
    print(f"BEFORE REVIEW #{review_number}:")
    print(f"Stability: {card_data['Stability']:.2f}")
    print(f"Difficulty: {card_data['Difficulty']:.2f}")
    print(f"State: {card_data['State']}")
    print(f"Next Review: {format_date(card_data['NextReviewDate'])}")
    print(f"Current Interval: {card_data['CurrentInterval']}")
    print(f"Mastery: {int(card_data['Mastery'] * 100)}%")
    print_divider()
    
    print(f"AFTER REVIEW #{review_number}:")
    print(f"Stability: {new_values['stability']:.2f} (change: {new_values['stability'] - card_data['Stability']:.2f})")
    print(f"Difficulty: {new_values['difficulty']:.2f} (change: {new_values['difficulty'] - card_data['Difficulty']:.2f})")
    print(f"State: {new_values['state']} (was: {card_data['State']})")
    print(f"Next Review: {format_date(new_values['due_date'])}")
    print(f"New Interval: {new_values['interval']} days")
    print(f"Mastery: {int(new_values['mastery'] * 100)}%")
    print_divider()
    
    # Check if values changed
    if (new_values['stability'] == card_data['Stability'] and 
        new_values['difficulty'] == card_data['Difficulty']):
        print("WARNING: Card values didn't change! Check FSRS engine implementation.")
    else:
        print("✓ Values updated successfully")
    print_divider()

def update_database(card_id, new_values):
    """Actually update the database with new values"""
    try:
        conn_str = config.get_connection_string()
        with pyodbc.connect(conn_str) as conn:
            with conn.cursor() as cursor:
                # Log the review
                cursor.execute("""
                    INSERT INTO ReviewLogs (FactCardID, ReviewDate, Rating, Interval)
                    VALUES (?, GETDATE(), ?, ?)
                """, (card_id, new_values["rating"], new_values["interval"]))
                
                # Update the card
                cursor.execute("""
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
                """, (
                    new_values["stability"], 
                    new_values["difficulty"],
                    new_values["state"],
                    new_values["interval"],
                    new_values["interval"],
                    new_values["mastery"],
                    1 if new_values["is_lapse"] else 0,
                    card_id
                ))
                
                conn.commit()
                return True
    except Exception as e:
        print(f"Error updating database: {e}")
        return False

def run_review_sequence(card_id, rating, num_reviews=5):
    """Run a sequence of reviews with the same rating, updating the database after each"""
    print(f"⚠️ CAUTION: This script will update card {card_id} in the database ⚠️")
    print(f"Performing {num_reviews} sequential reviews with rating '{rating}'")
    confirmation = input("Are you sure you want to proceed? (yes/no): ")
    
    if confirmation.lower() not in ["yes", "y"]:
        print("Operation cancelled.")
        return
    
    print_divider()
    print(f"Starting {num_reviews} review sequence...")
    
    # Store initial values for final summary
    original_data = fetch_card(card_id)
    if not original_data:
        print("Exiting due to error fetching card")
        return
    
    # Run multiple reviews
    for i in range(1, num_reviews + 1):
        # Fetch current card data
        card_data = fetch_card(card_id)
        if not card_data:
            print(f"Error fetching card for review {i}. Stopping sequence.")
            break
        
        # Simulate review
        results = simulate_review(card_data, rating)
        if not results:
            print(f"Error in review {i}. Stopping sequence.")
            break
        
        # Display results
        display_results(i, card_data, results["new_values"])
        
        # Update database
        print(f"Updating database for review #{i}...")
        success = update_database(card_id, results["new_values"])
        if not success:
            print(f"Error updating database for review {i}. Stopping sequence.")
            break
        
        print("Database updated successfully.")
        
        # Wait a short time between reviews to ensure timestamps are different
        if i < num_reviews:
            print(f"Waiting 2 seconds before next review...")
            time.sleep(2)
    
    # Print final summary
    final_data = fetch_card(card_id)
    if final_data:
        print("\nFINAL SUMMARY:")
        print_divider()
        print(f"Initial values from database:")
        print(f"Stability: {original_data['Stability']:.2f}")
        print(f"Difficulty: {original_data['Difficulty']:.2f}")
        print(f"State: {original_data['State']}")
        print(f"Mastery: {int(original_data['Mastery'] * 100)}%")
        print_divider()
        
        print(f"Final values after {num_reviews} '{rating}' reviews:")
        print(f"Stability: {final_data['Stability']:.2f}")
        print(f"Difficulty: {final_data['Difficulty']:.2f}")
        print(f"State: {final_data['State']}")
        print(f"Next Review: {format_date(final_data['NextReviewDate'])}")
        print(f"Final Interval: {final_data['CurrentInterval']} days")
        print(f"Mastery: {int(final_data['Mastery'] * 100)}%")
        print_divider()
        
        # Calculate improvement
        stability_improvement = final_data['Stability'] - original_data['Stability']
        mastery_improvement = final_data['Mastery'] - original_data['Mastery']
        
        print(f"Improvement after {num_reviews} reviews:")
        print(f"Stability increased by {stability_improvement:.2f}")
        print(f"Mastery increased by {int(mastery_improvement * 100)}%")
        print(f"Interval increased from {original_data['CurrentInterval']} to {final_data['CurrentInterval']} days")
    
    print_divider()
    print("Review sequence complete.")
    print(f"Card ID {card_id} has been updated in the database.")

def main():
    # Set the card ID to test
    card_id = 3
    
    # Rating to use for all reviews
    rating = "Easy"
    
    # Number of sequential reviews to perform
    num_reviews = 5
    
    # Run the reviews and update the database
    run_review_sequence(card_id, rating, num_reviews)

if __name__ == "__main__":
    main()