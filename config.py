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
    'server': os.environ.get('FACTDARI_DB_SERVER', 'GAURAVS_DESKTOP\\SQLEXPRESS'),
    'database': os.environ.get('FACTDARI_DB_NAME', 'FactDari'),
    'trusted_connection': os.environ.get('FACTDARI_DB_TRUSTED', 'yes')
}

# Idle timeout behavior (inactivity)
# Seconds before considering the user idle (default: 300s = 5 minutes)
IDLE_TIMEOUT_SECONDS = int(os.environ.get('FACTDARI_IDLE_TIMEOUT_SECONDS', '300'))
# If true, also end the session when idle; otherwise just finalize current view
IDLE_END_SESSION = os.environ.get('FACTDARI_IDLE_END_SESSION', 'true').lower() in ('1', 'true', 'yes', 'y')
# If true, auto-navigate to Home on idle timeout (only if ending session)
IDLE_NAVIGATE_HOME = os.environ.get('FACTDARI_IDLE_NAVIGATE_HOME', 'true').lower() in ('1', 'true', 'yes', 'y')

# UI Configuration
UI_CONFIG = {
    # Window dimensions
    'window_width': 520,
    'window_height': 380,
    'window_static_pos': "-1927+7",
    'popup_position': "-1923+400",
    'popup_add_card_size': "496x400",
    'popup_edit_card_size': "496x520",
    'popup_categories_size': "400x520",
    'popup_info_size': "420x480",
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
    
    # Fonts
    'font_family': "Trebuchet MS",
    'title_font_size': 14,
    'normal_font_size': 10,
    'small_font_size': 8,
    'large_font_size': 16,
    'stats_font_size': 9
}


# Helper functions
def get_icon_path(icon_name):
    """Get path to application icons"""
    return os.path.join(ICONS_DIR, icon_name)

def get_connection_string():
    return (
        r'DRIVER={SQL Server};'
        f"SERVER={DB_CONFIG['server']};"
        f"DATABASE={DB_CONFIG['database']};"
        f"Trusted_Connection={DB_CONFIG['trusted_connection']};"
    )

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

# (no chart config helpers are needed; Chart.js is configured in the template)
