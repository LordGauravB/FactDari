# config.py
import os

# Base directory where the application is installed
# Use environment variable if provided, otherwise use relative path
BASE_DIR = os.environ.get('FACTDARI_BASE_DIR', os.path.dirname(os.path.abspath(__file__)))

# Resource paths - allow override via environment variables
RESOURCES_DIR = os.environ.get('FACTDARI_RESOURCES_DIR', os.path.join(BASE_DIR, "Resources"))
ICONS_DIR = os.environ.get('FACTDARI_ICONS_DIR', os.path.join(RESOURCES_DIR, "application_icons"))


# Database configuration
DB_CONFIG = {
    'server': os.environ.get('FACTDARI_DB_SERVER', 'localhost\\SQLEXPRESS'),
    'database': os.environ.get('FACTDARI_DB_NAME', 'FactDari'),
    'trusted_connection': os.environ.get('FACTDARI_DB_TRUSTED', 'yes'),
    # Optional ODBC driver override. Examples: 'ODBC Driver 18 for SQL Server', 'ODBC Driver 17 for SQL Server'
    'driver': os.environ.get('FACTDARI_DB_DRIVER', 'SQL Server'),
    # Optional security toggles (useful with ODBC 18 where Encrypt defaults to yes)
    # Set FACTDARI_DB_ENCRYPT to 'yes'/'no' to force Encrypt parameter
    # Set FACTDARI_DB_TRUST_CERT to 'yes'/'no' to force TrustServerCertificate
    'encrypt': os.environ.get('FACTDARI_DB_ENCRYPT', ''),
    'trust_server_certificate': os.environ.get('FACTDARI_DB_TRUST_CERT', ''),
}

# Idle timeout behavior (inactivity)
# Seconds before considering the user idle (default: 300s = 5 minutes)
IDLE_TIMEOUT_SECONDS = int(os.environ.get('FACTDARI_IDLE_TIMEOUT_SECONDS', '300'))
# If true, also end the session when idle; otherwise just finalize current view
IDLE_END_SESSION = os.environ.get('FACTDARI_IDLE_END_SESSION', 'true').lower() in ('1', 'true', 'yes', 'y')
# If true, auto-navigate to Home on idle timeout (only if ending session)
IDLE_NAVIGATE_HOME = os.environ.get('FACTDARI_IDLE_NAVIGATE_HOME', 'true').lower() in ('1', 'true', 'yes', 'y')

# XP rewards and tuning (can be overridden via env vars)
XP_CONFIG = {
    # Base XP for review and time-based bonus
    'review_base_xp': int(os.environ.get('FACTDARI_XP_REVIEW_BASE', '1')),
    # Bonus XP: +1 for each N seconds after grace
    'review_bonus_step_seconds': int(os.environ.get('FACTDARI_XP_REVIEW_BONUS_STEP_SECONDS', '5')),
    # Grace before timing bonus starts
    'review_grace_seconds': int(os.environ.get('FACTDARI_XP_REVIEW_GRACE_SECONDS', '2')),
    # Max bonus increments added to base
    'review_bonus_cap': int(os.environ.get('FACTDARI_XP_REVIEW_BONUS_CAP', '5')),

    # Action XP
    'xp_favorite': int(os.environ.get('FACTDARI_XP_FAVORITE', '1')),
    'xp_known': int(os.environ.get('FACTDARI_XP_KNOWN', '10')),
    'xp_add': int(os.environ.get('FACTDARI_XP_ADD', '2')),
    'xp_edit': int(os.environ.get('FACTDARI_XP_EDIT', '1')),
    'xp_delete': int(os.environ.get('FACTDARI_XP_DELETE', '0')),

    # Daily check-in for streaks
    'xp_daily_checkin': int(os.environ.get('FACTDARI_XP_DAILY_CHECKIN', '2')),
}

# UI Configuration
UI_CONFIG = {
    # Window dimensions
    'window_width': 540,
    'window_height': 380,
    'window_static_pos': "-1927+7",
    'popup_position': "-1923+400",
    'popup_add_card_size': "496x400",
    'popup_edit_card_size': "496x520",
    'popup_categories_size': "400x520",
    'popup_info_size': "420x480",
    # Dedicated width for the Achievements popup (slightly wider)
    'popup_achievements_size': os.environ.get('FACTDARI_POPUP_ACHIEVEMENTS_SIZE', "518x480"),
    'popup_confirm_size': "360x180",
    'popup_rename_size': "420x200",
    'corner_radius': 15,
    
    # Colors
    'bg_color': "#1e1e1e",
    'title_bg_color': "#000000",
    'listbox_bg_color': "#2a2a2a",
    'text_color': "white",
    'green_color': "#4CAF50",
    'blue_color': "#2196F3",
    'red_color': "#F44336",
    'yellow_color': "#FFC107",
    'gray_color': "#607D8B",
    'status_color': "#b66d20",
    # Brand colors (for desktop widget branding)
    'brand_fact_color': os.environ.get('FACTDARI_BRAND_FACT_COLOR', "#34d399"),
    'brand_dari_color': os.environ.get('FACTDARI_BRAND_DARI_COLOR', "#38bdf8"),
    
    # Fonts
    'font_family': "Trebuchet MS",
    'title_font_size': 14,
    'normal_font_size': 10,
    'small_font_size': 8,
    'large_font_size': 16,
    'stats_font_size': 9
}


def _get_float_env(var_name: str, default: str = "0") -> float:
    """Safely parse a float from environment variables."""
    try:
        return float(os.environ.get(var_name, default))
    except Exception:
        try:
            return float(default)
        except Exception:
            return 0.0


# AI pricing/configuration (used for cost estimation and logging)
AI_PRICING = {
    'provider': os.environ.get('FACTDARI_AI_PROVIDER', 'together'),
    'model': os.environ.get('FACTDARI_AI_MODEL', 'deepseek-ai/DeepSeek-V3.1'),
    # Defaults derived from provided pricing per 1M tokens: $0.60 input, $1.70 output
    'prompt_cost_per_1k': _get_float_env('FACTDARI_AI_PROMPT_COST_PER_1K', '0.0006'),
    'completion_cost_per_1k': _get_float_env('FACTDARI_AI_COMPLETION_COST_PER_1K', '0.0017'),
    'currency': os.environ.get('FACTDARI_AI_CURRENCY', 'USD'),
}


# Helper functions
def get_icon_path(icon_name):
    """Get path to application icons"""
    return os.path.join(ICONS_DIR, icon_name)

def get_connection_string():
    driver = DB_CONFIG.get('driver', 'SQL Server')
    parts = [
        "DRIVER={" + driver + "};",
        f"SERVER={DB_CONFIG['server']};",
        f"DATABASE={DB_CONFIG['database']};",
        f"Trusted_Connection={DB_CONFIG['trusted_connection']};",
    ]
    # Append optional security flags if provided (empty values are ignored)
    enc = (DB_CONFIG.get('encrypt') or '').strip()
    if enc:
        parts.append(f"Encrypt={enc};")
    tsc = (DB_CONFIG.get('trust_server_certificate') or '').strip()
    if tsc:
        parts.append(f"TrustServerCertificate={tsc};")
    return "".join(parts)

def get_font(font_type):
    """Get font tuple based on predefined settings"""
    if font_type == 'title':
        return (UI_CONFIG['font_family'], UI_CONFIG['title_font_size'], 'bold')
    elif font_type == 'normal':
        return (UI_CONFIG['font_family'], UI_CONFIG['normal_font_size'])
    elif font_type == 'small':
        return (UI_CONFIG['font_family'], UI_CONFIG['small_font_size'])
    elif font_type == 'large':
        return (UI_CONFIG['font_family'], UI_CONFIG['large_font_size'], 'bold')
    elif font_type == 'stats':
        return (UI_CONFIG['font_family'], UI_CONFIG['stats_font_size'])
    else:
        return (UI_CONFIG['font_family'], UI_CONFIG['normal_font_size'])

def get_together_api_key():
    """Fetch Together AI API key from environment."""
    return (
        os.environ.get('FACTDARI_TOGETHER_API_KEY')
        or os.environ.get('TOGETHER_API_KEY')
        or os.environ.get('TOGETHER_API_TOKEN')
    )

# (no chart config helpers are needed; Chart.js is configured in the template)

# Leveling configuration (makes Level 100 total XP adjustable and early band sizes tunable)
LEVELING_CONFIG = {
    # Total XP required to reach Level 100 (used to fit constant and final steps)
    'total_xp_l100': int(os.environ.get('FACTDARI_LEVEL_TOTAL_XP_L100', '1000000')),

    # Early bands (inclusive end levels and per-level step sizes)
    'band1_end': int(os.environ.get('FACTDARI_LEVEL_BAND1_END', '4')),
    'band1_step': int(os.environ.get('FACTDARI_LEVEL_BAND1_STEP', '100')),
    'band2_end': int(os.environ.get('FACTDARI_LEVEL_BAND2_END', '9')),
    'band2_step': int(os.environ.get('FACTDARI_LEVEL_BAND2_STEP', '500')),
    'band3_end': int(os.environ.get('FACTDARI_LEVEL_BAND3_END', '14')),
    'band3_step': int(os.environ.get('FACTDARI_LEVEL_BAND3_STEP', '1000')),
    'band4_end': int(os.environ.get('FACTDARI_LEVEL_BAND4_END', '19')),
    'band4_step': int(os.environ.get('FACTDARI_LEVEL_BAND4_STEP', '5000')),

    # End of the constant step band (start is band4_end + 1; final step is at level 99)
    'const_end': int(os.environ.get('FACTDARI_LEVEL_CONST_END', '98')),
}
