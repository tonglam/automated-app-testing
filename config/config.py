"""
Configuration settings for the automated app testing project.
"""

import os
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# Asset paths
ASSETS_DIR = PROJECT_ROOT / "assets"
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"

# Image paths
AGREE_BUTTON = ASSETS_DIR / "agree.png"
LOCATION_BUTTON = ASSETS_DIR / "location.png"
SELECT_LOCATION = ASSETS_DIR / "select_location.png"
CLOSE_BUTTON = ASSETS_DIR / "close_button.png"
NATIONWIDE_DELIVERY = ASSETS_DIR / "nationwide_delivery_icon.png"
SEARCH_INPUT = ASSETS_DIR / "search_input.png"

# Appium settings
APPIUM_HOST = "127.0.0.1"
APPIUM_PORT = 4723

# App settings
APP_PACKAGE = "com.pagoda.buy"
APP_ACTIVITY = ".ui.MainActivity"

# Timeouts
IMPLICIT_WAIT = 30
INITIAL_WAIT = 15
ELEMENT_WAIT = 10
