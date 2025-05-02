# config.py
import os
from pathlib import Path

# Base directory where the application is installed
# Use environment variable if provided, otherwise use relative path
BASE_DIR = os.environ.get('MEMODARI_BASE_DIR', os.path.dirname(os.path.abspath(__file__)))

# Resource paths - allow override via environment variables
RESOURCES_DIR = os.environ.get('MEMODARI_RESOURCES_DIR', os.path.join(BASE_DIR, "Resources"))
IMAGES_DIR = os.environ.get('MEMODARI_IMAGES_DIR', os.path.join(RESOURCES_DIR, "Images"))

# Log directory
LOG_DIR = os.environ.get('MEMODARI_LOG_DIR', os.path.join(BASE_DIR, "util"))
LOG_FILE = os.environ.get('MEMODARI_LOG_FILE', os.path.join(LOG_DIR, "fsrs_debug.log"))

# FSRS weights file
WEIGHTS_FILE = os.environ.get('MEMODARI_WEIGHTS_FILE', os.path.join(BASE_DIR, "weights.json"))

# Analytics app path
ANALYTICS_APP = os.environ.get('MEMODARI_ANALYTICS_APP', os.path.join(BASE_DIR, "analytics.py"))

# Database configuration
DB_CONFIG = {
    'server': os.environ.get('MEMODARI_DB_SERVER', 'GAURAVS_DESKTOP\\SQLEXPRESS'),
    'database': os.environ.get('MEMODARI_DB_NAME', 'MemoDari'),
    'trusted_connection': os.environ.get('MEMODARI_DB_TRUSTED', 'yes')
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

# Chart.js Configuration - NEW SECTION
CHART_CONFIG = {
    # Chart colors
    'colors': [
        '#4CAF50', '#2196F3', '#FFC107', '#F44336', '#9C27B0', 
        '#00BCD4', '#FF9800', '#795548', '#607D8B', '#E91E63'
    ],
    
    # Font settings
    'font_family': "Trebuchet MS",
    'axis_title_size': 16,      # Larger font for axis titles
    'axis_tick_size': 14,       # Larger font for axis tick labels
    'legend_font_size': 14,     # Font size for chart legends
    'tooltip_title_size': 14,   # Font size for tooltip titles
    'tooltip_body_size': 13,    # Font size for tooltip content
    
    # Other chart settings
    'point_radius': 5,
    'hover_point_radius': 7,
    'line_thickness': 2,
    'grid_color': 'rgba(255, 255, 255, 0.1)',
    'text_color': 'white'
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

# NEW: Get chart configuration as JSON for JavaScript
def get_chart_config_js():
    """Return chart configuration as JavaScript code"""
    js_code = """
// Chart configuration from Python config
const CHART_CONFIG = {
    colors: %s,
    fontFamily: "%s",
    axisTitleSize: %d,
    axisTickSize: %d,
    legendFontSize: %d,
    tooltipTitleSize: %d,
    tooltipBodySize: %d,
    pointRadius: %d,
    hoverPointRadius: %d,
    lineThickness: %d,
    gridColor: '%s',
    textColor: '%s'
};
""" % (
        CHART_CONFIG['colors'],
        CHART_CONFIG['font_family'],
        CHART_CONFIG['axis_title_size'],
        CHART_CONFIG['axis_tick_size'],
        CHART_CONFIG['legend_font_size'],
        CHART_CONFIG['tooltip_title_size'],
        CHART_CONFIG['tooltip_body_size'],
        CHART_CONFIG['point_radius'],
        CHART_CONFIG['hover_point_radius'],
        CHART_CONFIG['line_thickness'],
        CHART_CONFIG['grid_color'],
        CHART_CONFIG['text_color']
    )
    return js_code