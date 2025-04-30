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
# ---------------------------------------------------------------------------

from fsrs import Scheduler, Card, Rating, DEFAULT_PARAMETERS
from datetime import datetime, timezone, timedelta
from typing    import Dict, Any, Optional
import json, os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filename='fsrs_debug.log',
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
            1 Again -- 4 Easy   (already mapped from UI)
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
        _, log = self.scheduler.review_card(
            card,
            Rating(rating_int),
            review_datetime=now
        )

        logging.info(f"After FSRS: stability={card.stability}, difficulty={card.difficulty}, state={card.state}, due={card.due}")
        
        # Calculate interval in days from now to the due date calculated by FSRS
        interval_days = 1  # Default fallback
        if card.due and now:
            # Convert both to UTC to ensure correct calculation
            if card.due.tzinfo is None:
                card.due = card.due.replace(tzinfo=timezone.utc)
            
            # Calculate interval in days
            interval_delta = card.due - now
            interval_days = max(1, interval_delta.days)
            
            logging.info(f"Calculated interval: {interval_days} days until next review at {card.due}")
        
        # Check if is_lapse attribute exists, otherwise calculate based on state transitions
        is_lapse = getattr(log, 'is_lapse', False)
        if not hasattr(log, 'is_lapse'):
            # Alternative method to determine if it's a lapse
            is_lapse = (rating_int == 1)  # Rating 1 (Again) is considered a lapse
        
        # Remove timezone info to avoid SQL Server issues
        next_review_date = None
        if card.due:
            next_review_date = card.due.replace(tzinfo=None)
        
        logging.info(f"Final values: stability={card.stability}, interval={interval_days}, is_lapse={is_lapse}")
        
        return {
            "stability" : card.stability,
            "difficulty": card.difficulty,
            "state"     : card.state,
            "due"       : next_review_date,   # Use the due date calculated by FSRS
            "interval"  : interval_days,      # integer days until next review
            "is_lapse"  : is_lapse,           # True if card was lapsed
        }

    # ──────────────────────────────────────────────────────────────────
    # Convenience helpers
    # ──────────────────────────────────────────────────────────────────
    def save_current_weights(self, path: str) -> None:
        """Dump the 19-parameter tuple to JSON (for backup or sharing)."""
        with open(path, "w") as fh:
            json.dump(list(self.scheduler.parameters), fh)