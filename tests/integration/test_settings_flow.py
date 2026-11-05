"""
Integration tests for the /settings command flow.

Settings is admin-only via is_admin() check. Uses ConversationHandler with
states: SETTINGS_MENU -> SETTINGS_LANGUAGE -> back to SETTINGS_MENU.

Patches:
- is_admin at the handler import site
- config.update_nested and config.save as no-ops to prevent disk writes
"""

import pytest
from unittest.mock import patch, MagicMock

from tests.integration.fixtures import find_response


@pytest.mark.asyncio
async def test_settings_as_admin_shows_menu(harness):
    """/settings as admin shows settings menu with keyboard."""
    with patch("src.bot.handlers.settings.is_admin", return_value=True):
        resp = await harness.send_command("/settings")
        assert resp is not None
        # Translations are not loaded here, so default= text is shown
        assert resp.text == "⚙️ Settings"
        assert resp.reply_markup is not None


@pytest.mark.asyncio
async def test_settings_as_non_admin_rejected(harness):
    """/settings as non-admin shows AdminOnly message and ends conversation."""
    with patch("src.bot.handlers.settings.is_admin", return_value=False):
        resp = await harness.send_command("/settings")
        assert resp is not None
        assert resp.text == "Settings are only available to admins."


@pytest.mark.asyncio
async def test_settings_language_flow(harness):
    """settings -> language menu -> select language -> confirmed."""
    with (
        patch("src.bot.handlers.settings.is_admin", return_value=True),
        patch("src.bot.handlers.settings.config") as mock_cfg,
    ):
        mock_cfg.get = MagicMock(return_value={})
        mock_cfg.update_nested = MagicMock()
        mock_cfg.save = MagicMock()

        # Enter settings
        await harness.send_command("/settings")

        # Tap language
        await harness.tap_button("settings_language")
        lang_resp = find_response(harness, "editMessageText")
        assert lang_resp is not None
        assert lang_resp.text == "🌐 Language"

        # Select a language
        await harness.tap_button("lang_en")
        select_resp = find_response(harness, "editMessageText")
        assert select_resp is not None
        assert select_resp.text == "✅ Language changed to en"
        mock_cfg.update_nested.assert_called_with("language", "en")
        mock_cfg.save.assert_called()


@pytest.mark.asyncio
async def test_settings_back_ends_conversation(harness):
    """settings -> back ends the conversation on the main menu."""
    with patch("src.bot.handlers.settings.is_admin", return_value=True):
        await harness.send_command("/settings")

        await harness.tap_button("settings_back")
        edit_resp = find_response(harness, "editMessageText")
        assert edit_resp is not None
        assert "Main Menu" in edit_resp.text
        assert "menu_movie" in edit_resp.reply_markup


@pytest.mark.asyncio
async def test_settings_command_reenters_open_conversation(harness):
    """/settings while settings is already open shows the menu again."""
    with patch("src.bot.handlers.settings.is_admin", return_value=True):
        await harness.send_command("/settings")
        resp = await harness.send_command("/settings")

    assert resp is not None
    assert resp.text == "⚙️ Settings"


@pytest.mark.asyncio
async def test_settings_service_toggle_says_restart_needed(harness):
    """settings -> radarr -> toggle -> reply tells the user to restart the bot."""
    with (
        patch("src.bot.handlers.settings.is_admin", return_value=True),
        patch("src.bot.handlers.settings.config") as mock_cfg,
    ):
        mock_cfg.get = MagicMock(return_value={"enable": True})
        mock_cfg.update_nested = MagicMock()
        mock_cfg.save = MagicMock()

        await harness.send_command("/settings")
        await harness.tap_button("settings_radarr")
        await harness.tap_button("svc_toggle_radarr")

        resp = find_response(harness, "editMessageText")
        assert resp is not None
        assert resp.text == (
            "✅ disabled radarr\nRestart the bot for this to take effect."
        )
        mock_cfg.update_nested.assert_called_with("radarr.enable", False)
