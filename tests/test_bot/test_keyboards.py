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
