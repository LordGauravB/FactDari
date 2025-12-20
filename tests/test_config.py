"""
Unit tests for config.py module.
Tests configuration loading, environment variable handling, and helper functions.
"""
import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDatabaseConfig:
    """Tests for database configuration."""

    def test_default_db_server(self):
        """Test default database server value."""
        import config
        assert config.DB_CONFIG['server'] == os.environ.get(
            'FACTDARI_DB_SERVER', 'localhost\\SQLEXPRESS'
        )

    def test_default_db_name(self):
        """Test default database name."""
        import config
        assert config.DB_CONFIG['database'] == os.environ.get(
            'FACTDARI_DB_NAME', 'FactDari'
        )

    def test_db_trusted_connection(self):
        """Test trusted connection setting."""
        import config
        assert config.DB_CONFIG['trusted_connection'] in ('yes', 'no')

    def test_connection_string_format(self):
        """Test connection string is properly formatted."""
        import config
        conn_str = config.get_connection_string()
        assert 'DRIVER=' in conn_str
        assert 'SERVER=' in conn_str
        assert 'DATABASE=' in conn_str
        assert 'Trusted_Connection=' in conn_str

    def test_connection_string_driver_braces(self):
        """Test that driver name is wrapped in braces."""
        import config
        conn_str = config.get_connection_string()
        assert 'DRIVER={' in conn_str
        assert '};' in conn_str


class TestUIConfig:
    """Tests for UI configuration."""

    def test_window_dimensions_exist(self):
        """Test that window dimensions are defined."""
        import config
        assert 'window_width' in config.UI_CONFIG
        assert 'window_height' in config.UI_CONFIG
        assert isinstance(config.UI_CONFIG['window_width'], int)
        assert isinstance(config.UI_CONFIG['window_height'], int)

    def test_window_dimensions_positive(self):
        """Test that window dimensions are positive."""
        import config
        assert config.UI_CONFIG['window_width'] > 0
        assert config.UI_CONFIG['window_height'] > 0

    def test_colors_are_hex(self):
        """Test that color values are valid hex codes."""
        import config
        color_keys = ['bg_color', 'text_color', 'green_color', 'blue_color',
                      'red_color', 'yellow_color', 'gray_color']
        for key in color_keys:
            color = config.UI_CONFIG[key]
            assert color.startswith('#') or color in ('white', 'black')

    def test_font_family_exists(self):
        """Test that font family is defined."""
        import config
        assert 'font_family' in config.UI_CONFIG
        assert isinstance(config.UI_CONFIG['font_family'], str)
        assert len(config.UI_CONFIG['font_family']) > 0

    def test_font_sizes_positive(self):
        """Test that font sizes are positive integers."""
        import config
        font_size_keys = ['title_font_size', 'normal_font_size', 'small_font_size',
                          'large_font_size', 'stats_font_size']
        for key in font_size_keys:
            assert config.UI_CONFIG[key] > 0


class TestXPConfig:
    """Tests for XP reward configuration."""

    def test_xp_values_are_integers(self):
        """Test that all XP values are integers."""
        import config
        for key, value in config.XP_CONFIG.items():
            assert isinstance(value, int), f"{key} should be int, got {type(value)}"

    def test_xp_values_non_negative(self):
        """Test that XP values are non-negative."""
        import config
        for key, value in config.XP_CONFIG.items():
            assert value >= 0, f"{key} should be non-negative, got {value}"

    def test_review_base_xp_default(self):
        """Test default review base XP."""
        import config
        assert config.XP_CONFIG['review_base_xp'] >= 1

    def test_review_grace_seconds_reasonable(self):
        """Test grace period is reasonable (0-60 seconds)."""
        import config
        assert 0 <= config.XP_CONFIG['review_grace_seconds'] <= 60


class TestLevelingConfig:
    """Tests for leveling configuration."""

    def test_leveling_config_exists(self):
        """Test that leveling config is defined."""
        import config
        assert hasattr(config, 'LEVELING_CONFIG')
        assert isinstance(config.LEVELING_CONFIG, dict)

    def test_total_xp_l100_positive(self):
        """Test total XP for level 100 is positive."""
        import config
        assert config.LEVELING_CONFIG['total_xp_l100'] > 0

    def test_band_ends_increasing(self):
        """Test that band end levels are in increasing order."""
        import config
        cfg = config.LEVELING_CONFIG
        assert cfg['band1_end'] < cfg['band2_end']
        assert cfg['band2_end'] < cfg['band3_end']
        assert cfg['band3_end'] < cfg['band4_end']
        assert cfg['band4_end'] < cfg['const_end']

    def test_band_steps_increasing(self):
        """Test that band step sizes generally increase."""
        import config
        cfg = config.LEVELING_CONFIG
        assert cfg['band1_step'] <= cfg['band2_step']
        assert cfg['band2_step'] <= cfg['band3_step']
        assert cfg['band3_step'] <= cfg['band4_step']


class TestAIPricingConfig:
    """Tests for AI pricing configuration."""

    def test_ai_pricing_exists(self):
        """Test that AI pricing config exists."""
        import config
        assert hasattr(config, 'AI_PRICING')
        assert isinstance(config.AI_PRICING, dict)

    def test_ai_provider_default(self):
        """Test default AI provider."""
        import config
        assert config.AI_PRICING['provider'] == 'together'

    def test_ai_model_default(self):
        """Test default AI model."""
        import config
        assert 'deepseek' in config.AI_PRICING['model'].lower()

    def test_ai_costs_non_negative(self):
        """Test that AI costs are non-negative."""
        import config
        assert config.AI_PRICING['prompt_cost_per_1k'] >= 0
        assert config.AI_PRICING['completion_cost_per_1k'] >= 0

    def test_ai_currency_code(self):
        """Test currency code is valid."""
        import config
        assert len(config.AI_PRICING['currency']) == 3  # ISO currency code


class TestHelperFunctions:
    """Tests for config helper functions."""

    def test_get_icon_path(self):
        """Test get_icon_path returns valid path."""
        import config
        path = config.get_icon_path('test.png')
        assert path.endswith('test.png')
        assert 'application_icons' in path or 'icons' in path.lower()

    def test_get_font_title(self):
        """Test get_font returns tuple for title."""
        import config
        font = config.get_font('title')
        assert isinstance(font, tuple)
        assert len(font) == 3
        assert font[2] == 'bold'

    def test_get_font_normal(self):
        """Test get_font returns tuple for normal."""
        import config
        font = config.get_font('normal')
        assert isinstance(font, tuple)
        assert len(font) == 2

    def test_get_font_invalid_returns_default(self):
        """Test get_font returns default for invalid type."""
        import config
        font = config.get_font('invalid_type')
        assert isinstance(font, tuple)
        assert len(font) == 2

    def test_get_together_api_key_from_env(self, monkeypatch):
        """Test API key retrieval from environment."""
        monkeypatch.setenv('FACTDARI_TOGETHER_API_KEY', 'test-key-123')
        # Need to reload config to pick up new env var
        import importlib
        import config
        importlib.reload(config)
        key = config.get_together_api_key()
        assert key == 'test-key-123'

    def test_get_together_api_key_fallback(self, monkeypatch):
        """Test API key fallback to alternative env vars."""
        monkeypatch.delenv('FACTDARI_TOGETHER_API_KEY', raising=False)
        monkeypatch.setenv('TOGETHER_API_KEY', 'fallback-key')
        import importlib
        import config
        importlib.reload(config)
        key = config.get_together_api_key()
        assert key == 'fallback-key'


class TestIdleConfig:
    """Tests for idle timeout configuration."""

    def test_idle_timeout_positive(self):
        """Test idle timeout is positive."""
        import config
        assert config.IDLE_TIMEOUT_SECONDS > 0

    def test_idle_timeout_reasonable(self):
        """Test idle timeout is reasonable (1-3600 seconds)."""
        import config
        assert 1 <= config.IDLE_TIMEOUT_SECONDS <= 3600

    def test_idle_end_session_is_bool(self):
        """Test idle end session flag is boolean."""
        import config
        assert isinstance(config.IDLE_END_SESSION, bool)

    def test_idle_navigate_home_is_bool(self):
        """Test idle navigate home flag is boolean."""
        import config
        assert isinstance(config.IDLE_NAVIGATE_HOME, bool)


class TestEnvironmentOverrides:
    """Tests for environment variable overrides."""

    def test_db_server_override(self, monkeypatch):
        """Test database server can be overridden."""
        monkeypatch.setenv('FACTDARI_DB_SERVER', 'custom-server')
        import importlib
        import config
        importlib.reload(config)
        assert config.DB_CONFIG['server'] == 'custom-server'

    def test_xp_values_override(self, monkeypatch):
        """Test XP values can be overridden."""
        monkeypatch.setenv('FACTDARI_XP_FAVORITE', '99')
        import importlib
        import config
        importlib.reload(config)
        assert config.XP_CONFIG['xp_favorite'] == 99

    def test_idle_timeout_override(self, monkeypatch):
        """Test idle timeout can be overridden."""
        monkeypatch.setenv('FACTDARI_IDLE_TIMEOUT_SECONDS', '600')
        import importlib
        import config
        importlib.reload(config)
        assert config.IDLE_TIMEOUT_SECONDS == 600


class TestFloatEnvHelper:
    """Tests for _get_float_env helper function."""

    def test_get_float_env_valid(self, monkeypatch):
        """Test parsing valid float from env."""
        monkeypatch.setenv('TEST_FLOAT', '1.5')
        import config
        result = config._get_float_env('TEST_FLOAT', '0')
        assert result == 1.5

    def test_get_float_env_default(self, monkeypatch):
        """Test default value when env not set."""
        monkeypatch.delenv('TEST_FLOAT_MISSING', raising=False)
        import config
        result = config._get_float_env('TEST_FLOAT_MISSING', '2.5')
        assert result == 2.5

    def test_get_float_env_invalid_returns_default(self, monkeypatch):
        """Test invalid value returns default."""
        monkeypatch.setenv('TEST_FLOAT_INVALID', 'not-a-number')
        import config
        result = config._get_float_env('TEST_FLOAT_INVALID', '3.0')
        assert result == 3.0


class TestAnalyticsConfig:
    """Tests for analytics configuration."""

    def test_analytics_config_exists(self):
        """Test that analytics config is defined."""
        import config
        assert hasattr(config, 'ANALYTICS_CONFIG')
        assert isinstance(config.ANALYTICS_CONFIG, dict)

    def test_time_windows_positive(self):
        """Test time windows are positive integers."""
        import config
        assert config.ANALYTICS_CONFIG['recent_days_window'] > 0
        assert config.ANALYTICS_CONFIG['history_days_window'] > 0

    def test_pagination_limits_positive(self):
        """Test pagination limits are positive integers."""
        import config
        assert config.ANALYTICS_CONFIG['top_n_default'] > 0
        assert config.ANALYTICS_CONFIG['top_n_sessions'] > 0
        assert config.ANALYTICS_CONFIG['top_n_reviews'] > 0
        assert config.ANALYTICS_CONFIG['top_n_reviews_expanded'] > 0

    def test_rate_limits_positive(self):
        """Test rate limits are positive integers."""
        import config
        assert config.ANALYTICS_CONFIG['rate_limit_per_minute'] > 0
        assert config.ANALYTICS_CONFIG['rate_limit_per_second'] > 0


class TestLoggingConfig:
    """Tests for logging configuration."""

    def test_logging_config_exists(self):
        """Test that logging config is defined."""
        import config
        assert hasattr(config, 'LOGGING_CONFIG')
        assert isinstance(config.LOGGING_CONFIG, dict)

    def test_log_level_valid(self):
        """Test log level is a valid level."""
        import config
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        assert config.LOGGING_CONFIG['log_level'].upper() in valid_levels

    def test_log_file_is_string(self):
        """Test log file path is a string."""
        import config
        assert isinstance(config.LOGGING_CONFIG['log_file'], str)
        assert len(config.LOGGING_CONFIG['log_file']) > 0

    def test_log_max_bytes_positive(self):
        """Test max log file size is positive."""
        import config
        assert config.LOGGING_CONFIG['log_max_bytes'] > 0

    def test_log_backup_count_non_negative(self):
        """Test backup count is non-negative."""
        import config
        assert config.LOGGING_CONFIG['log_backup_count'] >= 0


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_setup_logging_returns_logger(self):
        """Test setup_logging returns a logger instance."""
        import config
        import logging
        logger = config.setup_logging('test_logger')
        assert isinstance(logger, logging.Logger)

    def test_setup_logging_with_name(self):
        """Test setup_logging uses provided name."""
        import config
        logger = config.setup_logging('custom_test_name')
        assert logger.name == 'custom_test_name'

    def test_setup_logging_default_name(self):
        """Test setup_logging uses default name."""
        import config
        logger = config.setup_logging()
        assert logger.name == 'factdari'

    def test_setup_logging_has_handlers(self):
        """Test setup_logging adds handlers."""
        import config
        logger = config.setup_logging('test_with_handlers')
        # Should have at least one handler (console)
        assert len(logger.handlers) >= 1
