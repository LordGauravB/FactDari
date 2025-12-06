"""
Pytest configuration and shared fixtures for FactDari tests.
"""
import pytest
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up mock environment variables for testing."""
    monkeypatch.setenv('FACTDARI_DB_SERVER', 'localhost\\SQLEXPRESS')
    monkeypatch.setenv('FACTDARI_DB_NAME', 'FactDari_Test')
    monkeypatch.setenv('FACTDARI_DB_TRUSTED', 'yes')
    monkeypatch.setenv('FACTDARI_TOGETHER_API_KEY', 'test-api-key-12345')
    monkeypatch.setenv('FACTDARI_IDLE_TIMEOUT_SECONDS', '300')
    monkeypatch.setenv('FACTDARI_XP_REVIEW_BASE', '1')
    monkeypatch.setenv('FACTDARI_XP_FAVORITE', '1')
    monkeypatch.setenv('FACTDARI_XP_KNOWN', '10')
    monkeypatch.setenv('FACTDARI_XP_ADD', '2')
    monkeypatch.setenv('FACTDARI_XP_EDIT', '1')
    monkeypatch.setenv('FACTDARI_XP_DELETE', '0')


@pytest.fixture
def sample_fact():
    """Return a sample fact dictionary for testing."""
    return {
        'FactID': 1,
        'CategoryID': 1,
        'Content': 'The Earth is approximately 4.5 billion years old.',
        'DateAdded': '2024-01-01',
        'TotalViews': 10,
        'CategoryName': 'Science'
    }


@pytest.fixture
def sample_profile():
    """Return a sample gamification profile for testing."""
    return {
        'ProfileID': 1,
        'XP': 500,
        'Level': 5,
        'TotalReviews': 100,
        'TotalKnown': 25,
        'TotalFavorites': 10,
        'TotalAdds': 50,
        'TotalEdits': 15,
        'TotalDeletes': 5,
        'TotalAITokens': 1000,
        'TotalAICost': 0.05,
        'CurrentStreak': 7,
        'LongestStreak': 14,
        'LastCheckinDate': '2024-01-15'
    }


@pytest.fixture
def sample_achievement():
    """Return a sample achievement for testing."""
    return {
        'AchievementID': 1,
        'Code': 'KNOW_10',
        'Name': 'Knowledge Seeker',
        'Category': 'known',
        'Threshold': 10,
        'RewardXP': 50
    }


@pytest.fixture
def sample_ai_usage():
    """Return sample AI usage data for testing."""
    return {
        'FactID': 1,
        'SessionID': 1,
        'ProfileID': 1,
        'OperationType': 'explain',
        'Status': 'SUCCESS',
        'ModelName': 'deepseek-ai/DeepSeek-V3.1',
        'Provider': 'together',
        'InputTokens': 150,
        'OutputTokens': 200,
        'TotalTokens': 350,
        'Cost': 0.00043,
        'CurrencyCode': 'USD',
        'LatencyMs': 1500,
        'ReadingDurationSec': 30
    }


@pytest.fixture
def mock_db_cursor():
    """Create a mock database cursor for testing."""
    class MockCursor:
        def __init__(self):
            self.queries = []
            self.params = []
            self.results = []
            self.description = []
            self._result_index = 0

        def execute(self, query, params=None):
            self.queries.append(query)
            self.params.append(params)

        def fetchone(self):
            if self._result_index < len(self.results):
                result = self.results[self._result_index]
                self._result_index += 1
                return result
            return None

        def fetchall(self):
            if self._result_index < len(self.results):
                result = self.results[self._result_index]
                self._result_index += 1
                return result if isinstance(result, list) else [result]
            return []

        def set_results(self, results, description=None):
            self.results = results
            self._result_index = 0
            if description:
                self.description = description

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    return MockCursor()


@pytest.fixture
def mock_db_connection(mock_db_cursor):
    """Create a mock database connection for testing."""
    class MockConnection:
        def __init__(self, cursor):
            self._cursor = cursor
            self.committed = False

        def cursor(self):
            return self._cursor

        def commit(self):
            self.committed = True

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    return MockConnection(mock_db_cursor)
