"""
Filename: states.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Conversation states for the bot handlers
"""


class States:
    """States for conversation handlers"""

    # Settings states
    SETTINGS_MENU = "settings_menu"
    SETTINGS_LANGUAGE = "settings_language"
    SETTINGS_SERVICE = "settings_service"
    SETTINGS_QUALITY = "settings_quality"
    SETTINGS_DOWNLOADS = "settings_downloads"
    SETTINGS_USERS = "settings_users"

    # Webhook wizard states
    WEBHOOK_MENU = "webhook_menu"
    WEBHOOK_EVENTS = "webhook_events"
    WEBHOOK_CHANGE_PORT = "webhook_change_port"

    # Bazarr states
    BAZARR_SEARCH = "bazarr_search"
