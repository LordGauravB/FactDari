# fsrs_engine.py  – FactDari wrapper around the **official** py-fsrs ≥ 5.0
#
# pip install py-fsrs         # scheduler
# pip install fsrs-optimizer  # (optional) weight-training utility
#
# The wrapper exposes one public method:
#     review(db_row, rating_int)  ->  dict   ← ready to WRITE BACK to SQL
#
# “rating_int” must be 0 (Again) / 1 (Hard) / 2 (Good) / 3 (Easy).
# Map your GUI buttons accordingly before calling it.
#
# ---------------------------------------------------------------------------

from fsrs import Scheduler, Card, Rating, DEFAULT_PARAMETERS      # :contentReference[oaicite:0]{index=0}
from datetime import datetime, timezone
from typing    import Dict, Any, Optional
import json, os


class FSRSEngine:
    """Thin shim that hides py-fsrs details from the rest of FactDari."""

    def __init__(self, weights_file: Optional[str] = None) -> None:
        # ------------------------------------------------------------------
        # 1) choose the 19 model parameters (aka “weights”)
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
            0 Again -- 3 Easy   (already mapped from UI)
        now
            datetime (UTC).  If omitted we use “right now”.

        Returns
        -------
        Dict with **all** fields you typically write back:

            stability, difficulty, state, due,
            interval (days as int), is_lapse (bool)
        """
        now = now or datetime.now(timezone.utc)

        # 1) re-hydrate a Card object from the DB row ──────────────────────
        card = Card()
        if db_row.get("stability")   is not None: card.stability  = float(db_row["stability"])
        if db_row.get("difficulty")  is not None: card.difficulty = float(db_row["difficulty"])
        if db_row.get("state")       is not None: card.state      = int(db_row["state"])

        due = db_row.get("due")
        if due:
            # ensure tz-aware UTC for FSRS
            if due.tzinfo is None:
                due = due.replace(tzinfo=timezone.utc)
            card.due = due.astimezone(timezone.utc)

        # 2) Let FSRS work its magic ──────────────────────────────────────
        _, log = self.scheduler.review_card(
            card,
            Rating(rating_int),
            review_datetime=now
        )                                                               # :contentReference[oaicite:1]{index=1}

        # 3) Return a flat dict for the SQL UPDATE clause ────────────────
        return {
            "stability" : card.stability,
            "difficulty": card.difficulty,
            "state"     : card.state,
            "due"       : card.due,          # timezone-aware UTC datetime
            "interval"  : log.interval.days, # integer days until next review
            "is_lapse"  : log.is_lapse,      # True if rating 0/1 transitioned card
        }

    # ──────────────────────────────────────────────────────────────────
    # Convenience helpers
    # ──────────────────────────────────────────────────────────────────
    def save_current_weights(self, path: str) -> None:
        """Dump the 19-parameter tuple to JSON (for backup or sharing)."""
        with open(path, "w") as fh:
            json.dump(list(self.scheduler.parameters), fh)
