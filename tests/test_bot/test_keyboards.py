"""Tests for src/bot/keyboards.py"""

from unittest.mock import patch

from telegram import InlineKeyboardMarkup

from src.bot.keyboards import (
    get_confirmation_keyboard,
    get_main_menu_keyboard,
    get_settings_keyboard,
    get_system_keyboard,
    get_yes_no_keyboard,
)


def _mock_translation(mock_ts):
    """Configure TranslationService mock so get_text returns the key."""
    mock_ts.return_value.get_text.side_effect = lambda key, **kw: key


class TestMainMenuKeyboard:
    """Tests for get_main_menu_keyboard"""

    @patch("src.bot.keyboards.TranslationService")
    def test_main_menu_keyboard_structure(self, mock_ts):
        """Returns InlineKeyboardMarkup with correct callback_data values"""
        _mock_translation(mock_ts)

        result = get_main_menu_keyboard()

        assert isinstance(result, InlineKeyboardMarkup)

        # Collect all callback_data values from every button
        callback_data_values = [
            button.callback_data
            for row in result.inline_keyboard
            for button in row
        ]

        expected = [
            "menu_movie",
            "menu_series",
            "menu_music",
            "menu_status",
            "menu_upcoming",
            "menu_delete",
            "menu_help",
            "menu_cancel",
        ]
        for value in expected:
            assert value in callback_data_values, (
                f"{value} not found in keyboard callback data"
            )


class TestSystemKeyboard:
    """Tests for get_system_keyboard"""

    @patch("src.bot.keyboards.TranslationService")
    def test_system_keyboard_returns_markup(self, mock_ts):
        """get_system_keyboard returns InlineKeyboardMarkup"""
        _mock_translation(mock_ts)
        result = get_system_keyboard()
        assert isinstance(result, InlineKeyboardMarkup)

    @patch("src.bot.keyboards.TranslationService")
    def test_system_keyboard_has_refresh_button(self, mock_ts):
        """Keyboard contains system_refresh callback"""
        _mock_translation(mock_ts)
        result = get_system_keyboard()
        callbacks = [
            btn.callback_data
            for row in result.inline_keyboard for btn in row
        ]
        assert "system_refresh" in callbacks

    @patch("src.bot.keyboards.TranslationService")
    def test_system_keyboard_has_details_button(self, mock_ts):
        """Keyboard contains system_details callback"""
        _mock_translation(mock_ts)
        result = get_system_keyboard()
        callbacks = [
            btn.callback_data
            for row in result.inline_keyboard for btn in row
        ]
        assert "system_details" in callbacks

    @patch("src.bot.keyboards.TranslationService")
    def test_system_keyboard_has_back_button(self, mock_ts):
        """Keyboard contains system_back callback"""
        _mock_translation(mock_ts)
        result = get_system_keyboard()
        callbacks = [
            btn.callback_data
            for row in result.inline_keyboard for btn in row
        ]
        assert "system_back" in callbacks


class TestSettingsKeyboard:
    """Tests for get_settings_keyboard"""

    @patch("src.bot.keyboards.TranslationService")
    def test_settings_keyboard_structure(self, mock_ts):
        """4 rows with correct callback_data patterns (including back)"""
        _mock_translation(mock_ts)

        result = get_settings_keyboard()

        assert isinstance(result, InlineKeyboardMarkup)
        assert len(result.inline_keyboard) == 4

        callback_data_values = [
            button.callback_data
            for row in result.inline_keyboard
            for button in row
        ]

        expected = [
            "settings_radarr",
            "settings_sonarr",
            "settings_lidarr",
            "settings_downloads",
            "settings_users",
            "settings_language",
        ]
        for value in expected:
            assert value in callback_data_values, (
                f"{value} not found in settings keyboard callback data"
            )


class TestConfirmationKeyboard:
    """Tests for get_confirmation_keyboard"""

    @patch("src.bot.keyboards.TranslationService")
    def test_confirmation_keyboard(self, mock_ts):
        """get_confirmation_keyboard('add') has confirm_add and confirm_cancel"""
        _mock_translation(mock_ts)

        result = get_confirmation_keyboard("add")

        assert isinstance(result, InlineKeyboardMarkup)

        callback_data_values = [
            button.callback_data
            for row in result.inline_keyboard
            for button in row
        ]

        assert "confirm_add" in callback_data_values
        assert "confirm_cancel" in callback_data_values


class TestYesNoKeyboard:
    """Tests for get_yes_no_keyboard"""

    def test_yes_no_keyboard(self):
        """get_yes_no_keyboard('test') has test_yes and test_no"""
        result = get_yes_no_keyboard("test")

        assert isinstance(result, InlineKeyboardMarkup)

        callback_data_values = [
            button.callback_data
            for row in result.inline_keyboard
            for button in row
        ]

        assert "test_yes" in callback_data_values
        assert "test_no" in callback_data_values

    def test_yes_no_keyboard_custom_text(self):
        """Custom yes/no text appears on buttons"""
        result = get_yes_no_keyboard("prefix", yes_text="Confirm", no_text="Deny")

        button_texts = [
            button.text
            for row in result.inline_keyboard
            for button in row
        ]

        assert "Confirm" in button_texts
        assert "Deny" in button_texts


class TestMainMenuSettingsButton:
    """Tests for settings button in main menu"""

    @patch("src.bot.keyboards.TranslationService")
    def test_main_menu_has_settings_button(self, mock_ts):
        """Main menu keyboard includes a settings button"""
        _mock_translation(mock_ts)

        result = get_main_menu_keyboard()

        callback_data_values = [
            button.callback_data
            for row in result.inline_keyboard
            for button in row
        ]
        assert "menu_settings" in callback_data_values


class TestLanguageKeyboard:
    """Tests for get_language_keyboard"""

    @patch("src.bot.keyboards.TranslationService")
    def test_get_language_keyboard_has_9_languages(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_language_keyboard

        result = get_language_keyboard()

        # Count buttons excluding the back button
        lang_buttons = [
            button
            for row in result.inline_keyboard
            for button in row
            if button.callback_data.startswith("lang_")
        ]
        assert len(lang_buttons) == 9

    @patch("src.bot.keyboards.TranslationService")
    def test_get_language_keyboard_has_back_button(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_language_keyboard

        result = get_language_keyboard()

        callback_data_values = [
            button.callback_data
            for row in result.inline_keyboard
            for button in row
        ]
        assert "settings_back" in callback_data_values


class TestServiceToggleKeyboardRemoved:
    """Verify dead code get_service_toggle_keyboard is removed"""

    def test_service_toggle_keyboard_removed(self):
        """get_service_toggle_keyboard no longer exists in keyboards module"""
        import src.bot.keyboards as kb
        assert not hasattr(kb, "get_service_toggle_keyboard")


class TestDownloadsKeyboard:
    """Tests for get_downloads_keyboard"""

    @patch("src.bot.keyboards.TranslationService")
    def test_shows_transmission_when_enabled(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_downloads_keyboard

        result = get_downloads_keyboard(trans_enabled=True, sab_enabled=False)
        callback_data = [
            btn.callback_data
            for row in result.inline_keyboard
            for btn in row
        ]
        assert "dl_transmission" in callback_data

    @patch("src.bot.keyboards.TranslationService")
    def test_shows_sabnzbd_when_enabled(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_downloads_keyboard

        result = get_downloads_keyboard(trans_enabled=False, sab_enabled=True)
        callback_data = [
            btn.callback_data
            for row in result.inline_keyboard
            for btn in row
        ]
        assert "dl_sabnzbd" in callback_data

    @patch("src.bot.keyboards.TranslationService")
    def test_has_back_button(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_downloads_keyboard

        result = get_downloads_keyboard(trans_enabled=True, sab_enabled=True)
        callback_data = [
            btn.callback_data
            for row in result.inline_keyboard
            for btn in row
        ]
        assert "dl_back" in callback_data


class TestTransmissionSettingsKeyboard:
    """Tests for get_transmission_settings_keyboard"""

    @patch("src.bot.keyboards.TranslationService")
    def test_has_toggle_button(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_transmission_settings_keyboard

        result = get_transmission_settings_keyboard(
            enabled=True, alt_speed_enabled=False
        )
        callback_data = [
            btn.callback_data
            for row in result.inline_keyboard
            for btn in row
        ]
        assert "dl_trans_toggle" in callback_data

    @patch("src.bot.keyboards.TranslationService")
    def test_has_turtle_button(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_transmission_settings_keyboard

        result = get_transmission_settings_keyboard(
            enabled=True, alt_speed_enabled=False
        )
        callback_data = [
            btn.callback_data
            for row in result.inline_keyboard
            for btn in row
        ]
        assert "dl_trans_turtle" in callback_data

    @patch("src.bot.keyboards.TranslationService")
    def test_has_back_button(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_transmission_settings_keyboard

        result = get_transmission_settings_keyboard(
            enabled=True, alt_speed_enabled=False
        )
        callback_data = [
            btn.callback_data
            for row in result.inline_keyboard
            for btn in row
        ]
        assert "dl_back" in callback_data


class TestSabnzbdSettingsKeyboard:
    """Tests for get_sabnzbd_settings_keyboard"""

    @patch("src.bot.keyboards.TranslationService")
    def test_has_toggle_button(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_sabnzbd_settings_keyboard

        result = get_sabnzbd_settings_keyboard(enabled=True)
        callback_data = [
            btn.callback_data
            for row in result.inline_keyboard
            for btn in row
        ]
        assert "dl_sab_toggle" in callback_data

    @patch("src.bot.keyboards.TranslationService")
    def test_has_speed_button(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_sabnzbd_settings_keyboard

        result = get_sabnzbd_settings_keyboard(enabled=True)
        callback_data = [
            btn.callback_data
            for row in result.inline_keyboard
            for btn in row
        ]
        assert "dl_sab_speed" in callback_data

    @patch("src.bot.keyboards.TranslationService")
    def test_has_pause_resume_button(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_sabnzbd_settings_keyboard

        result = get_sabnzbd_settings_keyboard(enabled=True)
        callback_data = [
            btn.callback_data
            for row in result.inline_keyboard
            for btn in row
        ]
        assert "dl_sab_pause" in callback_data

    @patch("src.bot.keyboards.TranslationService")
    def test_has_back_button(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_sabnzbd_settings_keyboard

        result = get_sabnzbd_settings_keyboard(enabled=True)
        callback_data = [
            btn.callback_data
            for row in result.inline_keyboard
            for btn in row
        ]
        assert "dl_back" in callback_data


class TestUsersKeyboard:
    """Tests for get_users_keyboard"""

    @patch("src.bot.keyboards.TranslationService")
    def test_has_admin_toggle(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_users_keyboard

        result = get_users_keyboard(
            admin_enabled=False, allowlist_enabled=False,
            admin_count=0, auth_count=1
        )
        callback_data = [
            btn.callback_data
            for row in result.inline_keyboard
            for btn in row
        ]
        assert "usr_toggle_admin" in callback_data

    @patch("src.bot.keyboards.TranslationService")
    def test_has_allowlist_toggle(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_users_keyboard

        result = get_users_keyboard(
            admin_enabled=False, allowlist_enabled=False,
            admin_count=0, auth_count=1
        )
        callback_data = [
            btn.callback_data
            for row in result.inline_keyboard
            for btn in row
        ]
        assert "usr_toggle_allowlist" in callback_data

    @patch("src.bot.keyboards.TranslationService")
    def test_has_back_button(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_users_keyboard

        result = get_users_keyboard(
            admin_enabled=True, allowlist_enabled=True,
            admin_count=2, auth_count=5
        )
        callback_data = [
            btn.callback_data
            for row in result.inline_keyboard
            for btn in row
        ]
        assert "usr_back" in callback_data


class TestQualityProfileKeyboard:
    """Tests for get_quality_profile_keyboard"""

    @patch("src.bot.keyboards.TranslationService")
    def test_get_quality_profile_keyboard(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_quality_profile_keyboard

        profiles = [
            {"id": 1, "name": "Any"},
            {"id": 4, "name": "HD-1080p"},
            {"id": 6, "name": "Ultra-HD"},
        ]
        result = get_quality_profile_keyboard(profiles, "radarr")

        callback_data_values = [
            button.callback_data
            for row in result.inline_keyboard
            for button in row
        ]
        assert "setquality_radarr_1" in callback_data_values
        assert "setquality_radarr_4" in callback_data_values
        assert "setquality_radarr_6" in callback_data_values

    @patch("src.bot.keyboards.TranslationService")
    def test_get_quality_profile_keyboard_has_back_button(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_quality_profile_keyboard

        profiles = [{"id": 1, "name": "Any"}]
        result = get_quality_profile_keyboard(profiles, "radarr")

        callback_data_values = [
            button.callback_data
            for row in result.inline_keyboard
            for button in row
        ]
        assert "settings_back" in callback_data_values


class TestSettingsKeyboardBackButton:
    """Tests for back button in settings keyboard"""

    @patch("src.bot.keyboards.TranslationService")
    def test_settings_keyboard_has_back_button(self, mock_ts):
        _mock_translation(mock_ts)

        result = get_settings_keyboard()

        callback_data_values = [
            button.callback_data
            for row in result.inline_keyboard
            for button in row
        ]
        assert "settings_back" in callback_data_values


# ---------------------------------------------------------------------------
# get_search_results_list_keyboard
# ---------------------------------------------------------------------------


class TestSearchResultsListKeyboard:
    """Tests for the paginated search results list keyboard."""

    def _make_results(self, count=3):
        """Create sample search results."""
        return [
            {"id": str(i), "title": f"Movie {i}", "overview": "Overview"}
            for i in range(count)
        ]

    @patch("src.bot.keyboards.TranslationService")
    def test_renders_result_titles_with_movie_emoji(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_search_results_list_keyboard

        results = self._make_results(3)
        keyboard = get_search_results_list_keyboard(
            results, page=0, page_size=5, search_type="movie"
        )
        buttons = keyboard.inline_keyboard

        for i in range(3):
            assert buttons[i][0].text.startswith("\U0001f3ac")
            assert f"Movie {i}" in buttons[i][0].text
            assert buttons[i][0].callback_data == f"listsel_{i}"

    @patch("src.bot.keyboards.TranslationService")
    def test_renders_series_emoji(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_search_results_list_keyboard

        results = self._make_results(2)
        keyboard = get_search_results_list_keyboard(
            results, page=0, page_size=5, search_type="series"
        )
        buttons = keyboard.inline_keyboard

        for i in range(2):
            assert buttons[i][0].text.startswith("\U0001f4fa")

    @patch("src.bot.keyboards.TranslationService")
    def test_renders_music_emoji(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_search_results_list_keyboard

        results = self._make_results(2)
        keyboard = get_search_results_list_keyboard(
            results, page=0, page_size=5, search_type="music"
        )
        buttons = keyboard.inline_keyboard

        for i in range(2):
            assert buttons[i][0].text.startswith("\U0001f3b5")

    @patch("src.bot.keyboards.TranslationService")
    def test_renders_per_result_music_type_emoji(self, mock_ts):
        """Music results with music_type use per-result emoji."""
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_search_results_list_keyboard

        results = [
            {"id": "1", "title": "Artist A", "music_type": "artist"},
            {"id": "2", "title": "Album B", "music_type": "album"},
            {"id": "3", "title": "Song C", "music_type": "song"},
        ]
        keyboard = get_search_results_list_keyboard(
            results, page=0, page_size=5, search_type="music"
        )
        buttons = keyboard.inline_keyboard

        # artist = 🎤, album = 💿, song = 🎵
        assert buttons[0][0].text.startswith("\U0001f3a4")
        assert buttons[1][0].text.startswith("\U0001f4bf")
        assert buttons[2][0].text.startswith("\U0001f3b5")

    @patch("src.bot.keyboards.TranslationService")
    def test_pagination_buttons_on_first_page(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_search_results_list_keyboard

        results = self._make_results(10)
        keyboard = get_search_results_list_keyboard(
            results, page=0, page_size=5, search_type="movie"
        )
        buttons = keyboard.inline_keyboard

        # After 5 result rows, should have pagination row
        pagination_row = buttons[5]
        page_btn = next(
            b for b in pagination_row if b.callback_data == "listpage_noop"
        )
        assert "1" in page_btn.text and "2" in page_btn.text

        next_btn = next(
            b for b in pagination_row if b.callback_data == "listpage_1"
        )
        assert "\u25b6" in next_btn.text

        # No prev button on first page
        prev_cbs = [b.callback_data for b in pagination_row]
        assert "listpage_-1" not in prev_cbs

    @patch("src.bot.keyboards.TranslationService")
    def test_pagination_buttons_on_last_page(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_search_results_list_keyboard

        results = self._make_results(10)
        keyboard = get_search_results_list_keyboard(
            results, page=1, page_size=5, search_type="movie"
        )
        buttons = keyboard.inline_keyboard

        pagination_row = buttons[5]
        prev_btn = next(
            b for b in pagination_row if b.callback_data == "listpage_0"
        )
        assert "\u25c0" in prev_btn.text

        # No next button on last page
        next_cbs = [b.callback_data for b in pagination_row]
        assert "listpage_2" not in next_cbs

    @patch("src.bot.keyboards.TranslationService")
    def test_page_indicator_shows_correct_page(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_search_results_list_keyboard

        results = self._make_results(15)
        keyboard = get_search_results_list_keyboard(
            results, page=1, page_size=5, search_type="movie"
        )
        buttons = keyboard.inline_keyboard

        pagination_row = buttons[5]
        page_btn = next(
            b for b in pagination_row if b.callback_data == "listpage_noop"
        )
        assert "2" in page_btn.text and "3" in page_btn.text

    @patch("src.bot.keyboards.TranslationService")
    def test_single_page_omits_pagination_row(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_search_results_list_keyboard

        results = self._make_results(3)
        keyboard = get_search_results_list_keyboard(
            results, page=0, page_size=5, search_type="movie"
        )
        buttons = keyboard.inline_keyboard

        # 3 result rows + 1 bottom row (viewtoggle + cancel) = 4 total
        assert len(buttons) == 4

        all_callbacks = [
            b.callback_data for row in buttons for b in row
        ]
        assert not any(
            cb.startswith("listpage_") for cb in all_callbacks
        )

    @patch("src.bot.keyboards.TranslationService")
    def test_bottom_row_has_viewtoggle_and_cancel(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_search_results_list_keyboard

        results = self._make_results(3)
        keyboard = get_search_results_list_keyboard(
            results, page=0, page_size=5, search_type="movie"
        )
        buttons = keyboard.inline_keyboard

        bottom_row = buttons[-1]
        callbacks = [b.callback_data for b in bottom_row]
        assert "viewtoggle" in callbacks
        assert "select_cancel" in callbacks

    @patch("src.bot.keyboards.TranslationService")
    def test_page_slices_results_correctly(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_search_results_list_keyboard

        results = self._make_results(8)
        keyboard = get_search_results_list_keyboard(
            results, page=1, page_size=5, search_type="movie"
        )
        buttons = keyboard.inline_keyboard

        result_rows = [
            row for row in buttons
            if row[0].callback_data.startswith("listsel_")
        ]
        assert len(result_rows) == 3
        assert result_rows[0][0].callback_data == "listsel_5"
        assert result_rows[2][0].callback_data == "listsel_7"


# ---------------------------------------------------------------------------
# get_list_detail_keyboard
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# get_album_monitor_mode_keyboard
# ---------------------------------------------------------------------------


class TestAlbumMonitorModeKeyboard:
    """Tests for get_album_monitor_mode_keyboard"""

    @patch("src.bot.keyboards.TranslationService")
    def test_has_all_albums_button(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_album_monitor_mode_keyboard

        result = get_album_monitor_mode_keyboard()
        callbacks = [
            btn.callback_data
            for row in result.inline_keyboard for btn in row
        ]
        assert "album_monitor_mode_all" in callbacks

    @patch("src.bot.keyboards.TranslationService")
    def test_has_pick_specific_button(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_album_monitor_mode_keyboard

        result = get_album_monitor_mode_keyboard()
        callbacks = [
            btn.callback_data
            for row in result.inline_keyboard for btn in row
        ]
        assert "album_monitor_mode_pick" in callbacks

    @patch("src.bot.keyboards.TranslationService")
    def test_has_cancel_button(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_album_monitor_mode_keyboard

        result = get_album_monitor_mode_keyboard()
        callbacks = [
            btn.callback_data
            for row in result.inline_keyboard for btn in row
        ]
        assert "menu_cancel" in callbacks

    @patch("src.bot.keyboards.TranslationService")
    def test_returns_inline_keyboard_markup(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_album_monitor_mode_keyboard

        result = get_album_monitor_mode_keyboard()
        assert isinstance(result, InlineKeyboardMarkup)


# ---------------------------------------------------------------------------
# get_album_selection_keyboard
# ---------------------------------------------------------------------------


class TestAlbumSelectionKeyboard:
    """Tests for get_album_selection_keyboard"""

    SAMPLE_ALBUMS = [
        {"album_id": "abc-123", "title": "Album One", "release_date": "2020-01-01"},
        {"album_id": "def-456", "title": "Album Two", "release_date": "2021-06-15"},
    ]

    @patch("src.bot.keyboards.TranslationService")
    def test_returns_inline_keyboard_markup(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_album_selection_keyboard

        result = get_album_selection_keyboard(self.SAMPLE_ALBUMS, set(), False)
        assert isinstance(result, InlineKeyboardMarkup)

    @patch("src.bot.keyboards.TranslationService")
    def test_has_album_buttons(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_album_selection_keyboard

        result = get_album_selection_keyboard(self.SAMPLE_ALBUMS, set(), False)
        callbacks = [
            btn.callback_data
            for row in result.inline_keyboard for btn in row
        ]
        assert "albumsel_abc-123" in callbacks
        assert "albumsel_def-456" in callbacks

    @patch("src.bot.keyboards.TranslationService")
    def test_selected_albums_show_checkmarks(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_album_selection_keyboard

        result = get_album_selection_keyboard(
            self.SAMPLE_ALBUMS, {"abc-123"}, False
        )
        # Find the button for abc-123
        for row in result.inline_keyboard:
            for btn in row:
                if btn.callback_data == "albumsel_abc-123":
                    assert "✅" in btn.text
                if btn.callback_data == "albumsel_def-456":
                    assert "✅" not in btn.text

    @patch("src.bot.keyboards.TranslationService")
    def test_all_albums_button_uses_album_key(self, mock_ts):
        """All Albums button uses AllAlbums key, not AllSeasons."""
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_album_selection_keyboard

        result = get_album_selection_keyboard(self.SAMPLE_ALBUMS, set(), False)
        for row in result.inline_keyboard:
            for btn in row:
                if btn.callback_data == "albumsel_all":
                    # Should use album emoji, not TV emoji
                    assert "💿" in btn.text
                    assert "📺" not in btn.text

    @patch("src.bot.keyboards.TranslationService")
    def test_has_all_toggle_button(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_album_selection_keyboard

        result = get_album_selection_keyboard(self.SAMPLE_ALBUMS, set(), False)
        callbacks = [
            btn.callback_data
            for row in result.inline_keyboard for btn in row
        ]
        assert "albumsel_all" in callbacks

    @patch("src.bot.keyboards.TranslationService")
    def test_has_future_toggle_button(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_album_selection_keyboard

        result = get_album_selection_keyboard(self.SAMPLE_ALBUMS, set(), False)
        callbacks = [
            btn.callback_data
            for row in result.inline_keyboard for btn in row
        ]
        assert "albumsel_future" in callbacks

    @patch("src.bot.keyboards.TranslationService")
    def test_future_mode_shows_checkmark(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_album_selection_keyboard

        result = get_album_selection_keyboard(self.SAMPLE_ALBUMS, set(), True)
        for row in result.inline_keyboard:
            for btn in row:
                if btn.callback_data == "albumsel_future":
                    assert "✅" in btn.text

    @patch("src.bot.keyboards.TranslationService")
    def test_has_monitor_all_button(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_album_selection_keyboard

        result = get_album_selection_keyboard(self.SAMPLE_ALBUMS, set(), False)
        callbacks = [
            btn.callback_data
            for row in result.inline_keyboard for btn in row
        ]
        assert "albumsel_monitor_all" in callbacks

    @patch("src.bot.keyboards.TranslationService")
    def test_has_confirm_button(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_album_selection_keyboard

        result = get_album_selection_keyboard(self.SAMPLE_ALBUMS, set(), False)
        callbacks = [
            btn.callback_data
            for row in result.inline_keyboard for btn in row
        ]
        assert "albumsel_confirm" in callbacks

    @patch("src.bot.keyboards.TranslationService")
    def test_has_cancel_button(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_album_selection_keyboard

        result = get_album_selection_keyboard(self.SAMPLE_ALBUMS, set(), False)
        callbacks = [
            btn.callback_data
            for row in result.inline_keyboard for btn in row
        ]
        assert "menu_cancel" in callbacks


# ---------------------------------------------------------------------------
# Calendar keyboards
# ---------------------------------------------------------------------------


class TestCalendarKeyboard:
    """Tests for get_calendar_keyboard"""

    @patch("src.bot.keyboards.TranslationService")
    def test_returns_inline_keyboard_markup(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_calendar_keyboard

        result = get_calendar_keyboard(days=7)
        assert isinstance(result, InlineKeyboardMarkup)

    @patch("src.bot.keyboards.TranslationService")
    def test_has_period_buttons(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_calendar_keyboard

        result = get_calendar_keyboard(days=7)
        callbacks = [
            btn.callback_data
            for row in result.inline_keyboard for btn in row
        ]
        assert "cal_period_7" in callbacks
        assert "cal_period_14" in callbacks
        assert "cal_period_30" in callbacks

    @patch("src.bot.keyboards.TranslationService")
    def test_current_period_highlighted(self, mock_ts):
        """Current period button should have a checkmark."""
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_calendar_keyboard

        result = get_calendar_keyboard(days=14)
        for row in result.inline_keyboard:
            for btn in row:
                if btn.callback_data == "cal_period_14":
                    assert "\u2705" in btn.text
                elif btn.callback_data in ("cal_period_7", "cal_period_30"):
                    assert "\u2705" not in btn.text

    @patch("src.bot.keyboards.TranslationService")
    def test_has_refresh_button(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_calendar_keyboard

        result = get_calendar_keyboard(days=7)
        callbacks = [
            btn.callback_data
            for row in result.inline_keyboard for btn in row
        ]
        assert "cal_refresh" in callbacks

    @patch("src.bot.keyboards.TranslationService")
    def test_has_back_button(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_calendar_keyboard

        result = get_calendar_keyboard(days=7)
        callbacks = [
            btn.callback_data
            for row in result.inline_keyboard for btn in row
        ]
        assert "cal_back" in callbacks


class TestCalendarItemsKeyboard:
    """Tests for get_calendar_items_keyboard"""

    SAMPLE_ITEMS = [
        {"type": "movie", "title": "Movie A", "in_library": True,
         "media_id": "100", "date": "2026-03-10", "date_label": "Cinema"},
        {"type": "movie", "title": "Movie B", "in_library": False,
         "media_id": "200", "date": "2026-03-12", "date_label": "Digital"},
        {"type": "episode", "title": "Pilot", "in_library": False,
         "media_id": "9000", "series_title": "New Show",
         "date": "2026-03-15", "date_label": "Airing"},
    ]

    @patch("src.bot.keyboards.TranslationService")
    def test_returns_inline_keyboard_markup(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_calendar_items_keyboard

        result = get_calendar_items_keyboard(self.SAMPLE_ITEMS, page=0, days=7)
        assert isinstance(result, InlineKeyboardMarkup)

    @patch("src.bot.keyboards.TranslationService")
    def test_item_buttons_present(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_calendar_items_keyboard

        result = get_calendar_items_keyboard(self.SAMPLE_ITEMS, page=0, days=7)
        button_texts = [
            btn.text
            for row in result.inline_keyboard for btn in row
        ]
        text_joined = " ".join(button_texts)
        assert "Movie A" in text_joined
        assert "Movie B" in text_joined

    @patch("src.bot.keyboards.TranslationService")
    def test_add_buttons_only_for_non_library(self, mock_ts):
        """Non-library items get cal_add_* callback, library items don't."""
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_calendar_items_keyboard

        result = get_calendar_items_keyboard(self.SAMPLE_ITEMS, page=0, days=7)
        callbacks = [
            btn.callback_data
            for row in result.inline_keyboard for btn in row
        ]
        # Movie B (not in library, movie) should have add button
        assert "cal_add_movie_200" in callbacks
        # Pilot (not in library, episode) should have add button
        assert "cal_add_episode_9000" in callbacks
        # Movie A (in library) should NOT have add button
        assert "cal_add_movie_100" not in callbacks

    @patch("src.bot.keyboards.TranslationService")
    def test_pagination_when_items_exceed_page_size(self, mock_ts):
        """Pagination buttons appear when items > page_size."""
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_calendar_items_keyboard

        items = [
            {"type": "movie", "title": f"M{i}", "in_library": True,
             "media_id": str(i), "date": "2026-03-10", "date_label": "Cinema"}
            for i in range(8)
        ]
        result = get_calendar_items_keyboard(items, page=0, days=7, page_size=5)
        callbacks = [
            btn.callback_data
            for row in result.inline_keyboard for btn in row
        ]
        assert "cal_page_1" in callbacks

    @patch("src.bot.keyboards.TranslationService")
    def test_pagination_prev_button_on_page_1(self, mock_ts):
        """Page 1 should have a Prev button pointing to page 0."""
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_calendar_items_keyboard

        items = [
            {"type": "movie", "title": f"M{i}", "in_library": True,
             "media_id": str(i), "date": "2026-03-10", "date_label": "Cinema"}
            for i in range(8)
        ]
        result = get_calendar_items_keyboard(items, page=1, days=7, page_size=5)
        callbacks = [
            btn.callback_data
            for row in result.inline_keyboard for btn in row
        ]
        assert "cal_page_0" in callbacks

    @patch("src.bot.keyboards.TranslationService")
    def test_no_pagination_for_single_page(self, mock_ts):
        """No pagination buttons when items fit in one page."""
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_calendar_items_keyboard

        result = get_calendar_items_keyboard(
            self.SAMPLE_ITEMS, page=0, days=7, page_size=5
        )
        callbacks = [
            btn.callback_data
            for row in result.inline_keyboard for btn in row
        ]
        assert not any(cb.startswith("cal_page_") for cb in callbacks)

    @patch("src.bot.keyboards.TranslationService")
    def test_has_period_refresh_back_buttons(self, mock_ts):
        """Bottom row has period, refresh, and back buttons."""
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_calendar_items_keyboard

        result = get_calendar_items_keyboard(self.SAMPLE_ITEMS, page=0, days=7)
        callbacks = [
            btn.callback_data
            for row in result.inline_keyboard for btn in row
        ]
        assert "cal_period_7" in callbacks
        assert "cal_refresh" in callbacks
        assert "cal_back" in callbacks


class TestListDetailKeyboard:
    """Tests for the list detail view keyboard."""

    @patch("src.bot.keyboards.TranslationService")
    def test_add_button_with_correct_id(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_list_detail_keyboard

        keyboard = get_list_detail_keyboard("movie_123")
        buttons = keyboard.inline_keyboard

        add_btn = buttons[0][0]
        assert add_btn.callback_data == "select_movie_123"
        assert "Add" in add_btn.text

    @patch("src.bot.keyboards.TranslationService")
    def test_back_button(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_list_detail_keyboard

        keyboard = get_list_detail_keyboard("movie_123")
        buttons = keyboard.inline_keyboard

        back_btn = buttons[1][0]
        assert back_btn.callback_data == "listback"

    @patch("src.bot.keyboards.TranslationService")
    def test_cancel_button(self, mock_ts):
        _mock_translation(mock_ts)
        from src.bot.keyboards import get_list_detail_keyboard

        keyboard = get_list_detail_keyboard("movie_123")
        buttons = keyboard.inline_keyboard

        cancel_btn = buttons[2][0]
        assert cancel_btn.callback_data == "select_cancel"
