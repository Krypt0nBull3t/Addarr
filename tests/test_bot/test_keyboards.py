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
            "menu_help",
            "menu_cancel",
        ]
        for value in expected:
            assert value in callback_data_values, (
                f"{value} not found in keyboard callback data"
            )


class TestSystemKeyboard:
    """Tests for get_system_keyboard"""

    def test_system_keyboard_returns_none(self):
        """get_system_keyboard returns None"""
        result = get_system_keyboard()
        assert result is None


class TestSettingsKeyboard:
    """Tests for get_settings_keyboard"""

    @patch("src.bot.keyboards.TranslationService")
    def test_settings_keyboard_structure(self, mock_ts):
        """3 rows with correct callback_data patterns"""
        _mock_translation(mock_ts)

        result = get_settings_keyboard()

        assert isinstance(result, InlineKeyboardMarkup)
        assert len(result.inline_keyboard) == 3

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
