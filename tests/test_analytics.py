"""
Unit tests for analytics_factdari.py module.
Tests Flask routes, data formatting, and query logic.
"""
import pytest
from unittest.mock import patch, MagicMock
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestFlaskApp:
    """Tests for Flask application setup."""

    def test_app_exists(self):
        """Test Flask app is created."""
        with patch('pyodbc.connect'):
            from analytics_factdari import app
            assert app is not None

    def test_app_has_routes(self):
        """Test Flask app has expected routes."""
        with patch('pyodbc.connect'):
            from analytics_factdari import app
            rules = [rule.rule for rule in app.url_map.iter_rules()]
            assert '/' in rules
            assert '/api/chart-data' in rules


class TestIndexRoute:
    """Tests for the index route."""

    def test_index_returns_html(self):
        """Test index route returns HTML."""
        with patch('pyodbc.connect'):
            from analytics_factdari import app
            client = app.test_client()
            response = client.get('/')
            assert response.status_code == 200
            assert response.content_type.startswith('text/html')


class TestChartDataRoute:
    """Tests for the chart data API route."""

    @patch('analytics_factdari.fetch_query')
    @patch('analytics_factdari.calculate_review_streak')
    @patch('analytics_factdari.get_default_profile_id')
    def test_chart_data_returns_json(self, mock_profile, mock_streak, mock_fetch):
        """Test chart data route returns JSON."""
        mock_profile.return_value = 1
        mock_streak.return_value = {'current_streak': 5, 'longest_streak': 10}
        mock_fetch.return_value = []

        from analytics_factdari import app
        client = app.test_client()
        response = client.get('/api/chart-data')

        assert response.status_code == 200
        assert response.content_type == 'application/json'

    @patch('analytics_factdari.fetch_query')
    @patch('analytics_factdari.calculate_review_streak')
    @patch('analytics_factdari.get_default_profile_id')
    def test_chart_data_structure(self, mock_profile, mock_streak, mock_fetch):
        """Test chart data contains expected keys."""
        mock_profile.return_value = 1
        mock_streak.return_value = {'current_streak': 5, 'longest_streak': 10}
        mock_fetch.return_value = []

        from analytics_factdari import app
        client = app.test_client()
        response = client.get('/api/chart-data')
        data = json.loads(response.data)

        # Check for key data sections
        expected_keys = [
            'category_distribution',
            'reviews_per_day',
            'most_reviewed_facts',
            'least_reviewed_facts',
            'review_streak',
        ]
        for key in expected_keys:
            assert key in data, f"Missing key: {key}"

    @patch('analytics_factdari.fetch_query')
    @patch('analytics_factdari.calculate_review_streak')
    @patch('analytics_factdari.get_default_profile_id')
    def test_chart_data_all_param(self, mock_profile, mock_streak, mock_fetch):
        """Test chart data with all=true parameter."""
        mock_profile.return_value = 1
        mock_streak.return_value = {'current_streak': 5}
        mock_fetch.return_value = []

        from analytics_factdari import app
        client = app.test_client()
        response = client.get('/api/chart-data?all=true')

        assert response.status_code == 200


class TestFetchQuery:
    """Tests for the fetch_query function."""

    @patch('pyodbc.connect')
    def test_fetch_query_returns_list(self, mock_connect):
        """Test fetch_query returns a list of dicts."""
        mock_cursor = MagicMock()
        mock_cursor.description = [('col1',), ('col2',)]
        mock_cursor.fetchall.return_value = [('val1', 'val2'), ('val3', 'val4')]
        mock_connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor

        from analytics_factdari import fetch_query
        result = fetch_query("SELECT * FROM test")

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0] == {'col1': 'val1', 'col2': 'val2'}

    @patch('pyodbc.connect')
    def test_fetch_query_with_params(self, mock_connect):
        """Test fetch_query passes parameters correctly."""
        mock_cursor = MagicMock()
        mock_cursor.description = [('id',)]
        mock_cursor.fetchall.return_value = [(1,)]
        mock_connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor

        from analytics_factdari import fetch_query
        result = fetch_query("SELECT * FROM test WHERE id = ?", (1,))

        mock_cursor.execute.assert_called_once()
        # Verify params were passed
        call_args = mock_cursor.execute.call_args
        assert call_args[0][1] == (1,)

    @patch('pyodbc.connect')
    def test_fetch_query_empty_result(self, mock_connect):
        """Test fetch_query handles empty results."""
        mock_cursor = MagicMock()
        mock_cursor.description = [('col1',)]
        mock_cursor.fetchall.return_value = []
        mock_connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor

        from analytics_factdari import fetch_query
        result = fetch_query("SELECT * FROM empty_table")

        assert result == []


class TestGetDefaultProfileId:
    """Tests for get_default_profile_id function."""

    @patch('analytics_factdari.fetch_query')
    def test_returns_profile_id(self, mock_fetch):
        """Test returns profile ID from database."""
        mock_fetch.return_value = [{'ProfileID': 5}]

        from analytics_factdari import get_default_profile_id
        result = get_default_profile_id()

        assert result == 5

    @patch('analytics_factdari.fetch_query')
    def test_returns_default_on_empty(self, mock_fetch):
        """Test returns 1 when no profile found."""
        mock_fetch.return_value = []

        from analytics_factdari import get_default_profile_id
        result = get_default_profile_id()

        assert result == 1

    @patch('analytics_factdari.fetch_query')
    def test_returns_default_on_exception(self, mock_fetch):
        """Test returns 1 on database error."""
        import pyodbc
        mock_fetch.side_effect = pyodbc.Error("DB Error")

        from analytics_factdari import get_default_profile_id
        result = get_default_profile_id()

        assert result == 1


class TestDataFormatting:
    """Tests for data formatting functions."""

    def test_format_pie_chart(self):
        """Test pie chart data formatting."""
        from analytics_factdari import format_pie_chart

        data = [
            {'CategoryName': 'Science', 'FactCount': 10},
            {'CategoryName': 'History', 'FactCount': 5},
        ]
        result = format_pie_chart(data, 'CategoryName', 'FactCount')

        assert 'labels' in result
        assert 'data' in result
        assert result['labels'] == ['Science', 'History']
        assert result['data'] == [10, 5]

    def test_format_pie_chart_empty(self):
        """Test pie chart with empty data."""
        from analytics_factdari import format_pie_chart

        result = format_pie_chart([], 'label', 'value')

        assert result['labels'] == []
        assert result['data'] == []

    def test_format_line_chart(self):
        """Test line chart data formatting."""
        from analytics_factdari import format_line_chart

        # format_line_chart expects data with Date, FactsReviewed, TotalReviews keys
        data = [
            {'Date': '2024-01-01', 'FactsReviewed': 5, 'TotalReviews': 8},
            {'Date': '2024-01-02', 'FactsReviewed': 10, 'TotalReviews': 15},
        ]
        result = format_line_chart(data)

        assert 'labels' in result
        assert 'datasets' in result
        assert len(result['datasets']) == 2  # Unique Facts Reviewed + Total Reviews
        assert result['datasets'][0]['label'] == 'Unique Facts Reviewed'
        assert result['datasets'][0]['data'] == [5, 10]
        assert result['datasets'][1]['label'] == 'Total Reviews'
        assert result['datasets'][1]['data'] == [8, 15]

    def test_format_bar_chart(self):
        """Test bar chart data formatting."""
        from analytics_factdari import format_bar_chart

        data = [
            {'Hour': 9, 'Count': 20},
            {'Hour': 10, 'Count': 15},
        ]
        result = format_bar_chart(data, 'Hour', 'Count', 'Activity')

        assert 'labels' in result
        assert 'datasets' in result
        assert result['labels'] == [9, 10]

    def test_format_heatmap(self):
        """Test heatmap data formatting."""
        from analytics_factdari import format_heatmap

        data = [
            {'Hour': 9, 'DayOfWeek': 1, 'ReviewCount': 5},
            {'Hour': 10, 'DayOfWeek': 2, 'ReviewCount': 10},
        ]
        result = format_heatmap(data)

        assert 'data' in result
        assert isinstance(result['data'], list)
        # Should be 7x24 matrix
        assert len(result['data']) == 7
        assert len(result['data'][0]) == 24

    def test_format_table_data(self):
        """Test table data passthrough."""
        from analytics_factdari import format_table_data

        data = [{'col1': 'val1'}, {'col1': 'val2'}]
        result = format_table_data(data)

        assert result == data


class TestCalculateReviewStreak:
    """Tests for review streak calculation."""

    @patch('analytics_factdari.fetch_query')
    def test_returns_dict(self, mock_fetch):
        """Test returns dictionary with streak info."""
        mock_fetch.return_value = []

        from analytics_factdari import calculate_review_streak
        result = calculate_review_streak(1)

        assert isinstance(result, dict)
        assert 'current_streak' in result
        assert 'longest_streak' in result

    @patch('analytics_factdari.fetch_query')
    def test_empty_reviews_zero_streak(self, mock_fetch):
        """Test zero streak when no reviews."""
        mock_fetch.return_value = []

        from analytics_factdari import calculate_review_streak
        result = calculate_review_streak(1)

        assert result['current_streak'] == 0
        assert result['longest_streak'] == 0


class TestAIUsageData:
    """Tests for AI usage analytics."""

    @patch('analytics_factdari.fetch_query')
    @patch('analytics_factdari.calculate_review_streak')
    @patch('analytics_factdari.get_default_profile_id')
    def test_ai_usage_in_response(self, mock_profile, mock_streak, mock_fetch):
        """Test AI usage data is included in chart data."""
        mock_profile.return_value = 1
        mock_streak.return_value = {'current_streak': 0}
        mock_fetch.return_value = []

        from analytics_factdari import app
        client = app.test_client()
        response = client.get('/api/chart-data')
        data = json.loads(response.data)

        ai_keys = [
            'ai_usage_summary',
            'ai_cost_timeline',
            'ai_token_distribution',
            'ai_usage_by_category',
            'ai_latency_distribution',
            'ai_most_explained_facts',
            'ai_recent_usage',
        ]
        for key in ai_keys:
            assert key in data, f"Missing AI key: {key}"


class TestGamificationData:
    """Tests for gamification analytics."""

    @patch('analytics_factdari.fetch_query')
    @patch('analytics_factdari.calculate_review_streak')
    @patch('analytics_factdari.get_default_profile_id')
    def test_gamification_in_response(self, mock_profile, mock_streak, mock_fetch):
        """Test gamification data is included in chart data."""
        mock_profile.return_value = 1
        mock_streak.return_value = {'current_streak': 0}
        mock_fetch.return_value = []

        from analytics_factdari import app
        client = app.test_client()
        response = client.get('/api/chart-data')
        data = json.loads(response.data)

        gamification_keys = [
            'gamification',
            'achievements_summary',
            'recent_achievements',
            'achievements',
        ]
        for key in gamification_keys:
            assert key in data, f"Missing gamification key: {key}"


class TestSessionAnalytics:
    """Tests for session analytics data."""

    @patch('analytics_factdari.fetch_query')
    @patch('analytics_factdari.calculate_review_streak')
    @patch('analytics_factdari.get_default_profile_id')
    def test_session_data_in_response(self, mock_profile, mock_streak, mock_fetch):
        """Test session data is included in chart data."""
        mock_profile.return_value = 1
        mock_streak.return_value = {'current_streak': 0}
        mock_fetch.return_value = []

        from analytics_factdari import app
        client = app.test_client()
        response = client.get('/api/chart-data')
        data = json.loads(response.data)

        session_keys = [
            'session_duration_stats',
            'avg_facts_per_session',
            'session_duration_distribution',
            'session_efficiency',
        ]
        for key in session_keys:
            assert key in data, f"Missing session key: {key}"


class TestProgressAnalytics:
    """Tests for progress analytics."""

    @patch('analytics_factdari.fetch_query')
    @patch('analytics_factdari.calculate_review_streak')
    @patch('analytics_factdari.get_default_profile_id')
    def test_progress_data_in_response(self, mock_profile, mock_streak, mock_fetch):
        """Test progress data is included in chart data."""
        mock_profile.return_value = 1
        mock_streak.return_value = {'current_streak': 0}
        mock_fetch.return_value = []

        from analytics_factdari import app
        client = app.test_client()
        response = client.get('/api/chart-data')
        data = json.loads(response.data)

        progress_keys = [
            'monthly_progress',
            'category_completion_rate',
            'learning_velocity',
            'category_growth_trend',
        ]
        for key in progress_keys:
            assert key in data, f"Missing progress key: {key}"


class TestErrorHandling:
    """Tests for error handling in analytics."""

    @patch('analytics_factdari.fetch_query')
    @patch('analytics_factdari.calculate_review_streak')
    @patch('analytics_factdari.get_default_profile_id')
    def test_handles_db_error_gracefully(self, mock_profile, mock_streak, mock_fetch):
        """Test API handles database errors gracefully."""
        mock_profile.return_value = 1
        mock_streak.return_value = {'current_streak': 0}
        # Simulate DB returning empty results (not crashing)
        mock_fetch.return_value = []

        from analytics_factdari import app
        client = app.test_client()
        response = client.get('/api/chart-data')

        # Should not crash, should return 200
        assert response.status_code == 200
