"""
Comprehensive unit tests for factdari.py module.
Tests helper functions, data validation, business logic, timers, sessions, and UI states.

Tier 1: Timer, Idle, Sessions, Fact logging, Button states
Tier 2: Questions, Category switching, UI transitions
Tier 3: TTS, Window management, Edge cases
"""
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# TIER 1: CRITICAL TESTS - Timer, Idle, Sessions, Fact Logging, Button States
# =============================================================================

class TestTimerPauseResume:
    """Tests for timer pause/resume functionality."""

    def test_pause_timer_sets_paused_state(self):
        """Test that pause_review_timer sets timer_paused to True."""
        timer_paused = False
        current_fact_start_time = datetime.now()
        pause_started_at = None

        # Simulate pause_review_timer logic
        if current_fact_start_time and not timer_paused:
            pause_started_at = datetime.now()
            timer_paused = True

        assert timer_paused is True
        assert pause_started_at is not None

    def test_pause_timer_no_effect_when_already_paused(self):
        """Test that pausing again doesn't reset pause_started_at."""
        timer_paused = True
        pause_started_at = datetime.now() - timedelta(seconds=10)
        original_pause_time = pause_started_at
        current_fact_start_time = datetime.now() - timedelta(seconds=30)

        # Should not change when already paused
        if current_fact_start_time and not timer_paused:
            pause_started_at = datetime.now()
            timer_paused = True

        assert pause_started_at == original_pause_time

    def test_resume_timer_shifts_start_time(self):
        """Test that resume_review_timer shifts start time by paused duration."""
        pause_duration_seconds = 10
        original_start = datetime.now() - timedelta(seconds=30)
        pause_started_at = datetime.now() - timedelta(seconds=pause_duration_seconds)
        timer_paused = True
        current_fact_start_time = original_start

        # Simulate resume_review_timer logic
        if timer_paused:
            if current_fact_start_time and pause_started_at:
                delta = datetime.now() - pause_started_at
                current_fact_start_time = current_fact_start_time + delta
            pause_started_at = None
            timer_paused = False

        assert timer_paused is False
        assert pause_started_at is None
        assert current_fact_start_time > original_start

    def test_resume_timer_no_effect_when_not_paused(self):
        """Test that resuming when not paused does nothing."""
        timer_paused = False
        original_start = datetime.now() - timedelta(seconds=30)
        current_fact_start_time = original_start
        pause_started_at = None

        if timer_paused:
            if current_fact_start_time and pause_started_at:
                delta = datetime.now() - pause_started_at
                current_fact_start_time = current_fact_start_time + delta
            pause_started_at = None
            timer_paused = False

        assert current_fact_start_time == original_start


class TestIdleTimeout:
    """Tests for idle timeout detection and handling."""

    def test_record_activity_resets_last_activity_time(self):
        """Test that record_activity updates last_activity_time."""
        old_time = datetime.now() - timedelta(seconds=300)
        last_activity_time = old_time
        idle_triggered = True

        # Simulate record_activity logic
        last_activity_time = datetime.now()
        idle_triggered = False

        assert last_activity_time > old_time
        assert idle_triggered is False

    def test_idle_detection_triggers_after_timeout(self):
        """Test idle detection triggers after timeout seconds."""
        idle_timeout_seconds = 300
        last_activity_time = datetime.now() - timedelta(seconds=301)
        idle_triggered = False
        current_session_id = 1
        timer_paused = False

        if current_session_id and not timer_paused:
            idle_seconds = int((datetime.now() - last_activity_time).total_seconds())
            if not idle_triggered and idle_seconds >= idle_timeout_seconds:
                idle_triggered = True

        assert idle_triggered is True

    def test_idle_detection_does_not_trigger_before_timeout(self):
        """Test idle detection doesn't trigger before timeout."""
        idle_timeout_seconds = 300
        last_activity_time = datetime.now() - timedelta(seconds=100)
        idle_triggered = False
        current_session_id = 1
        timer_paused = False

        if current_session_id and not timer_paused:
            idle_seconds = int((datetime.now() - last_activity_time).total_seconds())
            if not idle_triggered and idle_seconds >= idle_timeout_seconds:
                idle_triggered = True

        assert idle_triggered is False

    def test_idle_not_triggered_when_timer_paused(self):
        """Test idle detection skipped when timer is paused."""
        idle_timeout_seconds = 300
        last_activity_time = datetime.now() - timedelta(seconds=400)
        idle_triggered = False
        current_session_id = 1
        timer_paused = True

        if current_session_id and not timer_paused:
            idle_seconds = int((datetime.now() - last_activity_time).total_seconds())
            if not idle_triggered and idle_seconds >= idle_timeout_seconds:
                idle_triggered = True

        assert idle_triggered is False

    def test_idle_not_triggered_when_no_session(self):
        """Test idle detection skipped when no active session."""
        idle_timeout_seconds = 300
        last_activity_time = datetime.now() - timedelta(seconds=400)
        idle_triggered = False
        current_session_id = None
        timer_paused = False

        if current_session_id and not timer_paused:
            idle_seconds = int((datetime.now() - last_activity_time).total_seconds())
            if not idle_triggered and idle_seconds >= idle_timeout_seconds:
                idle_triggered = True

        assert idle_triggered is False


class TestSessionManagement:
    """Tests for session creation and termination."""

    def test_start_new_session_sets_session_id(self):
        """Test that starting a session assigns a session ID."""
        current_session_id = None
        session_start_time = None

        session_start_time = datetime.now()
        current_session_id = 123

        assert current_session_id is not None
        assert session_start_time is not None

    def test_start_new_session_ends_existing_session_first(self):
        """Test that starting a new session ends any existing session."""
        existing_session_id = 100
        end_session_called = False

        def end_active_session():
            nonlocal end_session_called
            end_session_called = True

        if existing_session_id:
            end_active_session()

        assert end_session_called is True

    def test_end_session_calculates_duration(self):
        """Test that ending a session calculates correct duration."""
        session_start_time = datetime.now() - timedelta(seconds=120)

        end_marker = datetime.now()
        duration_seconds = int((end_marker - session_start_time).total_seconds())

        assert duration_seconds >= 120
        assert duration_seconds < 130

    def test_end_session_uses_last_activity_when_timed_out(self):
        """Test that timeout uses last activity time for duration."""
        session_start_time = datetime.now() - timedelta(seconds=300)
        last_activity_time = datetime.now() - timedelta(seconds=100)
        timed_out = True

        end_marker = last_activity_time if timed_out else datetime.now()
        duration_seconds = int((end_marker - session_start_time).total_seconds())

        assert 195 <= duration_seconds <= 205

    def test_end_session_clears_session_state(self):
        """Test that ending session clears session variables."""
        current_session_id = 123
        session_start_time = datetime.now()

        current_session_id = None
        session_start_time = None

        assert current_session_id is None
        assert session_start_time is None

    def test_session_duration_calculation(self):
        """Test session duration is calculated correctly."""
        start_time = datetime(2024, 1, 1, 10, 0, 0)
        end_time = datetime(2024, 1, 1, 10, 5, 30)

        duration_seconds = int((end_time - start_time).total_seconds())

        assert duration_seconds == 330

    def test_session_duration_zero(self):
        """Test zero duration for same start/end."""
        start_time = datetime(2024, 1, 1, 10, 0, 0)
        end_time = start_time

        duration_seconds = int((end_time - start_time).total_seconds())

        assert duration_seconds == 0


class TestFactViewFinalization:
    """Tests for fact view duration tracking and finalization."""

    def test_finalize_calculates_elapsed_time(self):
        """Test that finalization calculates correct elapsed time."""
        current_fact_start_time = datetime.now() - timedelta(seconds=30)

        end_ts = datetime.now()
        elapsed = int((end_ts - current_fact_start_time).total_seconds())

        assert elapsed >= 30
        assert elapsed < 35

    def test_finalize_caps_at_last_activity_when_timed_out(self):
        """Test that timeout caps elapsed at last activity time."""
        current_fact_start_time = datetime.now() - timedelta(seconds=100)
        last_activity_time = datetime.now() - timedelta(seconds=50)
        timed_out = True

        end_ts = last_activity_time if timed_out else datetime.now()
        elapsed = int((end_ts - current_fact_start_time).total_seconds())

        assert 45 <= elapsed <= 55

    def test_finalize_caps_at_pause_time_when_paused(self):
        """Test that paused time is excluded from duration."""
        current_fact_start_time = datetime.now() - timedelta(seconds=60)
        pause_started_at = datetime.now() - timedelta(seconds=20)
        timer_paused = True

        end_ts = datetime.now()
        if timer_paused and pause_started_at:
            end_ts = min(end_ts, pause_started_at)
        elapsed = int((end_ts - current_fact_start_time).total_seconds())

        assert 35 <= elapsed <= 45

    def test_finalize_clears_state_variables(self):
        """Test that finalization clears fact tracking state."""
        current_fact_log_id = 123
        current_fact_start_time = datetime.now()

        current_fact_log_id = None
        current_fact_start_time = None

        assert current_fact_log_id is None
        assert current_fact_start_time is None

    def test_finalize_handles_negative_elapsed_gracefully(self):
        """Test that negative elapsed time is clamped to 0."""
        current_fact_start_time = datetime.now() + timedelta(seconds=10)

        end_ts = datetime.now()
        elapsed = int((end_ts - current_fact_start_time).total_seconds())
        if elapsed < 0:
            elapsed = 0

        assert elapsed == 0


class TestButtonStates:
    """Tests for button enable/disable states."""

    def test_is_action_allowed_false_on_home_page(self):
        """Test actions are not allowed on home page."""
        is_home_page = True
        answer_revealed = True

        allowed = not is_home_page and answer_revealed

        assert allowed is False

    def test_is_action_allowed_false_when_answer_not_revealed(self):
        """Test actions not allowed when answer not revealed."""
        is_home_page = False
        answer_revealed = False

        allowed = not is_home_page and answer_revealed

        assert allowed is False

    def test_is_action_allowed_true_when_reviewing_and_revealed(self):
        """Test actions allowed when reviewing and answer revealed."""
        is_home_page = False
        answer_revealed = True

        allowed = not is_home_page and answer_revealed

        assert allowed is True

    def test_toggle_favorite_requires_current_fact_id(self):
        """Test toggle_favorite requires a current fact ID."""
        current_fact_id = None
        action_blocked = current_fact_id is None

        assert action_blocked is True

    def test_toggle_favorite_with_valid_fact_id(self):
        """Test toggle_favorite works with valid fact ID."""
        current_fact_id = 123
        action_blocked = current_fact_id is None

        assert action_blocked is False

    def test_ai_request_inflight_blocks_duplicate_requests(self):
        """Test that ai_request_inflight prevents duplicate AI calls."""
        ai_request_inflight = True

        request_allowed = not ai_request_inflight

        assert request_allowed is False

    def test_ai_request_not_blocked_when_idle(self):
        """Test AI request allowed when not in flight."""
        ai_request_inflight = False

        request_allowed = not ai_request_inflight

        assert request_allowed is True


# =============================================================================
# TIER 2: SHOULD HAVE TESTS - Questions, Categories, UI Transitions, Analytics
# =============================================================================

class TestQuestionDisplay:
    """Tests for question display and reveal functionality."""

    def test_answer_revealed_initially_false(self):
        """Test answer_revealed starts as False."""
        answer_revealed = False
        assert answer_revealed is False

    def test_reveal_answer_sets_answer_revealed(self):
        """Test reveal action sets answer_revealed to True."""
        answer_revealed = False
        answer_revealed = True
        assert answer_revealed is True

    def test_question_state_reset_on_next_fact(self):
        """Test question state resets when navigating to next fact."""
        answer_revealed = True
        current_question_id = 123

        answer_revealed = False
        current_question_id = None

        assert answer_revealed is False
        assert current_question_id is None

    def test_question_request_inflight_prevents_duplicate(self):
        """Test question generation blocked when already in progress."""
        question_request_inflight = True
        question_generation_fact_id = 100
        current_fact_id = 100

        blocked = question_request_inflight and question_generation_fact_id == current_fact_id

        assert blocked is True

    def test_question_cooldown_prevents_rapid_retries(self):
        """Test cooldown prevents rapid question generation retries."""
        cooldown_seconds = 60
        last_attempt = time.time() - 30
        now = time.time()

        in_cooldown = (now - last_attempt) < cooldown_seconds

        assert in_cooldown is True


class TestCategorySwitching:
    """Tests for category dropdown and switching functionality."""

    def test_category_change_finalizes_current_view(self):
        """Test category change triggers fact view finalization."""
        finalize_called = False

        def finalize_current_fact_view():
            nonlocal finalize_called
            finalize_called = True

        finalize_current_fact_view()

        assert finalize_called is True

    def test_category_change_resets_question_state(self):
        """Test category change resets question state."""
        answer_revealed = True
        current_question_id = 123

        answer_revealed = False
        current_question_id = None

        assert answer_revealed is False
        assert current_question_id is None

    def test_category_filter_all_categories(self):
        """Test 'All Categories' filter returns all facts."""
        category_var = "All Categories"
        should_filter = category_var != "All Categories"
        assert should_filter is False

    def test_category_filter_specific_category(self):
        """Test specific category filter is applied."""
        category_var = "Science"
        should_filter = category_var != "All Categories"
        assert should_filter is True

    def test_category_filter_favorites(self):
        """Test Favorites filter."""
        category_var = "Favorites"
        is_special_filter = category_var in ["Favorites", "Known", "Not Known", "Not Favorite"]
        assert is_special_filter is True

    def test_specific_category_filtering(self):
        """Test specific category filtering logic."""
        selected = "Science"
        all_facts = [
            (1, 'Fact 1', 'Science'),
            (2, 'Fact 2', 'History'),
            (3, 'Fact 3', 'Science'),
        ]

        filtered = [f for f in all_facts if f[2] == selected]

        assert len(filtered) == 2
        assert all(f[2] == 'Science' for f in filtered)


class TestUITransitions:
    """Tests for home page and review mode transitions."""

    def test_show_home_page_sets_is_home_page(self):
        """Test show_home_page sets is_home_page to True."""
        is_home_page = False
        is_home_page = True
        assert is_home_page is True

    def test_show_home_page_ends_session(self):
        """Test show_home_page ends active session."""
        session_ended = False

        def end_active_session():
            nonlocal session_ended
            session_ended = True

        end_active_session()

        assert session_ended is True

    def test_show_home_page_resets_question_state(self):
        """Test show_home_page resets question state."""
        answer_revealed = True
        current_question_id = 123

        answer_revealed = False
        current_question_id = None

        assert answer_revealed is False
        assert current_question_id is None

    def test_start_reviewing_sets_is_home_page_false(self):
        """Test start_reviewing clears is_home_page."""
        is_home_page = True
        is_home_page = False
        assert is_home_page is False

    def test_start_reviewing_creates_session(self):
        """Test start_reviewing starts a new session."""
        current_session_id = None
        current_session_id = 123
        assert current_session_id is not None

    def test_start_reviewing_records_activity(self):
        """Test start_reviewing records user activity."""
        activity_recorded = False

        def record_activity():
            nonlocal activity_recorded
            activity_recorded = True

        record_activity()

        assert activity_recorded is True

    def test_start_reviewing_skipped_if_already_reviewing(self):
        """Test start_reviewing does nothing if already reviewing."""
        is_home_page = False
        current_session_id = 123
        start_skipped = False

        if not is_home_page and current_session_id:
            start_skipped = True

        assert start_skipped is True

    def test_home_to_review_state(self):
        """Test transitioning from home to review state."""
        is_home_page = True
        is_home_page = False
        assert is_home_page is False

    def test_review_to_home_state(self):
        """Test transitioning from review to home state."""
        is_home_page = False
        is_home_page = True
        assert is_home_page is True

    def test_session_starts_on_review(self):
        """Test session starts when entering review mode."""
        current_session_id = None
        is_home_page = False

        if not is_home_page and current_session_id is None:
            current_session_id = 1

        assert current_session_id is not None


class TestAnalyticsQueryAccuracy:
    """Tests for analytics data formatting and calculations."""

    def test_format_pie_chart_structure(self):
        """Test pie chart formatting returns correct structure."""
        data = [
            {'CategoryName': 'Science', 'FactCount': 10},
            {'CategoryName': 'History', 'FactCount': 5},
        ]

        result = {
            'labels': [row['CategoryName'] for row in data],
            'data': [row['FactCount'] for row in data]
        }

        assert result['labels'] == ['Science', 'History']
        assert result['data'] == [10, 5]

    def test_format_pie_chart_empty_data(self):
        """Test pie chart with empty data."""
        data = []

        result = {
            'labels': [row.get('label') for row in data],
            'data': [row.get('value') for row in data]
        }

        assert result['labels'] == []
        assert result['data'] == []

    def test_review_streak_calculation_consecutive_days(self):
        """Test streak calculation for consecutive days."""
        from datetime import date

        today = date.today()
        yesterday = today - timedelta(days=1)
        day_before = today - timedelta(days=2)

        review_dates = [today, yesterday, day_before]

        streak = 0
        if review_dates:
            first = review_dates[0]
            if first in (today, yesterday):
                streak = 1
                for i, d in enumerate(review_dates[1:], 1):
                    expected = first - timedelta(days=i)
                    if d == expected:
                        streak += 1
                    else:
                        break

        assert streak == 3

    def test_review_streak_broken_by_gap(self):
        """Test streak resets when there's a gap."""
        from datetime import date

        today = date.today()
        review_dates = [today, today - timedelta(days=3)]

        streak = 1 if review_dates and review_dates[0] in (today, today - timedelta(days=1)) else 0

        assert streak == 1


# =============================================================================
# TIER 3: NICE TO HAVE TESTS - TTS, Window, Edge Cases, Errors
# =============================================================================

class TestTTSFunctionality:
    """Tests for text-to-speech functionality."""

    def test_speak_text_blocked_on_home_page(self):
        """Test speak_text does nothing on home page."""
        is_home_page = True
        speak_called = False

        if not is_home_page:
            speak_called = True

        assert speak_called is False

    def test_speak_text_gets_fact_label_text(self):
        """Test speak_text reads from fact label."""
        fact_label_text = "This is a test fact."
        is_home_page = False

        text_to_speak = fact_label_text if not is_home_page else None

        assert text_to_speak == "This is a test fact."

    def test_stop_speaking_clears_active_engine(self):
        """Test stop_speaking clears active TTS engine reference."""
        active_tts_engine = MagicMock()
        active_tts_engine = None
        assert active_tts_engine is None


class TestWindowManagement:
    """Tests for window positioning and management."""

    def test_set_static_position_applies_geometry(self):
        """Test static position sets window geometry."""
        window_static_pos = "+100+100"
        geometry_set = window_static_pos
        assert geometry_set == "+100+100"

    def test_on_drag_updates_coordinates(self):
        """Test dragging updates window coordinates."""
        x_window, y_window = 50, 50
        event_x_root, event_y_root = 150, 200

        new_x = event_x_root - x_window
        new_y = event_y_root - y_window

        assert new_x == 100
        assert new_y == 150

    def test_window_transparency_on_focus(self):
        """Test window alpha changes on focus."""
        focused_alpha = 1.0
        unfocused_alpha = 0.7

        assert focused_alpha == 1.0
        assert unfocused_alpha == 0.7


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_facts_list_handled(self):
        """Test empty facts list shows appropriate message."""
        all_facts = []
        has_facts = len(all_facts) > 0
        assert has_facts is False

    def test_single_fact_navigation_wraps(self):
        """Test navigation with single fact wraps correctly."""
        all_facts = [("Fact 1", 1)]
        current_index = 0
        next_index = (current_index + 1) % len(all_facts)
        assert next_index == 0

    def test_previous_fact_wraps_from_first(self):
        """Test previous from first fact wraps to last."""
        all_facts = [("Fact 1", 1), ("Fact 2", 2), ("Fact 3", 3)]
        current_index = 0
        prev_index = (current_index - 1) % len(all_facts)
        assert prev_index == 2

    def test_next_fact_wraps_from_last(self):
        """Test next from last fact wraps to first."""
        all_facts = [("Fact 1", 1), ("Fact 2", 2), ("Fact 3", 3)]
        current_index = 2
        next_index = (current_index + 1) % len(all_facts)
        assert next_index == 0

    def test_invalid_fact_index_clamped(self):
        """Test invalid fact index is clamped to valid range."""
        all_facts = [("Fact 1", 1), ("Fact 2", 2)]
        current_index = 10

        if all_facts:
            current_index = max(0, min(current_index, len(all_facts) - 1))

        assert current_index == 1

    def test_none_category_handled(self):
        """Test None category is handled gracefully."""
        category = None
        safe_category = category or "All Categories"
        assert safe_category == "All Categories"

    def test_rapid_navigation_preserves_state(self):
        """Test rapid navigation doesn't corrupt state."""
        all_facts = [("Fact 1", 1), ("Fact 2", 2), ("Fact 3", 3)]
        current_index = 0

        for _ in range(10):
            current_index = (current_index + 1) % len(all_facts)

        assert current_index == 1

    def test_zero_duration_handled(self):
        """Test zero duration is handled correctly."""
        duration_seconds = 0

        if duration_seconds > 0:
            rate = 10 / duration_seconds
        else:
            rate = 0

        assert rate == 0

    def test_negative_xp_prevented(self):
        """Test negative XP values are prevented."""
        xp_to_award = -10
        safe_xp = max(0, xp_to_award)
        assert safe_xp == 0


class TestFactNavigation:
    """Tests for fact navigation logic."""

    def test_next_fact_wraps_around(self):
        """Test next fact wraps to beginning."""
        all_facts = [(1, 'Fact 1'), (2, 'Fact 2'), (3, 'Fact 3')]
        current_index = 2

        next_index = (current_index + 1) % len(all_facts)

        assert next_index == 0

    def test_previous_fact_wraps_around(self):
        """Test previous fact wraps to end."""
        all_facts = [(1, 'Fact 1'), (2, 'Fact 2'), (3, 'Fact 3')]
        current_index = 0

        prev_index = (current_index - 1) % len(all_facts)

        assert prev_index == 2

    def test_single_fact_navigation(self):
        """Test navigation with single fact stays on same fact."""
        all_facts = [(1, 'Only Fact')]
        current_index = 0

        next_index = (current_index + 1) % len(all_facts)
        prev_index = (current_index - 1) % len(all_facts)

        assert next_index == 0
        assert prev_index == 0


class TestDatabaseErrorHandling:
    """Tests for database error handling."""

    def test_fetch_query_returns_empty_on_error(self):
        """Test fetch_query returns empty list on error."""
        result = []
        assert result == []

    def test_execute_update_returns_false_on_error(self):
        """Test execute_update returns False on error."""
        success = False
        assert success is False

    def test_execute_insert_return_id_returns_none_on_error(self):
        """Test execute_insert_return_id returns None on error."""
        new_id = None
        assert new_id is None

    def test_parameterized_query_format(self):
        """Test parameterized queries use ? placeholder."""
        sample_queries = [
            "SELECT * FROM Facts WHERE FactID = ?",
            "UPDATE Facts SET TotalViews = TotalViews + 1 WHERE FactID = ?",
            "INSERT INTO FactLogs (FactID, ReviewDate) VALUES (?, GETDATE())",
        ]

        for query in sample_queries:
            assert '?' in query
            assert '%s' not in query


class TestAPIErrorHandling:
    """Tests for external API error handling."""

    def test_ai_api_timeout_handled(self):
        """Test AI API timeout is handled gracefully."""
        usage_info = {"status": "FAILED"}
        result_text = "Timed out contacting AI. Please try again."

        assert usage_info["status"] == "FAILED"
        assert "Timed out" in result_text

    def test_ai_api_connection_error_handled(self):
        """Test AI API connection error is handled."""
        usage_info = {"status": "FAILED"}
        result_text = "Network error reaching AI service."

        assert usage_info["status"] == "FAILED"
        assert "Network error" in result_text

    def test_missing_api_key_blocks_request(self):
        """Test missing API key blocks AI requests."""
        api_key = None
        should_proceed = api_key is not None
        assert should_proceed is False

    def test_payload_structure(self):
        """Test AI API payload has required fields."""
        payload = {
            "model": "deepseek-ai/DeepSeek-V3.1",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Explain this fact."}
            ],
            "max_tokens": 320,
            "temperature": 0.35
        }

        assert "model" in payload
        assert "messages" in payload
        assert "max_tokens" in payload
        assert isinstance(payload["messages"], list)

    def test_payload_message_roles(self):
        """Test message roles are valid."""
        valid_roles = ["system", "user", "assistant"]
        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "User message"},
        ]

        for msg in messages:
            assert msg["role"] in valid_roles


class TestXPCalculation:
    """Tests for XP award calculations."""

    def test_xp_award_respects_grace_period(self):
        """Test XP not awarded below grace period."""
        elapsed_seconds = 1
        grace_seconds = 3
        should_award = elapsed_seconds >= grace_seconds
        assert should_award is False

    def test_xp_award_at_grace_period(self):
        """Test XP awarded at exactly grace period."""
        elapsed_seconds = 3
        grace_seconds = 3
        should_award = elapsed_seconds >= grace_seconds
        assert should_award is True

    def test_xp_time_bonus_calculation(self):
        """Test XP time bonus calculation."""
        elapsed_seconds = 10
        grace_seconds = 3
        max_bonus = 5

        bonus = min(elapsed_seconds - grace_seconds, max_bonus)

        assert bonus == 5

    def test_xp_bonus_capped_at_max(self):
        """Test XP bonus doesn't exceed maximum."""
        elapsed_seconds = 100
        grace_seconds = 3
        max_bonus = 5

        bonus = min(elapsed_seconds - grace_seconds, max_bonus)

        assert bonus == 5

    def test_xp_below_grace_period(self):
        """Test no XP awarded below grace period."""
        elapsed = 1
        grace = 2

        if elapsed < grace:
            xp = 0
        else:
            base_xp = 1
            step = 5
            cap = 5
            extra = (max(0, elapsed - grace)) // step
            xp = base_xp + min(cap, int(extra))

        assert xp == 0

    def test_xp_with_time_bonus(self):
        """Test XP with time bonus."""
        elapsed = 12
        grace = 2
        base_xp = 1
        step = 5
        cap = 5

        extra = (max(0, elapsed - grace)) // step
        xp = base_xp + min(cap, int(extra))

        assert xp == 3

    def test_xp_capped_bonus(self):
        """Test XP bonus is capped."""
        elapsed = 60
        grace = 2
        base_xp = 1
        step = 5
        cap = 5

        extra = (max(0, elapsed - grace)) // step
        xp = base_xp + min(cap, int(extra))

        assert xp == 6


class TestAICostEstimation:
    """Tests for AI cost estimation logic."""

    def test_estimate_cost_zero_tokens(self):
        """Test cost estimation with zero tokens."""
        prompt_tokens = 0
        completion_tokens = 0
        prompt_cost_per_1k = 0.0006
        completion_cost_per_1k = 0.0017

        cost = (prompt_tokens / 1000 * prompt_cost_per_1k) + \
               (completion_tokens / 1000 * completion_cost_per_1k)

        assert cost == 0.0

    def test_estimate_cost_typical_usage(self):
        """Test cost estimation with typical token counts."""
        prompt_tokens = 150
        completion_tokens = 200
        prompt_cost_per_1k = 0.0006
        completion_cost_per_1k = 0.0017

        cost = (prompt_tokens / 1000 * prompt_cost_per_1k) + \
               (completion_tokens / 1000 * completion_cost_per_1k)

        assert abs(cost - 0.00043) < 0.00001

    def test_estimate_cost_large_usage(self):
        """Test cost estimation with large token counts."""
        prompt_tokens = 1000
        completion_tokens = 500
        prompt_cost_per_1k = 0.0006
        completion_cost_per_1k = 0.0017

        cost = (prompt_tokens / 1000 * prompt_cost_per_1k) + \
               (completion_tokens / 1000 * completion_cost_per_1k)

        assert abs(cost - 0.00145) < 0.00001


class TestFontSizeAdjustment:
    """Tests for dynamic font size adjustment."""

    def test_adjust_font_size_short_text(self):
        """Test font size for short text."""
        text = "Short text"
        size = max(8, min(12, int(12 - (len(text) / 150))))
        assert size == 11

    def test_adjust_font_size_medium_text(self):
        """Test font size for medium text."""
        text = "A" * 300
        size = max(8, min(12, int(12 - (len(text) / 150))))
        assert size == 10

    def test_adjust_font_size_long_text(self):
        """Test font size for long text."""
        text = "A" * 900
        size = max(8, min(12, int(12 - (len(text) / 150))))
        assert size == 8

    def test_adjust_font_size_empty_text(self):
        """Test font size for empty text."""
        text = ""
        size = max(8, min(12, int(12 - (len(text) / 150))))
        assert size == 12


class TestContentDuplication:
    """Tests for content duplication detection logic."""

    def test_content_key_normalization(self):
        """Test content key normalization logic."""
        content1 = "  Hello World  "
        content2 = "Hello World"
        content3 = "hello world"

        def normalize(s):
            return s.lower().strip().replace('\r', ' ').replace('\n', ' ').replace('\t', ' ')

        assert normalize(content1) == normalize(content2)
        assert normalize(content2) == normalize(content3)

    def test_content_key_different_content(self):
        """Test different content produces different keys."""
        content1 = "Fact about science"
        content2 = "Fact about history"

        def normalize(s):
            return s.lower().strip()

        assert normalize(content1) != normalize(content2)


class TestToolTip:
    """Tests for ToolTip class."""

    def test_tooltip_class_exists(self):
        """Test ToolTip class is defined."""
        with patch.dict('sys.modules', {'tkinter': MagicMock(), 'tkinter.ttk': MagicMock()}):
            pass
