"""
Integration tests for the PreferencesHandler flow.

Tests /preferences command and pref_toggle_view callback through the full
handler chain.
"""

from unittest.mock import patch

import pytest

from src.services.preferences import PreferencesService


@pytest.mark.asyncio
async def test_preferences_command_shows_current_mode(harness):
    """/preferences returns sendMessage with current view mode and toggle button."""
    with patch.object(PreferencesService, "get_view_mode", return_value="list"):
        resp = await harness.send_command("/preferences")

    assert resp is not None
    assert resp.method == "sendMessage"
    assert "Preferences" in resp.text
    assert resp.reply_markup is not None


@pytest.mark.asyncio
async def test_toggle_view_switches_mode(harness):
    """pref_toggle_view callback edits message with updated mode text."""
    with patch.object(PreferencesService, "toggle_view_mode", return_value="card"):
        resp = await harness.tap_button("pref_toggle_view")

    assert resp is not None
    assert resp.method == "editMessageText"
    assert "Preferences" in resp.text
    assert "Card View" in resp.text
    assert resp.reply_markup is not None
