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
    """settings -> back ends the conversation."""
    with patch("src.bot.handlers.settings.is_admin", return_value=True):
        await harness.send_command("/settings")

        await harness.tap_button("settings_back")
        edit_resp = find_response(harness, "editMessageText")
        assert edit_resp is not None
        assert edit_resp.text == "Done."


@pytest.mark.asyncio
async def test_settings_command_reenters_open_conversation(harness):
    """/settings while settings is already open shows the menu again."""
    with patch("src.bot.handlers.settings.is_admin", return_value=True):
        await harness.send_command("/settings")
        resp = await harness.send_command("/settings")

    assert resp is not None
    assert resp.text == "⚙️ Settings"
