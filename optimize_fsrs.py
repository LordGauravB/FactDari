# optimize_fsrs.py for FSRS v5
import pyodbc
import pandas as pd
import json
import os
import argparse
import sys
from datetime import datetime, timezone
import config

def optimize_fsrs_weights(min_reviews=100, output_file="weights.json", verbose=False):
    """Train optimized FSRS weights based on user review history
    
    Args:
        min_reviews (int): Minimum number of reviews required for optimization
        output_file (str): Path to save the optimized weights
        verbose (bool): Whether to display detailed progress information
    
    Returns:
        bool: Whether optimization was successful
    """
    try:
        # Import here to avoid dependency issues if not installed
        from fsrs import Optimizer
    except ImportError:
        print("Error: fsrs-optimizer not installed.")
        print("Please run: pip install fsrs-optimizer")
        return False
    
    print(f"Starting FSRS weight optimization...")
    start_time = datetime.now()
    
    # Get database connection string from config
    conn_str = config.get_connection_string()
    
    try:
        # Connect to the database
        with pyodbc.connect(conn_str) as conn:
            # Check if ReviewLogs table exists
            table_check = conn.cursor().execute("""
                SELECT COUNT(*) 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_NAME = 'ReviewLogs'
            """).fetchone()[0]
            
            if table_check == 0:
                print("Error: ReviewLogs table does not exist. Please run the database migration first.")
                return False
            
            # Get review logs count
            review_count = conn.cursor().execute("SELECT COUNT(*) FROM ReviewLogs").fetchone()[0]
            print(f"Found {review_count} review logs in the database.")
            
            if review_count < min_reviews:
                print(f"Not enough review data for optimization. Found {review_count} reviews, need at least {min_reviews}.")
                print("Continue using the app and try again later when you have more review data.")
                return False

            # Get review logs with required fields for FSRS v5
            print("Retrieving review data from database...")
            
            # We need to join with FactCards to get card state information
            df = pd.read_sql("""
                SELECT 
                    rl.FactCardID as card_id,
                    rl.ReviewDate as review_time,
                    rl.Rating as rating,
                    rl.Interval as scheduled_days,
                    fc.State as state
                FROM ReviewLogs rl
                JOIN FactCards fc ON rl.FactCardID = fc.FactCardID
                ORDER BY rl.ReviewDate
            """, conn)
            
            # Format data for FSRS v5 optimizer
            if len(df) == 0:
                print("No review data found.")
                return False
                
            # Data preparation
            print("Preparing review data for optimization...")
            
            # Ensure we have the required columns
            required_columns = ['card_id', 'review_time', 'rating', 'state']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                print(f"Error: Missing required columns: {missing_columns}")
                print("Please make sure your database schema is correctly set up for FSRS v5.")
                return False
            
            # Convert review_time to datetime if it's not already
            if not pd.api.types.is_datetime64_dtype(df['review_time']):
                df['review_time'] = pd.to_datetime(df['review_time'])
            
            # Add timezone information if missing
            if df['review_time'].dt.tz is None:
                df['review_time'] = df['review_time'].dt.tz_localize(timezone.utc)
            
            # Fill missing states with 2 (Review)
            if 'state' in df.columns:
                df['state'] = df['state'].fillna(2)
            else:
                df['state'] = 2  # Default to Review state
            
            # Convert rating to int
            df['rating'] = df['rating'].astype(int)
            
            # Check for invalid ratings (must be 0-4 for FSRS v5)
            invalid_ratings = df[~df['rating'].isin([0, 1, 2, 3, 4])].shape[0]
            if invalid_ratings > 0:
                print(f"Warning: Found {invalid_ratings} reviews with invalid ratings. Filtering them out.")
                df = df[df['rating'].isin([0, 1, 2, 3, 4])]
            
            if verbose:
                print("\nSummary of ratings:")
                print(df['rating'].value_counts().sort_index())
                print(f"\nDate range: {df['review_time'].min()} to {df['review_time'].max()}")
                print(f"Number of cards: {df['card_id'].nunique()}")
                print(f"Reviews per card: {df.groupby('card_id').size().mean():.1f} (average)")
            
            # Check if we have enough data
            if len(df) < min_reviews:
                print(f"After filtering, only {len(df)} valid reviews remain. Need at least {min_reviews}.")
                return False
                
            # Initialize optimizer
            print("\nInitializing FSRS optimizer...")
            optimizer = Optimizer()
            
            # Train new weights
            print("Training model to find optimal weights (this may take several minutes)...")
            best_params = optimizer.optimize(df)
            
            # Save the weights
            print(f"Optimization complete! Saving weights to {output_file}")
            with open(output_file, "w") as f:
                json.dump(list(best_params), f, indent=2)
                
            # Display performance metrics if verbose
            if verbose:
                print("\nOptimized FSRS Parameters:")
                print(json.dumps(best_params, indent=2))
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            print(f"Optimization completed in {duration:.2f} seconds.")
            print(f"The optimized weights have been saved to {output_file}")
            print("Restart FactDari to use the new weights.")
            
            return True
            
    except Exception as e:
        print(f"Optimization error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Optimize FSRS weights for FactDari")
    parser.add_argument("--min-reviews", type=int, default=100, 
                        help="Minimum number of reviews required for optimization")
    parser.add_argument("--output", type=str, default="weights.json", 
                        help="Path to save the optimized weights")
    parser.add_argument("--verbose", action="store_true", 
                        help="Display detailed progress information")
    
    args = parser.parse_args()
    
    success = optimize_fsrs_weights(
        min_reviews=args.min_reviews,
        output_file=args.output,
        verbose=args.verbose
    )
    
    sys.exit(0 if success else 1)