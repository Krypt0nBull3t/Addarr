"""
Filename: keyboards.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Keyboard layouts module.

This module provides centralized keyboard layouts for the bot.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.services.translation import TranslationService


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Get the main menu keyboard"""
    translation = TranslationService()
    keyboard = [
        [
            InlineKeyboardButton(
                f"🎬 {translation.get_text('Movie')}",
                callback_data="menu_movie"
            ),
            InlineKeyboardButton(
                f"📺 {translation.get_text('Series')}",
                callback_data="menu_series"
            ),
        ],
        [
            InlineKeyboardButton(
                f"🎵 {translation.get_text('Music')}",
                callback_data="menu_music"
            ),
            InlineKeyboardButton(
                f"📊 {translation.get_text('Status')}",
                callback_data="menu_status"
            ),
        ],
        [
            InlineKeyboardButton(
                f"🗑 {translation.get_text('Delete')}",
                callback_data="menu_delete"
            ),
        ],
        [
            InlineKeyboardButton(
                f"⚙️ {translation.get_text('Settings')}",
                callback_data="menu_settings"
            ),
        ],
        [
            InlineKeyboardButton(
                f"❓ {translation.get_text('HelpButton')}",
                callback_data="menu_help"
            ),
            InlineKeyboardButton(
                f"❌ {translation.get_text('Cancel')}",
                callback_data="menu_cancel"
            ),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_system_keyboard() -> InlineKeyboardMarkup:
    """Get system status keyboard"""
    # Return empty keyboard - no buttons needed
    return None


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Get settings menu keyboard"""
    translation = TranslationService()
    keyboard = [
        [
            InlineKeyboardButton("🎬 Radarr", callback_data="settings_radarr"),
            InlineKeyboardButton("📺 Sonarr", callback_data="settings_sonarr")
        ],
        [
            InlineKeyboardButton("🎵 Lidarr", callback_data="settings_lidarr"),
            InlineKeyboardButton("📥 Downloads", callback_data="settings_downloads")
        ],
        [
            InlineKeyboardButton("👥 Users", callback_data="settings_users"),
            InlineKeyboardButton(
                f"🌐 {translation.get_text('Language')}",
                callback_data="settings_language"
            )
        ],
        [
            InlineKeyboardButton(
                f"◀️ {translation.get_text('Back')}",
                callback_data="settings_back"
            )
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_language_keyboard() -> InlineKeyboardMarkup:
    """Get language selection keyboard"""
    languages = [
        ("🇩🇪 Deutsch", "de-de"),
        ("🇺🇸 English", "en-us"),
        ("🇪🇸 Español", "es-es"),
        ("🇫🇷 Français", "fr-fr"),
        ("🇮🇹 Italiano", "it-it"),
        ("🇧🇪 Nederlands", "nl-be"),
        ("🇵🇱 Polski", "pl-pl"),
        ("🇵🇹 Português", "pt-pt"),
        ("🇷🇺 Русский", "ru-ru"),
    ]
    keyboard = []
    for i in range(0, len(languages), 2):
        row = [
            InlineKeyboardButton(
                languages[i][0],
                callback_data=f"lang_{languages[i][1]}"
            )
        ]
        if i + 1 < len(languages):
            row.append(
                InlineKeyboardButton(
                    languages[i + 1][0],
                    callback_data=f"lang_{languages[i + 1][1]}"
                )
            )
        keyboard.append(row)
    translation = TranslationService()
    keyboard.append([
        InlineKeyboardButton(
            f"◀️ {translation.get_text('Back')}",
            callback_data="settings_back"
        )
    ])
    return InlineKeyboardMarkup(keyboard)


def get_service_toggle_keyboard(
    services_status: dict,
) -> InlineKeyboardMarkup:
    """Get service enable/disable toggle keyboard"""
    keyboard = []
    for service, enabled in services_status.items():
        status = "✅" if enabled else "❌"
        keyboard.append([
            InlineKeyboardButton(
                f"{status} {service.title()}",
                callback_data=f"svc_toggle_{service}"
            )
        ])
    translation = TranslationService()
    keyboard.append([
        InlineKeyboardButton(
            f"◀️ {translation.get_text('Back')}",
            callback_data="settings_back"
        )
    ])
    return InlineKeyboardMarkup(keyboard)


def get_quality_profile_keyboard(
    profiles: list, service: str,
) -> InlineKeyboardMarkup:
    """Get quality profile selection keyboard"""
    keyboard = []
    for profile in profiles:
        keyboard.append([
            InlineKeyboardButton(
                profile["name"],
                callback_data=f"setquality_{service}_{profile['id']}"
            )
        ])
    translation = TranslationService()
    keyboard.append([
        InlineKeyboardButton(
            f"◀️ {translation.get_text('Back')}",
            callback_data="settings_back"
        )
    ])
    return InlineKeyboardMarkup(keyboard)


def get_confirmation_keyboard(action: str) -> InlineKeyboardMarkup:
    """Get confirmation keyboard"""
    translation = TranslationService()
    keyboard = [
        [
            InlineKeyboardButton(
                f"✅ {translation.get_text('Add')}",
                callback_data=f"confirm_{action}"
            ),
            InlineKeyboardButton(
                f"❌ {translation.get_text('Stop')}",
                callback_data="confirm_cancel"
            )
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_yes_no_keyboard(callback_prefix: str, yes_text: str = "Yes", no_text: str = "No") -> InlineKeyboardMarkup:
    """Create a Yes/No inline keyboard

    Args:
        callback_prefix: Prefix for callback data
        yes_text: Text for Yes button
        no_text: Text for No button

    Returns:
        InlineKeyboardMarkup: Keyboard with Yes/No buttons
    """
    keyboard = [
        [
            InlineKeyboardButton(yes_text, callback_data=f"{callback_prefix}_yes"),
            InlineKeyboardButton(no_text, callback_data=f"{callback_prefix}_no")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
