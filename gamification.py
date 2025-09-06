import pyodbc
from datetime import datetime, date, timedelta
import config


class Gamification:
    """Lightweight gamification service backed by SQL Server.

    Stores a single user profile in GamificationProfile and a catalog of Achievements.
    """

    def __init__(self, conn_str: str):
        self.conn_str = conn_str

    # --- Profile helpers ---
    def get_profile(self) -> dict:
        with pyodbc.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT TOP 1 ProfileID, XP, Level, TotalReviews, TotalKnown, TotalFavorites,
                           TotalAdds, TotalEdits, TotalDeletes, CurrentStreak, LongestStreak, LastCheckinDate
                    FROM GamificationProfile
                    ORDER BY ProfileID
                    """
                )
                row = cur.fetchone()
                if not row:
                    # Bootstrap a row if missing
                    cur.execute("INSERT INTO GamificationProfile (XP, Level) VALUES (0,1)")
                    conn.commit()
                    return {
                        'ProfileID': 1,
                        'XP': 0,
                        'Level': 1,
                        'TotalReviews': 0,
                        'TotalKnown': 0,
                        'TotalFavorites': 0,
                        'TotalAdds': 0,
                        'TotalEdits': 0,
                        'TotalDeletes': 0,
                        'CurrentStreak': 0,
                        'LongestStreak': 0,
                        'LastCheckinDate': None,
                    }
                cols = [d[0] for d in cur.description]
                return dict(zip(cols, row))

    def ensure_profile(self):
        # Forces creation by fetching
        _ = self.get_profile()

    # --- Counters and XP ---
    def increment_counter(self, field: str, amount: int = 1) -> int:
        if field not in (
            'TotalReviews', 'TotalKnown', 'TotalFavorites', 'TotalAdds', 'TotalEdits', 'TotalDeletes'
        ):
            return 0
        with pyodbc.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute(f"UPDATE GamificationProfile SET {field} = {field} + ?", (amount,))
                conn.commit()
                cur.execute(f"SELECT TOP 1 {field} FROM GamificationProfile")
                return int(cur.fetchone()[0])

    def award_xp(self, amount: int) -> dict:
        if amount <= 0:
            return self.get_profile()
        with pyodbc.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                # Update XP
                cur.execute("UPDATE GamificationProfile SET XP = XP + ?", (amount,))
                conn.commit()
        # Recompute level after XP change
        return self.recompute_level()

    def recompute_level(self) -> dict:
        profile = self.get_profile()
        xp = int(profile.get('XP', 0))
        level = self._level_for_xp(xp)

        # Gate level 100 based on achievements
        if level >= 100 and not self._all_achievements_unlocked():
            level = 99

        with pyodbc.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE GamificationProfile SET Level = ?", (int(level),))
                conn.commit()
        profile['Level'] = int(level)
        return profile

    # --- Achievements ---
    def unlock_achievements_if_needed(self, category: str, current_value: int) -> list:
        """Unlocks all achievements in a category up to current_value if not unlocked.
        Returns list of dicts for unlocked achievements.
        """
        unlocked = []
        with pyodbc.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT a.AchievementID, a.Code, a.Name, a.RewardXP
                    FROM Achievements a
                    LEFT JOIN AchievementUnlocks u ON u.AchievementID = a.AchievementID
                    WHERE a.Category = ? AND a.Threshold <= ? AND u.UnlockID IS NULL
                    ORDER BY a.Threshold
                    """,
                    (category, int(current_value))
                )
                rows = cur.fetchall()
                for r in rows:
                    ach_id, code, name, reward = r
                    cur.execute(
                        "INSERT INTO AchievementUnlocks (AchievementID) VALUES (?)",
                        (ach_id,)
                    )
                    unlocked.append({'Code': code, 'Name': name, 'RewardXP': int(reward)})
                if rows:
                    conn.commit()
        # Grant cumulative XP for all unlocked
        total_reward = sum(x['RewardXP'] for x in unlocked)
        if total_reward:
            self.award_xp(total_reward)
        return unlocked

    # --- Daily streaks & progress ---
    def daily_checkin(self) -> dict:
        """Update streak based on last check-in date.
        Returns dict with 'profile' and 'unlocked' keys.
        """
        unlocked = []
        with pyodbc.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT TOP 1 ProfileID, XP, Level, TotalReviews, TotalKnown, TotalFavorites,
                           TotalAdds, TotalEdits, TotalDeletes, CurrentStreak, LongestStreak, LastCheckinDate
                    FROM GamificationProfile
                    ORDER BY ProfileID
                    """
                )
                row = cur.fetchone()
                if not row:
                    cur.execute("INSERT INTO GamificationProfile (XP, Level, CurrentStreak, LongestStreak) VALUES (0,1,0,0)")
                    conn.commit()
                    cur.execute("SELECT TOP 1 ProfileID, XP, Level, TotalReviews, TotalKnown, TotalFavorites, TotalAdds, TotalEdits, TotalDeletes, CurrentStreak, LongestStreak, LastCheckinDate FROM GamificationProfile ORDER BY ProfileID")
                    row = cur.fetchone()

                cols = [d[0] for d in cur.description]
                prof = dict(zip(cols, row))

                today = date.today()
                last = prof.get('LastCheckinDate')
                # Normalize to date
                if isinstance(last, datetime):
                    last = last.date()
                elif last is not None and not isinstance(last, date):
                    try:
                        last = datetime.strptime(str(last), '%Y-%m-%d').date()
                    except Exception:
                        last = None

                # Determine new streak
                new_streak = int(prof.get('CurrentStreak', 0) or 0)
                longest = int(prof.get('LongestStreak', 0) or 0)
                changed = False

                if last == today:
                    # Already checked in today
                    pass
                else:
                    if last == today - timedelta(days=1):
                        new_streak = new_streak + 1 if new_streak > 0 else 1
                    else:
                        new_streak = 1
                    longest = max(longest, new_streak)
                    cur.execute(
                        "UPDATE GamificationProfile SET CurrentStreak = ?, LongestStreak = ?, LastCheckinDate = ?",
                        (int(new_streak), int(longest), today)
                    )
                    conn.commit()
                    changed = True

                # Award daily check-in XP (only when day advanced or first time)
                if changed:
                    daily_xp = int(config.XP_CONFIG.get('xp_daily_checkin', 0))
                    if daily_xp > 0:
                        # award_xp recomputes level
                        self.award_xp(daily_xp)

                    # Unlock streak achievements if thresholds crossed
                    unlocked = self.unlock_achievements_if_needed('streak', new_streak)

                # Return updated profile snapshot
                prof['CurrentStreak'] = new_streak
                prof['LongestStreak'] = longest
                prof['LastCheckinDate'] = today if changed else last
                return {'profile': prof, 'unlocked': unlocked}

    def get_level_progress(self) -> dict:
        """Return progress metrics for current XP/level.
        Keys: level, xp, xp_into_level, xp_to_next, next_level_requirement
        """
        prof = self.get_profile()
        xp = int(prof.get('XP', 0))
        # Recreate progression used in _level_for_xp
        level = 1
        need = 100
        remaining = xp
        while remaining >= need and level < 100:
            remaining -= need
            level += 1
            need += 50
        xp_into = remaining
        xp_to_next = (need - remaining) if level < 100 else 0
        return {
            'level': level,
            'xp': xp,
            'xp_into_level': xp_into,
            'xp_to_next': xp_to_next,
            'next_level_requirement': 0 if level >= 100 else need
        }

    def get_achievements_with_status(self) -> list:
        """List all achievements with unlock status and progress.
        Adds ProgressCurrent based on GamificationProfile counters.
        """
        prof = self.get_profile()
        counters = {
            'known': int(prof.get('TotalKnown', 0) or 0),
            'favorites': int(prof.get('TotalFavorites', 0) or 0),
            'reviews': int(prof.get('TotalReviews', 0) or 0),
            'adds': int(prof.get('TotalAdds', 0) or 0),
            'edits': int(prof.get('TotalEdits', 0) or 0),
            'deletes': int(prof.get('TotalDeletes', 0) or 0),
            'streak': int(prof.get('CurrentStreak', 0) or 0),
        }
        out = []
        with pyodbc.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT a.AchievementID, a.Code, a.Name, a.Category, a.Threshold, a.RewardXP,
                           u.UnlockID, u.UnlockDate, u.Notified
                    FROM Achievements a
                    LEFT JOIN AchievementUnlocks u ON u.AchievementID = a.AchievementID
                    ORDER BY a.Category, a.Threshold
                    """
                )
                rows = cur.fetchall()
                for r in rows:
                    (ach_id, code, name, category, threshold, reward,
                     unlock_id, unlock_date, notified) = r
                    progress = counters.get(str(category), 0)
                    out.append({
                        'AchievementID': int(ach_id),
                        'Code': code,
                        'Name': name,
                        'Category': category,
                        'Threshold': int(threshold),
                        'RewardXP': int(reward),
                        'Unlocked': unlock_id is not None,
                        'UnlockDate': unlock_date,
                        'Notified': bool(notified) if unlock_id is not None else False,
                        'ProgressCurrent': int(progress),
                    })
        return out

    def mark_unlocked_notified_by_codes(self, codes: list):
        if not codes:
            return
        with pyodbc.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                # Update Notified for unlock rows that match codes and are not yet notified
                q = (
                    "UPDATE u SET Notified = 1 FROM AchievementUnlocks u "
                    "JOIN Achievements a ON a.AchievementID = u.AchievementID "
                    f"WHERE a.Code IN ({','.join('?' for _ in codes)}) AND u.Notified = 0"
                )
                cur.execute(q, tuple(codes))
                conn.commit()

    def mark_all_unnotified_as_notified(self):
        with pyodbc.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE AchievementUnlocks SET Notified = 1 WHERE Notified = 0")
                conn.commit()

    # --- Internal helpers ---
    def _level_for_xp(self, xp: int) -> int:
        """Compute level from XP with gently increasing requirements.
        Level 1 at 0 XP. To reach next levels: 100, 150, 200, 250, ... (arith. progression).
        Caps at 100.
        """
        level = 1
        need = 100
        remaining = int(xp)
        while remaining >= need and level < 100:
            remaining -= need
            level += 1
            need += 50  # increase requirement each level
        return level

    def _all_achievements_unlocked(self) -> bool:
        with pyodbc.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM Achievements")
                total = int(cur.fetchone()[0])
                if total == 0:
                    return False
                cur.execute("SELECT COUNT(*) FROM AchievementUnlocks")
                unlocked = int(cur.fetchone()[0])
                return unlocked >= total
