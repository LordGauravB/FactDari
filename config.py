# config.py
import os

# Base directory where the application is installed
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Resource paths
RESOURCES_DIR = os.path.join(BASE_DIR, "Resources")
IMAGES_DIR = os.path.join(RESOURCES_DIR, "Images")

# Database configuration
DB_CONFIG = {
    'server': os.environ.get('FACTDARI_DB_SERVER', 'GAURAVS_DESKTOP\\SQLEXPRESS'),
    'database': os.environ.get('FACTDARI_DB_NAME', 'FactDari'),
    'trusted_connection': os.environ.get('FACTDARI_DB_TRUSTED', 'yes')
}

# UI Configuration
UI_CONFIG = {
    # Window dimensions
    'window_width': 500,
    'window_height': 380,
    'window_static_pos': "-1927+7",
    'popup_position': "-1923+400",
    'popup_add_card_size': "496x400",
    'popup_edit_card_size': "496x450",
    'popup_categories_size': "400x500",
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
def get_image_path(image_name):
    return os.path.join(IMAGES_DIR, image_name)

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