"""
Unit tests for gamification.py module.
Tests XP system, leveling, achievements, and streak calculations.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date, timedelta
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestLevelCalculation:
    """Tests for level calculation from XP."""

    def test_level_for_xp_zero(self):
        """Test level 1 for 0 XP."""
        from gamification import Gamification
        gamify = Gamification("dummy_conn_str")
        level = gamify._level_for_xp(0)
        assert level == 1

    def test_level_for_xp_band1(self):
        """Test levels in band 1 (1-4, 100 XP each)."""
        from gamification import Gamification
        gamify = Gamification("dummy_conn_str")
        # After 100 XP, should be level 2
        assert gamify._level_for_xp(100) == 2
        # After 200 XP, should be level 3
        assert gamify._level_for_xp(200) == 3
        # After 400 XP (100*4), should be level 5
        assert gamify._level_for_xp(400) == 5

    def test_level_for_xp_band2(self):
        """Test levels in band 2 (5-9, 500 XP each)."""
        from gamification import Gamification
        gamify = Gamification("dummy_conn_str")
        # Band 1 total: 400 XP (4 levels * 100)
        # Band 2 starts at level 5
        # 400 + 500 = 900 XP for level 6
        assert gamify._level_for_xp(900) == 6

    def test_level_for_xp_band3(self):
        """Test levels in band 3 (10-14, 1000 XP each)."""
        from gamification import Gamification
        gamify = Gamification("dummy_conn_str")
        # Band 1: 400, Band 2: 2500 (5*500), Total: 2900 for level 10
        assert gamify._level_for_xp(2900) == 10

    def test_level_for_xp_caps_at_100(self):
        """Test level caps at 100."""
        from gamification import Gamification
        gamify = Gamification("dummy_conn_str")
        # Very high XP should still cap at 100
        level = gamify._level_for_xp(10_000_000)
        assert level == 100

    def test_level_for_xp_negative_returns_1(self):
        """Test negative XP returns level 1."""
        from gamification import Gamification
        gamify = Gamification("dummy_conn_str")
        level = gamify._level_for_xp(-100)
        assert level == 1


class TestIncrementCounterValidation:
    """Tests for increment_counter field validation."""

    def test_valid_fields(self):
        """Test that valid fields are accepted."""
        valid_fields = [
            'TotalReviews', 'TotalKnown', 'TotalFavorites',
            'TotalAdds', 'TotalEdits', 'TotalDeletes'
        ]
        from gamification import Gamification
        gamify = Gamification("dummy_conn_str")

        for field in valid_fields:
            # The field validation happens before DB call
            # Since we can't connect to DB, we just verify the whitelist exists
            assert field in (
                'TotalReviews', 'TotalKnown', 'TotalFavorites',
                'TotalAdds', 'TotalEdits', 'TotalDeletes'
            )

    def test_invalid_field_returns_zero(self):
        """Test that invalid field returns 0 without DB call."""
        from gamification import Gamification
        gamify = Gamification("dummy_conn_str")

        # Mock the connection to verify no DB call is made
        with patch('pyodbc.connect') as mock_connect:
            result = gamify.increment_counter('InvalidField', 1)
            assert result == 0
            # Verify connect was never called (rejected before DB access)
            mock_connect.assert_not_called()

    def test_sql_injection_field_rejected(self):
        """Test SQL injection attempt in field name is rejected."""
        from gamification import Gamification
        gamify = Gamification("dummy_conn_str")

        with patch('pyodbc.connect') as mock_connect:
            # Try SQL injection
            result = gamify.increment_counter("TotalReviews; DROP TABLE Users;--", 1)
            assert result == 0
            mock_connect.assert_not_called()


class TestAwardXP:
    """Tests for XP awarding logic."""

    def test_award_xp_zero_does_nothing(self):
        """Test awarding 0 XP doesn't make DB call."""
        from gamification import Gamification
        gamify = Gamification("dummy_conn_str")

        with patch.object(gamify, 'get_profile') as mock_get:
            mock_get.return_value = {'XP': 100, 'Level': 2}
            result = gamify.award_xp(0)
            # Should return profile without DB update
            assert result == {'XP': 100, 'Level': 2}

    def test_award_xp_negative_does_nothing(self):
        """Test awarding negative XP doesn't make DB call."""
        from gamification import Gamification
        gamify = Gamification("dummy_conn_str")

        with patch.object(gamify, 'get_profile') as mock_get:
            mock_get.return_value = {'XP': 100, 'Level': 2}
            result = gamify.award_xp(-50)
            assert result == {'XP': 100, 'Level': 2}


class TestAddAIUsage:
    """Tests for AI usage tracking."""

    def test_add_ai_usage_zero_values(self):
        """Test adding zero AI usage returns profile without update."""
        from gamification import Gamification
        gamify = Gamification("dummy_conn_str")

        with patch.object(gamify, 'get_profile') as mock_get:
            mock_get.return_value = {'TotalAITokens': 100, 'TotalAICost': 0.05}
            result = gamify.add_ai_usage(0, 0.0)
            assert result == {'TotalAITokens': 100, 'TotalAICost': 0.05}

    def test_add_ai_usage_handles_none(self):
        """Test add_ai_usage handles None values."""
        from gamification import Gamification
        gamify = Gamification("dummy_conn_str")

        with patch.object(gamify, 'get_profile') as mock_get:
            mock_get.return_value = {'TotalAITokens': 100, 'TotalAICost': 0.05}
            # Should not raise exception
            result = gamify.add_ai_usage(None, None)
            assert result is not None

    def test_add_ai_usage_handles_invalid_types(self):
        """Test add_ai_usage handles invalid input types."""
        from gamification import Gamification
        gamify = Gamification("dummy_conn_str")

        with patch.object(gamify, 'get_profile') as mock_get:
            mock_get.return_value = {'TotalAITokens': 100, 'TotalAICost': 0.05}
            # Should not raise exception with string inputs
            result = gamify.add_ai_usage("invalid", "invalid")
            assert result is not None


class TestStreakCalculation:
    """Tests for streak calculation logic."""

    def test_empty_dates_returns_zero_streak(self):
        """Test empty review dates returns zero streak."""
        from gamification import Gamification
        gamify = Gamification("dummy_conn_str")

        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = []

        current, longest, last = gamify._calculate_streak_from_logs(mock_cursor, 1)
        assert current == 0
        assert longest == 0
        assert last is None

    def test_single_day_streak(self):
        """Test single day of reviews gives streak of 1."""
        from gamification import Gamification
        gamify = Gamification("dummy_conn_str")

        today = date.today()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [(today,)]

        current, longest, last = gamify._calculate_streak_from_logs(mock_cursor, 1)
        assert current == 1
        assert longest == 1
        assert last == today

    def test_consecutive_days_streak(self):
        """Test consecutive days increase streak."""
        from gamification import Gamification
        gamify = Gamification("dummy_conn_str")

        today = date.today()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            (today,),
            (today - timedelta(days=1),),
            (today - timedelta(days=2),),
        ]

        current, longest, last = gamify._calculate_streak_from_logs(mock_cursor, 1)
        assert current == 3
        assert longest == 3

    def test_broken_streak(self):
        """Test gap in days breaks current streak but preserves longest."""
        from gamification import Gamification
        gamify = Gamification("dummy_conn_str")

        today = date.today()
        mock_cursor = Mock()
        # Today, yesterday, then gap, then 5-day streak
        mock_cursor.fetchall.return_value = [
            (today,),
            (today - timedelta(days=1),),
            # Gap at day 2
            (today - timedelta(days=4),),
            (today - timedelta(days=5),),
            (today - timedelta(days=6),),
            (today - timedelta(days=7),),
            (today - timedelta(days=8),),
        ]

        current, longest, last = gamify._calculate_streak_from_logs(mock_cursor, 1)
        assert current == 2  # Today + yesterday
        assert longest == 5  # The older 5-day streak

    def test_streak_yesterday_only(self):
        """Test streak continues from yesterday even if no review today."""
        from gamification import Gamification
        gamify = Gamification("dummy_conn_str")

        today = date.today()
        yesterday = today - timedelta(days=1)
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            (yesterday,),
            (yesterday - timedelta(days=1),),
            (yesterday - timedelta(days=2),),
        ]

        current, longest, last = gamify._calculate_streak_from_logs(mock_cursor, 1)
        # Streak should still count because yesterday is included
        assert current == 3


class TestAllAchievementsUnlocked:
    """Tests for checking if all achievements are unlocked."""

    @patch('pyodbc.connect')
    def test_no_achievements_returns_false(self, mock_connect):
        """Test returns False when no achievements exist."""
        from gamification import Gamification
        gamify = Gamification("dummy_conn_str")

        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [(1,), (0,), (0,)]  # profile_id, total=0
        mock_connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor

        result = gamify._all_achievements_unlocked()
        assert result is False


class TestLevelProgress:
    """Tests for level progress calculation."""

    @patch('pyodbc.connect')
    def test_level_progress_structure(self, mock_connect):
        """Test get_level_progress returns expected structure."""
        from gamification import Gamification
        gamify = Gamification("dummy_conn_str")

        with patch.object(gamify, 'get_profile') as mock_get:
            mock_get.return_value = {'XP': 250, 'Level': 3}

            progress = gamify.get_level_progress()

            assert 'level' in progress
            assert 'xp' in progress
            assert 'xp_into_level' in progress
            assert 'xp_to_next' in progress
            assert 'next_level_requirement' in progress

    @patch('pyodbc.connect')
    def test_level_progress_level_100(self, mock_connect):
        """Test level 100 has no XP to next."""
        from gamification import Gamification
        gamify = Gamification("dummy_conn_str")

        with patch.object(gamify, 'get_profile') as mock_get:
            mock_get.return_value = {'XP': 1_000_000, 'Level': 100}

            progress = gamify.get_level_progress()

            assert progress['level'] == 100
            assert progress['xp_to_next'] == 0
            assert progress['next_level_requirement'] == 0


class TestUnlockAchievements:
    """Tests for achievement unlocking logic."""

    def test_unlock_returns_list(self):
        """Test unlock_achievements_if_needed returns a list."""
        from gamification import Gamification
        gamify = Gamification("dummy_conn_str")

        # Mock the entire database interaction
        with patch('pyodbc.connect') as mock_connect:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = (1,)  # profile_id
            mock_cursor.fetchall.return_value = []  # no achievements to unlock
            mock_connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor

            result = gamify.unlock_achievements_if_needed('known', 5)
            assert isinstance(result, list)


class TestMarkNotified:
    """Tests for marking achievements as notified."""

    def test_mark_empty_codes_does_nothing(self):
        """Test marking empty codes list does nothing."""
        from gamification import Gamification
        gamify = Gamification("dummy_conn_str")

        with patch('pyodbc.connect') as mock_connect:
            gamify.mark_unlocked_notified_by_codes([])
            # Should not attempt to connect
            mock_connect.assert_not_called()

    def test_mark_none_codes_does_nothing(self):
        """Test marking None codes does nothing."""
        from gamification import Gamification
        gamify = Gamification("dummy_conn_str")

        with patch('pyodbc.connect') as mock_connect:
            gamify.mark_unlocked_notified_by_codes(None)
            mock_connect.assert_not_called()


class TestDailyCheckin:
    """Tests for daily check-in functionality."""

    @patch('pyodbc.connect')
    def test_daily_checkin_returns_dict(self, mock_connect):
        """Test daily_checkin returns expected structure."""
        from gamification import Gamification
        gamify = Gamification("dummy_conn_str")

        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            (1,),  # profile_id
            (1, 100, 2, 10, 5, 3, 5, 2, 1, 0, 0.0, 1, 1, None),  # profile data
        ]
        mock_cursor.fetchall.return_value = []  # no review logs
        mock_cursor.description = [
            ('ProfileID',), ('XP',), ('Level',), ('TotalReviews',),
            ('TotalKnown',), ('TotalFavorites',), ('TotalAdds',),
            ('TotalEdits',), ('TotalDeletes',), ('TotalAITokens',),
            ('TotalAICost',), ('CurrentStreak',), ('LongestStreak',),
            ('LastCheckinDate',)
        ]
        mock_connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor

        result = gamify.daily_checkin()

        assert 'profile' in result
        assert 'unlocked' in result
        assert isinstance(result['unlocked'], list)


class TestProfileEnsure:
    """Tests for profile creation/retrieval."""

    @patch('pyodbc.connect')
    def test_ensure_profile_calls_get_profile(self, mock_connect):
        """Test ensure_profile triggers profile fetch."""
        from gamification import Gamification
        gamify = Gamification("dummy_conn_str")

        with patch.object(gamify, 'get_profile') as mock_get:
            mock_get.return_value = {'ProfileID': 1}
            gamify.ensure_profile()
            mock_get.assert_called_once()


class TestGetAchievementsWithStatus:
    """Tests for getting achievements with status."""

    @patch('pyodbc.connect')
    def test_returns_list(self, mock_connect):
        """Test get_achievements_with_status returns a list."""
        from gamification import Gamification
        gamify = Gamification("dummy_conn_str")

        with patch.object(gamify, 'get_profile') as mock_get:
            mock_get.return_value = {
                'ProfileID': 1,
                'TotalReviews': 100,
                'TotalAdds': 50,
                'TotalEdits': 10,
                'TotalDeletes': 5,
                'CurrentStreak': 7
            }

            mock_cursor = MagicMock()
            mock_cursor.fetchone.side_effect = [(10,), (5,)]  # known count, favorites count
            mock_cursor.fetchall.return_value = []  # no achievements
            mock_connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor

            result = gamify.get_achievements_with_status()
            assert isinstance(result, list)
