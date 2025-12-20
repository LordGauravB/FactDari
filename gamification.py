import pyodbc
from datetime import datetime, date, timedelta
import config


class Gamification:
    """Lightweight gamification service backed by SQL Server.

    Stores a single user profile in GamificationProfile and a catalog of Achievements.
    """

    def __init__(self, conn_str: str):
        self.conn_str = conn_str

    def _get_or_create_profile_id(self, cur, conn=None) -> int:
        """Return the active profile id, inserting the default row if missing."""
        cur.execute("SELECT TOP 1 ProfileID FROM GamificationProfile ORDER BY ProfileID")
        row = cur.fetchone()
        if row:
            return int(row[0])
        cur.execute("INSERT INTO GamificationProfile (XP, Level) VALUES (0,1)")
        if conn:
            conn.commit()
        cur.execute("SELECT TOP 1 ProfileID FROM GamificationProfile ORDER BY ProfileID")
        row = cur.fetchone()
        return int(row[0]) if row else 1

    # --- Profile helpers ---
    def get_profile(self) -> dict:
        with pyodbc.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                pid = self._get_or_create_profile_id(cur, conn)
                cur.execute(
                    """
                    SELECT ProfileID, XP, Level, TotalReviews, TotalKnown, TotalFavorites,
                           TotalAdds, TotalEdits, TotalDeletes, TotalAITokens, TotalAICost,
                           CurrentStreak, LongestStreak, LastCheckinDate
                    FROM GamificationProfile
                    WHERE ProfileID = ?
                    """,
                    (pid,)
                )
                row = cur.fetchone()
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
                pid = self._get_or_create_profile_id(cur, conn)
                cur.execute(f"UPDATE GamificationProfile SET {field} = {field} + ? WHERE ProfileID = ?", (amount, pid))
                conn.commit()
                cur.execute(f"SELECT {field} FROM GamificationProfile WHERE ProfileID = ?", (pid,))
                return int(cur.fetchone()[0])

    def add_ai_usage(self, total_tokens: int = 0, cost: float = 0.0) -> dict:
        """Accumulate AI token/cost totals on the profile."""
        try:
            tokens_val = int(total_tokens or 0)
        except Exception:
            tokens_val = 0
        try:
            cost_val = float(cost or 0.0)
        except Exception:
            cost_val = 0.0

        if tokens_val <= 0 and cost_val <= 0.0:
            return self.get_profile()

        with pyodbc.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                pid = self._get_or_create_profile_id(cur, conn)
                cur.execute(
                    """
                    UPDATE GamificationProfile
                    SET TotalAITokens = ISNULL(TotalAITokens,0) + ?,
                        TotalAICost = ISNULL(TotalAICost,0) + ?
                    WHERE ProfileID = ?
                    """,
                    (tokens_val, cost_val, pid)
                )
                conn.commit()
        return self.get_profile()

    def add_question_usage(self, total_tokens: int = 0, cost: float = 0.0) -> dict:
        """Accumulate question generation token/cost totals on the profile."""
        try:
            tokens_val = int(total_tokens or 0)
        except Exception:
            tokens_val = 0
        try:
            cost_val = float(cost or 0.0)
        except Exception:
            cost_val = 0.0

        if tokens_val <= 0 and cost_val <= 0.0:
            return self.get_profile()

        with pyodbc.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                pid = self._get_or_create_profile_id(cur, conn)
                cur.execute(
                    """
                    UPDATE GamificationProfile
                    SET TotalQuestionTokens = ISNULL(TotalQuestionTokens,0) + ?,
                        TotalQuestionCost = ISNULL(TotalQuestionCost,0) + ?
                    WHERE ProfileID = ?
                    """,
                    (tokens_val, cost_val, pid)
                )
                conn.commit()
        return self.get_profile()

    def award_xp(self, amount: int) -> dict:
        if amount <= 0:
            return self.get_profile()
        with pyodbc.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                pid = self._get_or_create_profile_id(cur, conn)
                # Update XP for that profile
                cur.execute("UPDATE GamificationProfile SET XP = XP + ? WHERE ProfileID = ?", (amount, pid))
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
                pid = self._get_or_create_profile_id(cur, conn)
                cur.execute("UPDATE GamificationProfile SET Level = ? WHERE ProfileID = ?", (int(level), pid))
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
                pid = self._get_or_create_profile_id(cur, conn)
                cur.execute(
                    """
                    SELECT a.AchievementID, a.Code, a.Name, a.RewardXP
                    FROM Achievements a
                    LEFT JOIN AchievementUnlocks u ON u.AchievementID = a.AchievementID AND u.ProfileID = ?
                    WHERE a.Category = ? AND a.Threshold <= ? AND u.UnlockID IS NULL
                    ORDER BY a.Threshold
                    """,
                    (pid, category, int(current_value))
                )
                rows = cur.fetchall()
                for r in rows:
                    ach_id, code, name, reward = r
                    try:
                        cur.execute(
                            "INSERT INTO AchievementUnlocks (AchievementID, ProfileID) VALUES (?, ?)",
                            (ach_id, pid)
                        )
                        unlocked.append({'Code': code, 'Name': name, 'RewardXP': int(reward)})
                    except Exception:
                        # Likely a concurrent unlock; ignore
                        pass
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
                pid = self._get_or_create_profile_id(cur, conn)
                cur.execute(
                    """
                    SELECT ProfileID, XP, Level, TotalReviews, TotalKnown, TotalFavorites,
                           TotalAdds, TotalEdits, TotalDeletes, TotalAITokens, TotalAICost,
                           CurrentStreak, LongestStreak, LastCheckinDate
                    FROM GamificationProfile
                    WHERE ProfileID = ?
                    """,
                    (pid,)
                )
                row = cur.fetchone()

                cols = [d[0] for d in cur.description]
                prof = dict(zip(cols, row)) if row else {'ProfileID': pid}

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

                # Derive streak from actual review activity (authoritative)
                log_current, log_longest, log_last = self._calculate_streak_from_logs(cur, pid)
                new_streak = log_current
                longest = log_longest
                changed = False

                if log_last:
                    # Persist derived values
                    last_param = log_last
                    if isinstance(log_last, (datetime, date)):
                        # SQL Server accepts ISO date strings; avoid driver date binding issues
                        last_param = log_last.strftime("%Y-%m-%d")
                    cur.execute(
                        "UPDATE GamificationProfile SET CurrentStreak = ?, LongestStreak = ?, LastCheckinDate = ? WHERE ProfileID = ?",
                        (int(new_streak), int(longest), last_param, pid)
                    )
                    conn.commit()
                    # Award daily XP only once per new day
                    if last != today and log_last == today:
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
                prof['LastCheckinDate'] = log_last
                return {'profile': prof, 'unlocked': unlocked}

    def _calculate_streak_from_logs(self, cur, profile_id: int):
        """Compute current and longest streak from ReviewLogs (view/null actions only) for a profile."""
        try:
            cur.execute(
                """
                SELECT DISTINCT CONVERT(date, rl.ReviewDate) as ReviewDay
                FROM ReviewLogs rl
                LEFT JOIN ReviewSessions rs ON rs.SessionID = rl.SessionID
                WHERE (rl.Action IS NULL OR rl.Action = 'view')
                  AND (rs.ProfileID = ? OR rl.SessionID IS NULL)
                ORDER BY ReviewDay DESC
                """,
                (profile_id,)
            )
            rows = cur.fetchall()
        except Exception:
            return 0, 0, None

        dates = []
        for r in rows:
            d = r[0]
            if isinstance(d, datetime):
                d = d.date()
            elif not isinstance(d, date):
                try:
                    d = datetime.strptime(str(d), '%Y-%m-%d').date()
                except Exception:
                    continue
            dates.append(d)

        if not dates:
            return 0, 0, None

        today = date.today()
        longest = 1
        run = 1
        for i in range(1, len(dates)):
            if dates[i] == dates[i-1] - timedelta(days=1):
                run += 1
            else:
                run = 1
            if run > longest:
                longest = run

        current = 0
        if dates[0] in (today, today - timedelta(days=1)):
            current = 1
            for i in range(1, len(dates)):
                if dates[i] == dates[i-1] - timedelta(days=1):
                    current += 1
                else:
                    break

        last_review = dates[0]
        return current, longest, last_review

    def get_level_progress(self) -> dict:
        """Return progress metrics using stored Level (with gating) and current XP.
        Keys: level, xp, xp_into_level, xp_to_next, next_level_requirement
        """
        prof = self.get_profile()
        xp = int(prof.get('XP', 0))
        level = int(prof.get('Level', 1) or 1)

        # Early bands from config
        cfg = getattr(config, 'LEVELING_CONFIG', {})
        b1_end = int(cfg.get('band1_end', 4))
        b1_step = int(cfg.get('band1_step', 100))
        b2_end = int(cfg.get('band2_end', 9))
        b2_step = int(cfg.get('band2_step', 500))
        b3_end = int(cfg.get('band3_end', 14))
        b3_step = int(cfg.get('band3_step', 1000))
        b4_end = int(cfg.get('band4_end', 19))
        b4_step = int(cfg.get('band4_step', 5000))
        const_end = int(cfg.get('const_end', 98))
        total_target = int(cfg.get('total_xp_l100', 1_000_000))

        def early_band_step(lvl: int) -> int:
            if lvl <= b1_end:
                return b1_step
            if lvl <= b2_end:
                return b2_step
            if lvl <= b3_end:
                return b3_step
            if lvl <= b4_end:
                return b4_step
            return 0

        # Early sum (levels 1..b4_end)
        EARLY_SUM = sum(early_band_step(l) for l in range(1, b4_end + 1))
        # Constant band is levels (b4_end+1) .. const_end; final step is level 99
        const_start = b4_end + 1
        const_levels = max(0, const_end - const_start + 1)
        REMAINING = total_target - EARLY_SUM
        MID_CONST = REMAINING // (const_levels + 1) if (const_levels + 1) > 0 else 0

        def step_for_level(lvl: int) -> int:
            if lvl >= 100:
                return 0
            if lvl <= b4_end:
                return early_band_step(lvl)
            if lvl <= const_end:
                return int(MID_CONST)
            # lvl == 99: final step to fit total exactly
            sum_const = MID_CONST * const_levels
            final_needed = total_target - (EARLY_SUM + sum_const)
            return int(final_needed)

        # Total XP required to reach current stored level
        total_required = 0
        cur = 1
        while cur < level:
            total_required += step_for_level(cur)
            cur += 1
        need_next = step_for_level(level)
        xp_into = max(0, xp - total_required)
        if level < 100:
            xp_into = min(xp_into, need_next)
        xp_to_next = 0 if level >= 100 else max(0, need_next - xp_into)
        return {
            'level': level,
            'xp': xp,
            'xp_into_level': int(xp_into),
            'xp_to_next': int(xp_to_next),
            'next_level_requirement': 0 if level >= 100 else int(need_next)
        }

    def get_achievements_with_status(self) -> list:
        """List all achievements with unlock status and progress.
        ProgressCurrent derives from Facts for 'known' and 'favorites',
        and from profile lifetime counters for other categories.
        """
        prof = self.get_profile()
        pid = int(prof.get('ProfileID', 1) or 1)
        counters = {
            'known': 0,  # placeholder, will be computed from Facts
            'favorites': 0,  # placeholder, will be computed from Facts
            'reviews': int(prof.get('TotalReviews', 0) or 0),
            'adds': int(prof.get('TotalAdds', 0) or 0),
            'edits': int(prof.get('TotalEdits', 0) or 0),
            'deletes': int(prof.get('TotalDeletes', 0) or 0),
            'streak': int(prof.get('CurrentStreak', 0) or 0),
        }
        out = []
        with pyodbc.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                # Compute current states from Facts
                try:
                    cur.execute("SELECT COUNT(*) FROM ProfileFacts WHERE ProfileID = ? AND IsEasy = 1", (pid,))
                    counters['known'] = int(cur.fetchone()[0] or 0)
                except Exception:
                    counters['known'] = 0
                try:
                    cur.execute("SELECT COUNT(*) FROM ProfileFacts WHERE ProfileID = ? AND IsFavorite = 1", (pid,))
                    counters['favorites'] = int(cur.fetchone()[0] or 0)
                except Exception:
                    counters['favorites'] = 0

                cur.execute(
                    """
                    SELECT a.AchievementID, a.Code, a.Name, a.Category, a.Threshold, a.RewardXP,
                           u.UnlockID, u.UnlockDate, u.Notified
                    FROM Achievements a
                    LEFT JOIN AchievementUnlocks u ON u.AchievementID = a.AchievementID AND u.ProfileID = ?
                    ORDER BY a.Category, a.Threshold
                    """,
                    (pid,)
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
                pid = self._get_or_create_profile_id(cur, conn)
                # Update Notified for unlock rows that match codes and are not yet notified
                placeholders = ','.join('?' for _ in codes)
                q = (
                    "UPDATE u SET Notified = 1 FROM AchievementUnlocks u "
                    "JOIN Achievements a ON a.AchievementID = u.AchievementID "
                    f"WHERE a.Code IN ({placeholders}) AND u.ProfileID = ? AND u.Notified = 0"
                )
                cur.execute(q, tuple(codes) + (pid,))
                conn.commit()

    def mark_all_unnotified_as_notified(self):
        with pyodbc.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                pid = self._get_or_create_profile_id(cur, conn)
                cur.execute("UPDATE AchievementUnlocks SET Notified = 1 WHERE Notified = 0 AND ProfileID = ?", (pid,))
                conn.commit()

    # --- Internal helpers ---
    def _level_for_xp(self, xp: int) -> int:
        """Compute level from XP using banded + fitted progression to reach 1,000,000 at Level 100.
        - Levels 1–4: 100 per level
        - Levels 5–9: 500 per level
        - Levels 10–14: 1000 per level
        - Levels 15–19: 5000 per level
        - Levels 20–98: constant step computed to make total to Level 100 be 1,000,000
        - Level 99→100: final step is the exact remainder to reach 1,000,000
        Caps at 100.
        """
        cfg = getattr(config, 'LEVELING_CONFIG', {})
        b1_end = int(cfg.get('band1_end', 4))
        b1_step = int(cfg.get('band1_step', 100))
        b2_end = int(cfg.get('band2_end', 9))
        b2_step = int(cfg.get('band2_step', 500))
        b3_end = int(cfg.get('band3_end', 14))
        b3_step = int(cfg.get('band3_step', 1000))
        b4_end = int(cfg.get('band4_end', 19))
        b4_step = int(cfg.get('band4_step', 5000))
        const_end = int(cfg.get('const_end', 98))
        total_target = int(cfg.get('total_xp_l100', 1_000_000))

        def early_band_step(lvl: int) -> int:
            if lvl <= b1_end:
                return b1_step
            if lvl <= b2_end:
                return b2_step
            if lvl <= b3_end:
                return b3_step
            if lvl <= b4_end:
                return b4_step
            return 0

        EARLY_SUM = sum(early_band_step(l) for l in range(1, b4_end + 1))
        const_start = b4_end + 1
        const_levels = max(0, const_end - const_start + 1)
        MID_CONST = (total_target - EARLY_SUM) // (const_levels + 1) if (const_levels + 1) > 0 else 0

        def step_for_level(lvl: int) -> int:
            if lvl >= 100:
                return 0
            if lvl <= b4_end:
                return early_band_step(lvl)
            if lvl <= const_end:
                return int(MID_CONST)
            # lvl == 99
            sum_const = MID_CONST * const_levels
            final_needed = total_target - (EARLY_SUM + sum_const)
            return int(final_needed)

        remaining = int(xp)
        level = 1
        while level < 100:
            need = step_for_level(level)
            if remaining >= need:
                remaining -= need
                level += 1
            else:
                break
        return level

    def _all_achievements_unlocked(self) -> bool:
        with pyodbc.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                pid = self._get_or_create_profile_id(cur, conn)
                cur.execute("SELECT COUNT(*) FROM Achievements")
                total = int(cur.fetchone()[0])
                if total == 0:
                    return False
                cur.execute("SELECT COUNT(*) FROM AchievementUnlocks WHERE ProfileID = ?", (pid,))
                unlocked = int(cur.fetchone()[0])
                return unlocked >= total
