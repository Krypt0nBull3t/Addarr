"""
Filename: definitions.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Project path definitions module.

This module defines all the important paths used throughout the application,
including paths for configuration files, logs, translations, and user data.
"""

import os

# Set Projects Root Directory
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.normpath(__file__)))

# Set Projects Configuration path
CONFIG_PATH = os.path.join(ROOT_DIR, "config.yaml")
CONFIG_EXAMPLE_PATH = os.path.join(ROOT_DIR, "config_example.yaml")
TRANSLATIONS_PATH = os.path.join(ROOT_DIR, "translations")
LANG_PATH = os.path.join(ROOT_DIR, "translations/")
CHATID_PATH = os.path.join(ROOT_DIR, "chatid.txt")
LOG_PATH = os.path.join(ROOT_DIR, "logs", "addarr.log")
ERROR_LOG_PATH = os.path.join(ROOT_DIR, "logs", "error.log")

# Data directory for persistent storage
DATA_PATH = os.path.join(ROOT_DIR, "data")

# User preferences file (in DATA_PATH so Docker can persist it as a volume)
PREFERENCES_PATH = os.path.join(DATA_PATH, "user_preferences.json")
# Location before DATA_PATH, still read when PREFERENCES_PATH does not exist
LEGACY_PREFERENCES_PATH = os.path.join(ROOT_DIR, "user_preferences.json")

# Valid values of security.chatMode (kept here: src/setup/ must not import settings)
CHAT_MODES = ("private_only", "allow_all")
