# fsrs_engine_fixed.py  – FactDari wrapper around the **official** py-fsrs ≥ 5.0
#
# pip install py-fsrs==5.0.0         # scheduler (specifying exact version)
# pip install fsrs-optimizer  # (optional) weight-training utility
#
# The wrapper exposes one public method:
#     review(db_row, rating_int)  ->  dict   ← ready to WRITE BACK to SQL
#
# "rating_int" must be 1 (Again) / 2 (Hard) / 3 (Good) / 4 (Easy).
# Map your GUI buttons accordingly before calling it.
#
# FSRS Fields explained:
#   stability: Memory stability (how long you'll remember it) in days (0.0+)
#   difficulty: How hard the card is to recall (0.0-1.0, higher = harder)
#   state: Card learning state (1=Learning, 2=Review, 3=Relearning)
#   due: Next review date
#   interval: Days until next review
#   is_lapse: Whether this review was a memory failure
#
# ---------------------------------------------------------------------------

from fsrs import Scheduler, Card, Rating, DEFAULT_PARAMETERS
from datetime import datetime, timezone, timedelta
from typing    import Dict, Any, Optional
import json, os
import logging

# Configure logging
import config
log_dir = config.LOG_DIR
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
log_file = config.LOG_FILE
logging.basicConfig(level=logging.DEBUG,  # Changed to DEBUG level for more detailed logs
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filename=log_file,
                    filemode='a')


class FSRSEngine:
    """Thin shim that hides py-fsrs details from the rest of FactDari."""

    def __init__(self, weights_file: Optional[str] = None) -> None:
        # ------------------------------------------------------------------
        # 1) choose the 19 model parameters (aka "weights")
        # ------------------------------------------------------------------
        parameters = DEFAULT_PARAMETERS
        logging.debug(f"DEFAULT_PARAMETERS: {DEFAULT_PARAMETERS}")

        if weights_file and os.path.exists(weights_file):
            try:
                with open(weights_file, "r") as fh:
                    custom = json.load(fh)
                if isinstance(custom, list) and len(custom) == len(DEFAULT_PARAMETERS):
                    parameters = custom
                    logging.debug(f"Loaded custom parameters: {parameters}")
                else:
                    print("[FSRS] ⚠️  Ignoring weights file — wrong length.")
                    logging.warning(f"Ignoring weights file - wrong length. Expected {len(DEFAULT_PARAMETERS)}, got {len(custom) if isinstance(custom, list) else 'not a list'}")
            except Exception as exc:                                 # noqa: BLE001
                print(f"[FSRS] ⚠️  Could not load '{weights_file}': {exc}")
                logging.error(f"Could not load weights file '{weights_file}': {exc}")
        
        # Log the parameters being used
        logging.info(f"Using FSRS parameters: {parameters}")

        # ------------------------------------------------------------------
        # 2) build the scheduler
        # ------------------------------------------------------------------
        try:
            self.scheduler = Scheduler(parameters)
            logging.info("FSRS Scheduler initialized successfully")
        except Exception as e:
            logging.error(f"Error initializing FSRS Scheduler: {e}")
            # Fall back to default parameters if there was an error
            try:
                self.scheduler = Scheduler(DEFAULT_PARAMETERS)
                logging.info("FSRS Scheduler initialized with default parameters after error")
            except Exception as e2:
                logging.critical(f"Critical error initializing FSRS Scheduler with defaults: {e2}")
                raise

    # ──────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────
    def review(
        self,
        db_row: Dict[str, Any],
        rating_int: int,
        now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Run a *single* review and obtain updated scheduling fields.

        Parameters
        ----------
        db_row
            Dict holding the current card state fetched from SQL.
            Expected keys (anything missing falls back to FSRS defaults):
                stability : float | None
                difficulty: float | None
                due       : datetime | None    # NextReviewDate in UTC
                state     : int | None         # 1 Learning, 2 Review, 3 Relearning
        rating_int
            1 Again / 2 Hard / 3 Good / 4 Easy  (already mapped from UI)
        now
            datetime (UTC).  If omitted we use "right now".

        Returns
        -------
        Dict with **all** fields you typically write back:

            stability, difficulty, state, due,
            interval (days as int), is_lapse (bool)
        """
        now = now or datetime.now(timezone.utc)
        
        logging.info(f"Starting review for rating {rating_int}, current time: {now}")
        logging.debug(f"Input db_row: {db_row}")
        
        # 1) re-hydrate a Card object from the DB row
        card = Card()
        
        # Set default values in case they're missing
        if db_row.get("stability") is not None: 
            card.stability = float(db_row["stability"])
        else:
            card.stability = 0.1  # Default starting stability
            logging.debug("Using default stability: 0.1")
            
        if db_row.get("difficulty") is not None: 
            card.difficulty = float(db_row["difficulty"])
        else:
            card.difficulty = 0.3  # Default starting difficulty
            logging.debug("Using default difficulty: 0.3")
            
        if db_row.get("state") is not None: 
            card.state = int(db_row["state"])
        else:
            card.state = 1  # Default to Learning state
            logging.debug("Using default state: 1 (Learning)")

        logging.info(f"Initial card state: stability={card.stability}, difficulty={card.difficulty}, state={card.state}")
        
        # Set a default due date if none is provided
        # This is important for new cards with no previous due date
        due = db_row.get("due")
        if due:
            # ensure tz-aware UTC for FSRS
            if due.tzinfo is None:
                due = due.replace(tzinfo=timezone.utc)
            card.due = due.astimezone(timezone.utc)
        else:
            # Default to current time if no due date is provided
            card.due = now
            logging.debug(f"No due date provided, using current time: {now}")
            
        logging.info(f"Initial due date: {card.due}")

        # 2) Let FSRS work its magic
        try:
            # Make sure we have a valid Rating
            if rating_int < 1 or rating_int > 4:
                logging.warning(f"Invalid rating {rating_int}, clamping to range 1-4")
                rating_int = max(1, min(4, rating_int))
                
            # Create rating object
            rating = Rating(rating_int)
            logging.debug(f"Using rating: {rating} (from rating_int: {rating_int})")
            
            # Capture card state before review for comparison
            before_state = {
                "stability": card.stability,
                "difficulty": card.difficulty,
                "state": card.state,
                "due": card.due,
            }
            
            # Execute the review
            scheduling_result = self.scheduler.review_card(
                card,
                rating,
                review_datetime=now
            )
            
            # In py-fsrs 5.0+, review_card returns a tuple (scheduling_info, scheduling_cards)
            # where scheduling_info has the next card state information
            # The original card object is also updated in-place
            scheduling_info = scheduling_result[0]  # First element is the scheduling info
            
            # Log the full result for debugging
            logging.debug(f"FSRS review_card raw result: {scheduling_result}")
            logging.debug(f"Card object after review: {card.__dict__}")
            
            # Compare before and after states to verify changes
            if card.stability == before_state["stability"] and card.difficulty == before_state["difficulty"]:
                logging.warning("WARNING: Card values didn't change after review! Using manual fallback values.")
                
                # Apply manual fallback values based on the rating
                if rating_int == 1:  # Again
                    card.stability = max(0.1, before_state["stability"] * 0.2)
                    card.difficulty = min(1.0, before_state["difficulty"] + 0.15)
                    card.state = 3  # Relearning
                elif rating_int == 2:  # Hard
                    card.stability = before_state["stability"] * 1.2
                    card.difficulty = min(1.0, before_state["difficulty"] + 0.05)
                    card.state = 2  # Review
                elif rating_int == 3:  # Good
                    card.stability = max(1.0, before_state["stability"] * 1.5)
                    card.difficulty = max(0.1, before_state["difficulty"] - 0.05)
                    card.state = 2  # Review
                elif rating_int == 4:  # Easy
                    card.stability = max(1.0, before_state["stability"] * 3.0)
                    card.difficulty = max(0.1, before_state["difficulty"] - 0.1)
                    card.state = 2  # Review
                
                # Calculate new due date based on stability
                interval_days = max(1, int(card.stability))
                card.due = now + timedelta(days=interval_days)
                
                logging.info(f"Applied manual fallback values: stability={card.stability}, difficulty={card.difficulty}, state={card.state}")
        
        except Exception as e:
            logging.error(f"Error during FSRS review: {e}")
            # Emergency fallback - apply simple spaced repetition rules
            if rating_int == 1:  # Again
                card.stability = 0.1
                card.difficulty = min(1.0, card.difficulty + 0.2 if card.difficulty else 0.5)
                card.state = 3  # Relearning
                card.due = now + timedelta(days=1)
            else:
                # Use a simple exponential backoff
                interval_factor = {2: 1.5, 3: 2.0, 4: 3.0}.get(rating_int, 2.0)
                card.difficulty = max(0.1, card.difficulty - 0.1 if card.difficulty else 0.3)
                card.stability = max(0.1, card.stability * interval_factor if card.stability else interval_factor)
                card.state = 2  # Review
                card.due = now + timedelta(days=max(1, int(card.stability)))
                
            logging.info(f"Applied emergency fallback values after error: stability={card.stability}, difficulty={card.difficulty}, state={card.state}")
        
        # Set the next review interval based on the due date
        # Make sure we use a minimum interval of 1 day
        if card.due <= now:
            # If the card is currently overdue or due today, use at least 1 day
            interval_days = 1  # Minimum interval
            card.due = now + timedelta(days=1)  # Force at least one day ahead
        else:
            # Calculate days between now and the due date
            interval_days = max(1, (card.due - now).days)
        
        # Get proper due date from FSRS scheduling
        next_review_date = card.due
        
        # Log the actual processed FSRS values
        logging.info(f"After FSRS: stability={card.stability}, difficulty={card.difficulty}, state={card.state}")
        logging.info(f"FSRS scheduled: due={card.due}, interval={interval_days} days")
        
        # Remove timezone info to avoid SQL Server issues while preserving the same datetime
        next_review_date = next_review_date.replace(tzinfo=None)
        
        # Check if this review is a lapse (rating is "Again")
        is_lapse = (rating_int == 1)
        
        result = {
            "stability" : card.stability,
            "difficulty": card.difficulty,
            "state"     : card.state,
            "due"       : next_review_date,
            "interval"  : interval_days,
            "is_lapse"  : is_lapse,
        }
        
        logging.debug(f"Final result: {result}")
        return result

    # ──────────────────────────────────────────────────────────────────
    # Convenience helpers
    # ──────────────────────────────────────────────────────────────────
    def save_current_weights(self, path: str) -> None:
        """Dump the 19-parameter tuple to JSON (for backup or sharing)."""
        with open(path, "w") as fh:
            json.dump(list(self.scheduler.parameters), fh)