"""
Unit tests for factdari.py logic.
These tests use stubs/mocks to avoid GUI and database dependencies.
"""
from datetime import datetime, timedelta
from unittest.mock import MagicMock
import time

import requests

import config
import factdari


class DummyVar:
    def __init__(self, value=None):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


def make_app():
    return factdari.FactDariApp.__new__(factdari.FactDariApp)


def make_mock_conn(mock_cursor):
    mock_conn = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = None
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.__exit__.return_value = None
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn


def test_tooltip_binds_events():
    widget = MagicMock()
    tooltip = factdari.ToolTip(widget, "Help text", delay=100)
    widget.bind.assert_any_call("<Enter>", tooltip._schedule)
    widget.bind.assert_any_call("<Leave>", tooltip._hide)
    widget.bind.assert_any_call("<ButtonPress>", tooltip._hide)


def test_tooltip_cancel_clears_after_id():
    widget = MagicMock()
    widget.after.return_value = "after-id"
    tooltip = factdari.ToolTip(widget, "Help text", delay=50)
    tooltip._schedule()
    assert tooltip._after_id == "after-id"
    tooltip._cancel()
    widget.after_cancel.assert_called_once_with("after-id")
    assert tooltip._after_id is None


def test_pause_review_timer_sets_pause_state():
    app = make_app()
    app.pause_depth = 0
    app.current_fact_start_time = datetime.now()
    app.timer_paused = False
    app.pause_started_at = None

    app.pause_review_timer()

    assert app.timer_paused is True
    assert app.pause_depth == 1
    assert app.pause_started_at is not None


def test_pause_review_timer_nested_does_not_reset_pause_start():
    app = make_app()
    app.pause_depth = 1
    app.current_fact_start_time = datetime.now()
    app.timer_paused = True
    original_pause = datetime.now() - timedelta(seconds=5)
    app.pause_started_at = original_pause

    app.pause_review_timer()

    assert app.pause_depth == 2
    assert app.pause_started_at == original_pause


def test_resume_review_timer_decrements_depth_only():
    app = make_app()
    app.pause_depth = 2
    app.timer_paused = True
    app.pause_started_at = datetime.now() - timedelta(seconds=5)

    app.resume_review_timer()

    assert app.pause_depth == 1
    assert app.timer_paused is True


def test_resume_review_timer_shifts_start_time():
    app = make_app()
    app.pause_depth = 1
    app.timer_paused = True
    app.current_fact_start_time = datetime.now() - timedelta(seconds=30)
    original_start = app.current_fact_start_time
    app.pause_started_at = datetime.now() - timedelta(seconds=5)
    app.category_dropdown_open = True

    app.resume_review_timer()

    assert app.pause_depth == 0
    assert app.timer_paused is False
    assert app.pause_started_at is None
    assert app.category_dropdown_open is False
    assert app.current_fact_start_time > original_start


def test_record_activity_updates_timestamp_and_resets_idle():
    app = make_app()
    old_time = datetime.now() - timedelta(seconds=10)
    app.last_activity_time = old_time
    app.idle_triggered = True

    app.record_activity()

    assert app.idle_triggered is False
    assert app.last_activity_time > old_time


def test_update_ui_triggers_idle_timeout_when_threshold_exceeded():
    app = make_app()
    app.update_coordinates = MagicMock()
    app.update_fact_count = MagicMock()
    app.update_review_stats = MagicMock()
    app.update_level_progress = MagicMock()
    app.handle_idle_timeout = MagicMock()
    app.root = MagicMock()
    app.root.after = MagicMock()
    app.UI_UPDATE_INTERVAL_MS = 123

    app.is_home_page = False
    app.current_session_id = 1
    app.timer_paused = False
    app.idle_triggered = False
    app.idle_timeout_seconds = 300
    app.last_activity_time = datetime.now() - timedelta(seconds=301)

    app.update_ui()

    app.handle_idle_timeout.assert_called_once()
    args = app.root.after.call_args[0]
    assert args[0] == 123


def test_update_ui_skips_idle_check_when_paused():
    app = make_app()
    app.update_coordinates = MagicMock()
    app.update_fact_count = MagicMock()
    app.update_review_stats = MagicMock()
    app.update_level_progress = MagicMock()
    app.handle_idle_timeout = MagicMock()
    app.root = MagicMock()
    app.root.after = MagicMock()
    app.UI_UPDATE_INTERVAL_MS = 100

    app.is_home_page = False
    app.current_session_id = 1
    app.timer_paused = True
    app.idle_triggered = False
    app.idle_timeout_seconds = 300
    app.last_activity_time = datetime.now() - timedelta(seconds=400)

    app.update_ui()

    app.handle_idle_timeout.assert_not_called()


def test_update_ui_skips_idle_check_without_session():
    app = make_app()
    app.update_coordinates = MagicMock()
    app.update_fact_count = MagicMock()
    app.update_review_stats = MagicMock()
    app.update_level_progress = MagicMock()
    app.handle_idle_timeout = MagicMock()
    app.root = MagicMock()
    app.root.after = MagicMock()
    app.UI_UPDATE_INTERVAL_MS = 100

    app.is_home_page = False
    app.current_session_id = None
    app.timer_paused = False
    app.idle_triggered = False
    app.idle_timeout_seconds = 300
    app.last_activity_time = datetime.now() - timedelta(seconds=400)

    app.update_ui()

    app.handle_idle_timeout.assert_not_called()


def test_is_action_allowed_false_on_home():
    app = make_app()
    app.is_home_page = True
    app.answer_revealed = True
    app._block_popup_when_questioning = MagicMock()

    assert app._is_action_allowed() is False
    app._block_popup_when_questioning.assert_not_called()


def test_is_action_allowed_false_when_answer_hidden():
    app = make_app()
    app.is_home_page = False
    app.answer_revealed = False
    app._block_popup_when_questioning = MagicMock(return_value=True)

    assert app._is_action_allowed("toggle favorite") is False
    app._block_popup_when_questioning.assert_called_once()


def test_is_action_allowed_true_when_reviewing_and_revealed():
    app = make_app()
    app.is_home_page = False
    app.answer_revealed = True
    app._block_popup_when_questioning = MagicMock()

    assert app._is_action_allowed() is True


def test_award_for_elapsed_awards_expected_xp(monkeypatch):
    app = make_app()
    app.gamify = MagicMock()
    app.status_label = MagicMock()
    app.clear_status_after_delay = MagicMock()
    app.update_level_progress = MagicMock()
    app.GREEN_COLOR = "#00ff00"
    app.gamify.increment_counter.return_value = 7
    app.gamify.unlock_achievements_if_needed.return_value = []

    monkeypatch.setattr(
        config,
        "XP_CONFIG",
        {
            "review_base_xp": 1,
            "review_bonus_step_seconds": 5,
            "review_grace_seconds": 2,
            "review_bonus_cap": 5,
        },
    )

    app._award_for_elapsed(12, timed_out=False)

    app.gamify.increment_counter.assert_called_once_with("TotalReviews", 1)
    app.gamify.award_xp.assert_called_once_with(3)


def test_award_for_elapsed_below_grace_skips_award(monkeypatch):
    app = make_app()
    app.gamify = MagicMock()

    monkeypatch.setattr(
        config,
        "XP_CONFIG",
        {
            "review_base_xp": 1,
            "review_bonus_step_seconds": 5,
            "review_grace_seconds": 3,
            "review_bonus_cap": 5,
        },
    )

    app._award_for_elapsed(1, timed_out=False)

    app.gamify.increment_counter.assert_not_called()
    app.gamify.award_xp.assert_not_called()


def test_award_for_elapsed_timed_out_skips_award():
    app = make_app()
    app.gamify = MagicMock()

    app._award_for_elapsed(10, timed_out=True)

    app.gamify.increment_counter.assert_not_called()
    app.gamify.award_xp.assert_not_called()


def test_finalize_current_fact_view_uses_last_activity_on_timeout():
    app = make_app()
    app.current_fact_log_id = 123
    app.current_fact_start_time = datetime(2024, 1, 1, 0, 0, 0)
    app.last_activity_time = datetime(2024, 1, 1, 0, 1, 0)
    app.timer_paused = False
    app.pause_started_at = None
    app.execute_update = MagicMock(return_value=True)
    app._award_for_elapsed = MagicMock()

    app.finalize_current_fact_view(timed_out=True)

    query, params = app.execute_update.call_args[0]
    assert params == (60, 1, 123)
    app._award_for_elapsed.assert_called_once_with(60, timed_out=True)
    assert app.current_fact_log_id is None
    assert app.current_fact_start_time is None


def test_adjust_font_size_bounds():
    app = make_app()
    assert app.adjust_font_size("Short text") == 11
    assert app.adjust_font_size("A" * 900) == 8
    assert app.adjust_font_size("") == 12


def test_estimate_ai_cost_typical():
    app = make_app()
    app.ai_prompt_cost_per_1k = 0.0006
    app.ai_completion_cost_per_1k = 0.0017

    cost = app._estimate_ai_cost(150, 200)

    assert abs(cost - 0.00043) < 0.00001


def test_call_together_ai_timeout_sets_failed(monkeypatch):
    app = make_app()
    app.ai_endpoint = "https://example.com"
    app.ai_timeout_seconds = 5
    app.ai_explanation_max_tokens = 100
    app.ai_explanation_temperature = 0.5

    monkeypatch.setattr(factdari.requests, "post", MagicMock(side_effect=requests.exceptions.Timeout))

    message, usage = app._call_together_ai("Fact text", "key")

    assert "Timed out" in message
    assert usage["status"] == "FAILED"


def test_call_together_ai_connection_error_sets_failed(monkeypatch):
    app = make_app()
    app.ai_endpoint = "https://example.com"
    app.ai_timeout_seconds = 5
    app.ai_explanation_max_tokens = 100
    app.ai_explanation_temperature = 0.5

    monkeypatch.setattr(factdari.requests, "post", MagicMock(side_effect=requests.exceptions.ConnectionError))

    message, usage = app._call_together_ai("Fact text", "key")

    assert "Network error" in message
    assert usage["status"] == "FAILED"


def test_speak_text_returns_early_on_home_page():
    app = make_app()
    app.is_home_page = True
    app.stop_speaking = MagicMock()

    app.speak_text()

    app.stop_speaking.assert_not_called()


def test_stop_speaking_stops_engine_and_clears_reference():
    app = make_app()
    engine = MagicMock()
    app.active_tts_engine = engine
    app.speaking_thread = MagicMock()
    app.speaking_thread.is_alive.return_value = False

    app.stop_speaking()

    engine.stop.assert_called_once()
    assert app.active_tts_engine is None


def test_set_static_position_applies_geometry_and_updates_coordinates():
    app = make_app()
    app.WINDOW_STATIC_POS = "+100+100"
    app.root = MagicMock()
    app.update_coordinates = MagicMock()

    app.set_static_position()

    app.root.geometry.assert_called_once_with("+100+100")
    app.update_coordinates.assert_called_once()


def test_update_category_dropdown_preserves_selection():
    app = make_app()
    app.load_categories = MagicMock(return_value=["All Categories", "Science"])
    app.category_dropdown = {}
    app.category_var = DummyVar("Science")

    app.update_category_dropdown()

    assert app.category_dropdown["values"] == ["All Categories", "Science"]
    assert app.category_var.get() == "Science"


def test_update_category_dropdown_defaults_when_missing():
    app = make_app()
    app.load_categories = MagicMock(return_value=["All Categories", "Science"])
    app.category_dropdown = {}
    app.category_var = DummyVar("History")

    app.update_category_dropdown()

    assert app.category_var.get() == "All Categories"


def test_get_or_generate_question_blocks_duplicate_inflight(monkeypatch):
    app = make_app()
    app.fetch_query = MagicMock(return_value=[])
    app.question_request_inflight = True
    app.question_generation_fact_id = 42
    app.question_generation_last_attempt = {}
    app.question_generation_cooldown_seconds = 60
    app.root = MagicMock()

    monkeypatch.setattr(config, "get_together_api_key", lambda: "key")

    question, q_id = app._get_or_generate_question(42, "Fact text")

    assert question is None
    assert q_id is None


def test_get_or_generate_question_respects_cooldown(monkeypatch):
    app = make_app()
    app.fetch_query = MagicMock(return_value=[])
    app.question_request_inflight = False
    app.question_generation_fact_id = None
    app.question_generation_last_attempt = {42: time.time() - 10}
    app.question_generation_cooldown_seconds = 60
    app.root = MagicMock()

    monkeypatch.setattr(config, "get_together_api_key", lambda: "key")

    question, q_id = app._get_or_generate_question(42, "Fact text")

    assert question == "What does this fact say?"
    assert q_id is None


def test_show_next_fact_advances_index():
    app = make_app()
    app.is_home_page = False
    app.answer_revealed = True
    app.all_facts = [(1, "Fact 1"), (2, "Fact 2"), (3, "Fact 3")]
    app.current_fact_index = 0
    app.stop_speaking = MagicMock()
    app.finalize_current_fact_view = MagicMock()
    app._finalize_question_view = MagicMock()
    app.load_all_facts = MagicMock()
    app.display_current_fact = MagicMock()

    app.show_next_fact()

    assert app.current_fact_index == 1
    app.display_current_fact.assert_called_once()
    assert app.answer_revealed is False
    assert app.current_question_id is None


def test_show_previous_fact_wraps_index():
    app = make_app()
    app.is_home_page = False
    app.answer_revealed = True
    app.all_facts = [(1, "Fact 1"), (2, "Fact 2"), (3, "Fact 3")]
    app.current_fact_index = 0
    app.stop_speaking = MagicMock()
    app.finalize_current_fact_view = MagicMock()
    app._finalize_question_view = MagicMock()
    app.load_all_facts = MagicMock()
    app.display_current_fact = MagicMock()

    app.show_previous_fact()

    assert app.current_fact_index == 2
    app.display_current_fact.assert_called_once()
    assert app.answer_revealed is False
    assert app.current_question_id is None


def test_display_current_fact_handles_empty_list():
    app = make_app()
    app.all_facts = []
    app.stop_speaking = MagicMock()
    app.fact_label = MagicMock()
    app.NORMAL_FONT = ("Trebuchet MS", 10)
    app.white_star_icon = object()
    app.easy_icon = object()
    app.star_button = MagicMock()
    app.easy_button = MagicMock()
    app.prev_button = MagicMock()
    app.next_button = MagicMock()
    app.single_card_label = MagicMock()
    app.GRAY_COLOR = "#888888"
    app.BLUE_COLOR = "#0000ff"

    app.display_current_fact()

    assert app.current_fact_id is None
    app.prev_button.config.assert_called_with(state="disabled", bg=app.GRAY_COLOR)
    app.next_button.config.assert_called_with(state="disabled", bg=app.GRAY_COLOR)


def test_fetch_query_passes_params(monkeypatch):
    app = make_app()
    app.CONN_STR = "conn"
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [("row1",)]
    mock_conn = make_mock_conn(mock_cursor)
    monkeypatch.setattr(factdari.pyodbc, "connect", MagicMock(return_value=mock_conn))

    result = app.fetch_query("SELECT * FROM table WHERE id = ?", (1,))

    mock_cursor.execute.assert_called_once_with("SELECT * FROM table WHERE id = ?", (1,))
    assert result == [("row1",)]


def test_fetch_query_returns_empty_on_error(monkeypatch):
    app = make_app()
    app.CONN_STR = "conn"
    monkeypatch.setattr(factdari.pyodbc, "connect", MagicMock(side_effect=Exception("boom")))

    assert app.fetch_query("SELECT 1") == []


def test_execute_update_returns_false_on_error(monkeypatch):
    app = make_app()
    app.CONN_STR = "conn"
    monkeypatch.setattr(factdari.pyodbc, "connect", MagicMock(side_effect=Exception("boom")))

    assert app.execute_update("UPDATE table SET col = 1") is False


def test_execute_insert_return_id_returns_none_on_error(monkeypatch):
    app = make_app()
    app.CONN_STR = "conn"
    monkeypatch.setattr(factdari.pyodbc, "connect", MagicMock(side_effect=Exception("boom")))

    assert app.execute_insert_return_id("INSERT INTO table OUTPUT INSERTED.ID VALUES (1)") is None


def test_execute_insert_return_id_returns_new_id(monkeypatch):
    app = make_app()
    app.CONN_STR = "conn"
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (99,)
    mock_conn = make_mock_conn(mock_cursor)
    monkeypatch.setattr(factdari.pyodbc, "connect", MagicMock(return_value=mock_conn))

    assert app.execute_insert_return_id("INSERT INTO table OUTPUT INSERTED.ID VALUES (1)") == 99


def test_get_or_generate_question_returns_cached_question(monkeypatch):
    app = make_app()
    app.fetch_query = MagicMock(return_value=[(10, "Cached question", 1)])
    app.question_request_inflight = False
    app.question_generation_fact_id = None
    app.question_generation_last_attempt = {}
    app.question_generation_cooldown_seconds = 60

    monkeypatch.setattr(config, "get_together_api_key", lambda: "key")

    question, q_id = app._get_or_generate_question(42, "Fact text")

    assert question == "Cached question"
    assert q_id == 10


def test_get_or_generate_question_falls_back_without_api_key(monkeypatch):
    app = make_app()
    app.fetch_query = MagicMock(return_value=[])
    app.question_request_inflight = False
    app.question_generation_fact_id = None
    app.question_generation_last_attempt = {}
    app.question_generation_cooldown_seconds = 60

    monkeypatch.setattr(config, "get_together_api_key", lambda: None)

    question, q_id = app._get_or_generate_question(42, "Fact text")

    assert question == "What does this fact say?"
    assert q_id is None


def test_disable_ui_during_generation_disables_controls():
    app = make_app()
    app.home_button = MagicMock()
    app.prev_button = MagicMock()
    app.next_button = MagicMock()
    app._disable_fact_action_buttons = MagicMock()

    app._disable_ui_during_generation()

    app.home_button.config.assert_called_once_with(state="disabled")
    app.prev_button.config.assert_called_once_with(state="disabled")
    app.next_button.config.assert_called_once_with(state="disabled")
    app._disable_fact_action_buttons.assert_called_once()


def test_enable_ui_after_generation_enables_controls():
    app = make_app()
    app.home_button = MagicMock()
    app.prev_button = MagicMock()
    app.next_button = MagicMock()

    app._enable_ui_after_generation()

    app.home_button.config.assert_called_once_with(state="normal")
    app.prev_button.config.assert_called_once_with(state="normal")
    app.next_button.config.assert_called_once_with(state="normal")


def test_show_next_fact_noop_with_single_fact():
    app = make_app()
    app.is_home_page = False
    app.answer_revealed = True
    app.all_facts = [(1, "Fact 1")]
    app.current_fact_index = 0
    app.stop_speaking = MagicMock()
    app.finalize_current_fact_view = MagicMock()
    app._finalize_question_view = MagicMock()
    app.load_all_facts = MagicMock()
    app.display_current_fact = MagicMock()

    app.show_next_fact()

    assert app.current_fact_index == 0
    app.display_current_fact.assert_not_called()


def test_display_current_fact_single_fact_shows_warning_label():
    app = make_app()
    app.all_facts = [(1, "Fact 1", False, False)]
    app.current_fact_index = 0
    app.answer_revealed = True
    app.stop_speaking = MagicMock()
    app.fact_label = MagicMock()
    app.NORMAL_FONT = ("Trebuchet MS", 10)
    app.white_star_icon = object()
    app.gold_star_icon = object()
    app.easy_icon = object()
    app.easy_gold_icon = object()
    app.star_button = MagicMock()
    app.easy_button = MagicMock()
    app.prev_button = MagicMock()
    app.next_button = MagicMock()
    app.single_card_label = MagicMock()
    app.GRAY_COLOR = "#888888"
    app.BLUE_COLOR = "#0000ff"
    app.status_label = MagicMock()
    app.STATUS_COLOR = "#111111"
    app.clear_status_after_delay = MagicMock()
    app.adjust_font_size = MagicMock(return_value=10)
    app.track_fact_view = MagicMock()

    app.display_current_fact()

    app.single_card_label.pack.assert_called_once()
    app.prev_button.config.assert_called_with(state="disabled", bg=app.GRAY_COLOR)
    app.next_button.config.assert_called_with(state="disabled", bg=app.GRAY_COLOR)
    app.track_fact_view.assert_called_once_with(1)


def test_show_home_page_resets_state_and_calls_session_end():
    app = make_app()
    app.end_active_session = MagicMock()
    app._finalize_question_view = MagicMock()
    app.stop_speaking = MagicMock()
    app.clear_status_after_delay = MagicMock()
    app.apply_rounded_corners = MagicMock()
    app.root = MagicMock()
    app.root.update_idletasks = MagicMock()

    app.stats_frame = MagicMock()
    app.icon_buttons_frame = MagicMock()
    app.nav_frame = MagicMock()
    app.category_frame = MagicMock()
    app.single_card_label = MagicMock()
    app.star_button = MagicMock()
    app.easy_button = MagicMock()
    app.ai_button = MagicMock()
    app.reveal_button = MagicMock()
    app.level_label = MagicMock()
    app.info_button = MagicMock()
    app.speaker_button = MagicMock()
    app.brand_frame = MagicMock()
    app.fact_label = MagicMock()
    app.slogan_label = MagicMock()
    app.start_button = MagicMock()
    app.status_label = MagicMock()
    app.STATUS_COLOR = "#222222"
    app.is_home_page = False
    app.answer_revealed = True
    app.current_question_id = 12

    app.show_home_page()

    app.end_active_session.assert_called_once()
    assert app.is_home_page is True
    assert app.answer_revealed is False
    assert app.current_question_id is None
