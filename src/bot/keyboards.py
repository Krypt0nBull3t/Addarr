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
                f"📅 {translation.get_text('Upcoming')}",
                callback_data="menu_upcoming"
            ),
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
    """Get system status keyboard with action buttons"""
    translation = TranslationService()
    keyboard = [
        [
            InlineKeyboardButton(
                "🔄 Refresh", callback_data="system_refresh"
            ),
            InlineKeyboardButton(
                "📋 Details", callback_data="system_details"
            ),
        ],
        [
            InlineKeyboardButton(
                f"◀️ {translation.get_text('Back')}",
                callback_data="system_back"
            ),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


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


def get_downloads_keyboard(
    trans_enabled: bool, sab_enabled: bool,
) -> InlineKeyboardMarkup:
    """Get downloads sub-menu keyboard"""
    translation = TranslationService()
    keyboard = []
    if trans_enabled:
        keyboard.append([
            InlineKeyboardButton(
                "📡 Transmission", callback_data="dl_transmission"
            )
        ])
    if sab_enabled:
        keyboard.append([
            InlineKeyboardButton(
                "📥 SABnzbd", callback_data="dl_sabnzbd"
            )
        ])
    keyboard.append([
        InlineKeyboardButton(
            f"◀️ {translation.get_text('Back')}",
            callback_data="dl_back"
        )
    ])
    return InlineKeyboardMarkup(keyboard)


def get_transmission_settings_keyboard(
    enabled: bool, alt_speed_enabled: bool,
) -> InlineKeyboardMarkup:
    """Get Transmission settings keyboard"""
    translation = TranslationService()
    status = "✅" if enabled else "❌"
    turtle = "🐢 On" if alt_speed_enabled else "🐢 Off"
    keyboard = [
        [InlineKeyboardButton(
            f"{status} Enabled — tap to toggle",
            callback_data="dl_trans_toggle"
        )],
        [InlineKeyboardButton(
            f"Turtle Mode: {turtle}",
            callback_data="dl_trans_turtle"
        )],
        [InlineKeyboardButton(
            f"◀️ {translation.get_text('Back')}",
            callback_data="dl_back"
        )],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_sabnzbd_settings_keyboard(
    enabled: bool,
) -> InlineKeyboardMarkup:
    """Get SABnzbd settings keyboard"""
    translation = TranslationService()
    status = "✅" if enabled else "❌"
    keyboard = [
        [InlineKeyboardButton(
            f"{status} Enabled — tap to toggle",
            callback_data="dl_sab_toggle"
        )],
        [InlineKeyboardButton(
            "⚡ Speed Limit", callback_data="dl_sab_speed"
        )],
        [InlineKeyboardButton(
            "⏸ Pause / ▶️ Resume", callback_data="dl_sab_pause"
        )],
        [InlineKeyboardButton(
            f"◀️ {translation.get_text('Back')}",
            callback_data="dl_back"
        )],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_users_keyboard(
    admin_enabled: bool, allowlist_enabled: bool,
    admin_count: int, auth_count: int,
) -> InlineKeyboardMarkup:
    """Get users sub-menu keyboard"""
    translation = TranslationService()
    admin_status = "✅" if admin_enabled else "❌"
    allowlist_status = "✅" if allowlist_enabled else "❌"
    keyboard = [
        [InlineKeyboardButton(
            f"{admin_status} Admin Mode ({admin_count} admins)",
            callback_data="usr_toggle_admin"
        )],
        [InlineKeyboardButton(
            f"{allowlist_status} Allowlist ({auth_count} users)",
            callback_data="usr_toggle_allowlist"
        )],
        [InlineKeyboardButton(
            f"◀️ {translation.get_text('Back')}",
            callback_data="usr_back"
        )],
    ]
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


def get_search_results_list_keyboard(
    results: list, page: int, page_size: int = 5, search_type: str = "movie"
) -> InlineKeyboardMarkup:
    """Get paginated list keyboard for search results.

    Args:
        results: Full list of search results.
        page: Current page (0-indexed).
        page_size: Number of results per page.
        search_type: "movie", "series", or "music" for emoji prefix.
    """
    emoji_map = {"movie": "\U0001f3ac", "series": "\U0001f4fa", "music": "\U0001f3b5"}
    music_type_emoji = {"artist": "\U0001f3a4", "album": "\U0001f4bf", "song": "\U0001f3b5"}
    default_emoji = emoji_map.get(search_type, "\U0001f3ac")

    total_pages = max(1, -(-len(results) // page_size))  # ceil division
    start = page * page_size
    end = start + page_size
    page_results = results[start:end]

    keyboard = []

    # Result buttons
    for i, result in enumerate(page_results):
        idx = start + i
        # Per-result emoji for music based on music_type
        if search_type == "music" and "music_type" in result:
            emoji = music_type_emoji.get(result["music_type"], default_emoji)
        else:
            emoji = default_emoji
        keyboard.append([
            InlineKeyboardButton(
                f"{emoji} {result['title']}",
                callback_data=f"listsel_{idx}"
            )
        ])

    # Pagination row (only if more than one page)
    if total_pages > 1:
        nav_row = []
        if page > 0:
            nav_row.append(
                InlineKeyboardButton(
                    "\u25c0\ufe0f Prev",
                    callback_data=f"listpage_{page - 1}"
                )
            )
        nav_row.append(
            InlineKeyboardButton(
                f"Page {page + 1}/{total_pages}",
                callback_data="listpage_noop"
            )
        )
        if page < total_pages - 1:
            nav_row.append(
                InlineKeyboardButton(
                    "Next \u25b6\ufe0f",
                    callback_data=f"listpage_{page + 1}"
                )
            )
        keyboard.append(nav_row)

    # Bottom row: view toggle + cancel
    translation = TranslationService()
    keyboard.append([
        InlineKeyboardButton(
            "\U0001f4cb Switch to Card View",
            callback_data="viewtoggle"
        ),
        InlineKeyboardButton(
            f"\u274c {translation.get_text('Cancel')}",
            callback_data="select_cancel"
        ),
    ])

    return InlineKeyboardMarkup(keyboard)


def get_list_detail_keyboard(result_id: str) -> InlineKeyboardMarkup:
    """Get keyboard for list detail view (single result expanded).

    Args:
        result_id: The ID of the selected result.
    """
    translation = TranslationService()
    keyboard = [
        [InlineKeyboardButton(
            f"\u2705 {translation.get_text('Add')} to Library",
            callback_data=f"select_{result_id}"
        )],
        [InlineKeyboardButton(
            "\u25c0\ufe0f Back to List",
            callback_data="listback"
        )],
        [InlineKeyboardButton(
            f"\u274c {translation.get_text('Cancel')}",
            callback_data="select_cancel"
        )],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_album_monitor_mode_keyboard() -> InlineKeyboardMarkup:
    """Get album monitor mode selection keyboard.

    Prompts the user to choose between monitoring all albums
    or picking specific albums for an artist.
    """
    translation = TranslationService()
    keyboard = [
        [InlineKeyboardButton(
            f"💿 {translation.get_text('AlbumMonitorAll', default='All Albums')}",
            callback_data="album_monitor_mode_all"
        )],
        [InlineKeyboardButton(
            f"🎯 {translation.get_text('AlbumMonitorPick', default='Pick Specific Albums')}",
            callback_data="album_monitor_mode_pick"
        )],
        [InlineKeyboardButton(
            f"❌ {translation.get_text('Cancel')}",
            callback_data="menu_cancel"
        )],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_album_selection_keyboard(
    albums: list, selected_albums: set, future_mode: bool,
) -> InlineKeyboardMarkup:
    """Get album selection keyboard with toggle buttons.

    Args:
        albums: List of album dicts with album_id, title, release_date.
        selected_albums: Set of selected album IDs.
        future_mode: Whether future albums monitoring is enabled.
    """
    translation = TranslationService()
    keyboard = [
        [InlineKeyboardButton(
            f"{'✅ ' if future_mode else ''}🔄 {translation.get_text('FutureAlbums', default='Future Albums')}",
            callback_data="albumsel_future"
        )],
        [InlineKeyboardButton(
            f"💿 {translation.get_text('AllAlbums', default='All Albums')}",
            callback_data="albumsel_all"
        )],
    ]

    # Individual album buttons
    for album in albums:
        album_id = album["album_id"]
        is_selected = album_id in selected_albums
        title = album["title"]
        year = album.get("release_date", "")[:4]
        label = f"{'✅ ' if is_selected else ''}{title}"
        if year:
            label += f" ({year})"
        keyboard.append([InlineKeyboardButton(
            label, callback_data=f"albumsel_{album_id}"
        )])

    # Action buttons
    keyboard.extend([
        [InlineKeyboardButton(
            f"👁️ {translation.get_text('MonitorAll', default='Monitor All')}",
            callback_data="albumsel_monitor_all"
        )],
        [InlineKeyboardButton(
            f"✅ {translation.get_text('ConfirmSelection', default='Confirm Selection')}",
            callback_data="albumsel_confirm"
        )],
        [InlineKeyboardButton(
            f"❌ {translation.get_text('Cancel')}",
            callback_data="menu_cancel"
        )],
    ])
    return InlineKeyboardMarkup(keyboard)


def _build_period_row(days: int, translation) -> list:
    """Build the calendar period button row.

    Args:
        days: Currently selected period (7, 14, or 30).
        translation: TranslationService instance.
    """
    periods = [
        (7, translation.get_text("CalendarDays7", default="7 days")),
        (14, translation.get_text("CalendarDays14", default="14 days")),
        (30, translation.get_text("CalendarDays30", default="30 days")),
    ]
    row = []
    for period_days, label in periods:
        text = f"\u2705 {label}" if period_days == days else label
        row.append(
            InlineKeyboardButton(text, callback_data=f"cal_period_{period_days}")
        )
    return row


def get_calendar_keyboard(days: int) -> InlineKeyboardMarkup:
    """Get calendar period/navigation keyboard.

    Args:
        days: Currently selected period (7, 14, or 30).
    """
    translation = TranslationService()
    keyboard = [
        _build_period_row(days, translation),
        [InlineKeyboardButton(
            "\U0001f504 Refresh", callback_data="cal_refresh"
        )],
        [InlineKeyboardButton(
            f"\u25c0\ufe0f {translation.get_text('Back')}",
            callback_data="cal_back"
        )],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_calendar_items_keyboard(
    items: list, page: int, days: int, page_size: int = 5,
) -> InlineKeyboardMarkup:
    """Get paginated calendar items keyboard.

    Args:
        items: Full list of normalized calendar items.
        page: Current page (0-indexed).
        days: Currently selected period for period buttons.
        page_size: Number of items per page.
    """
    translation = TranslationService()
    type_emoji = {
        "movie": "\U0001f3ac",
        "episode": "\U0001f4fa",
    }

    total_pages = max(1, -(-len(items) // page_size))
    start = page * page_size
    end = start + page_size
    page_items = items[start:end]

    keyboard = []

    # Item buttons
    for item in page_items:
        emoji = type_emoji.get(item["type"], "\U0001f3ac")
        title = item["title"]
        keyboard.append([
            InlineKeyboardButton(
                f"{emoji} {title}", callback_data="cal_noop"
            )
        ])
        # Add button for non-library items
        if not item.get("in_library"):
            keyboard.append([
                InlineKeyboardButton(
                    f"\u2795 {translation.get_text('Add')}",
                    callback_data=f"cal_add_{item['type']}_{item['media_id']}"
                )
            ])

    # Pagination row
    if total_pages > 1:
        nav_row = []
        if page > 0:
            nav_row.append(
                InlineKeyboardButton(
                    "\u25c0\ufe0f Prev", callback_data=f"cal_page_{page - 1}"
                )
            )
        nav_row.append(
            InlineKeyboardButton(
                f"{page + 1}/{total_pages}", callback_data="cal_noop"
            )
        )
        if page < total_pages - 1:
            nav_row.append(
                InlineKeyboardButton(
                    "Next \u25b6\ufe0f", callback_data=f"cal_page_{page + 1}"
                )
            )
        keyboard.append(nav_row)

    # Period / refresh / back row
    keyboard.append(_build_period_row(days, translation))
    keyboard.append([
        InlineKeyboardButton(
            "\U0001f504 Refresh", callback_data="cal_refresh"
        ),
        InlineKeyboardButton(
            f"\u25c0\ufe0f {translation.get_text('Back')}",
            callback_data="cal_back"
        ),
    ])

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
