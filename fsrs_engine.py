# fsrs_engine.py  – FactDari wrapper around the **official** py-fsrs ≥ 5.0
#
# pip install py-fsrs         # scheduler
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
logging.basicConfig(level=logging.INFO, 
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

        if weights_file and os.path.exists(weights_file):
            try:
                with open(weights_file, "r") as fh:
                    custom = json.load(fh)
                if isinstance(custom, list) and len(custom) == len(DEFAULT_PARAMETERS):
                    parameters = custom
                else:
                    print("[FSRS] ⚠️  Ignoring weights file — wrong length.")
            except Exception as exc:                                 # noqa: BLE001
                print(f"[FSRS] ⚠️  Could not load '{weights_file}': {exc}")

        # ------------------------------------------------------------------
        # 2) build the scheduler
        # ------------------------------------------------------------------
        self.scheduler = Scheduler(parameters)                       # uses defaults:
                                                                     # desired_retention=0.9, etc.

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
        
        # 1) re-hydrate a Card object from the DB row
        card = Card()
        if db_row.get("stability")   is not None: card.stability  = float(db_row["stability"])
        if db_row.get("difficulty")  is not None: card.difficulty = float(db_row["difficulty"])
        if db_row.get("state")       is not None: card.state      = int(db_row["state"])

        logging.info(f"Initial card state: stability={card.stability}, difficulty={card.difficulty}, state={card.state}")
        
        due = db_row.get("due")
        if due:
            # ensure tz-aware UTC for FSRS
            if due.tzinfo is None:
                due = due.replace(tzinfo=timezone.utc)
            card.due = due.astimezone(timezone.utc)
            logging.info(f"Initial due date: {card.due}")

        # 2) Let FSRS work its magic
        scheduling_result = self.scheduler.review_card(
            card,
            Rating(rating_int),
            review_datetime=now
        )
        
        # In py-fsrs 5.0+, review_card returns a tuple (scheduling_info, log)
        # where scheduling_info has the next card state information
        # The original card object is also updated in-place
        log = scheduling_result[1]  # The second element is the log
        
        # Set the next review interval based on FSRS scheduling
        # Make sure we use a minimum interval of 1 day
        if card.due <= now:
            # If the card is currently overdue, calculate from now
            interval_days = 1  # Minimum interval
        else:
            # Calculate days between now and the due date
            interval_days = max(1, (card.due - now).days)
        
        # Let FSRS handle stability calculations naturally
        # No manual adjustments to stay true to the algorithm
        
        # Get proper due date from FSRS scheduling
        next_review_date = card.due
        
        # Log the actual processed FSRS values
        logging.info(f"After FSRS: stability={card.stability}, difficulty={card.difficulty}, state={card.state}")
        logging.info(f"FSRS scheduled: due={card.due}, interval={interval_days} days")
        
        # Remove timezone info to avoid SQL Server issues while preserving the same datetime
        next_review_date = next_review_date.replace(tzinfo=None)
        
        # Check if this review is a lapse (rating is "Again")
        is_lapse = (rating_int == 1)
        
        return {
            "stability" : card.stability,
            "difficulty": card.difficulty,
            "state"     : card.state,
            "due"       : next_review_date,
            "interval"  : interval_days,
            "is_lapse"  : is_lapse,
        }

    # ──────────────────────────────────────────────────────────────────
    # Convenience helpers
    # ──────────────────────────────────────────────────────────────────
    def save_current_weights(self, path: str) -> None:
        """Dump the 19-parameter tuple to JSON (for backup or sharing)."""
        with open(path, "w") as fh:
            json.dump(list(self.scheduler.parameters), fh)