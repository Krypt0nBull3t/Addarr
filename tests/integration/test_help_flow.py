"""
Integration tests for the HelpHandler flow.

Tests /help command and menu_back callback through the full handler chain.
"""

import pytest


@pytest.mark.asyncio
async def test_help_command_returns_help_text(harness):
    """/help returns a sendMessage with non-empty help text."""
    resp = await harness.send_command("/help")
    assert resp is not None
    assert resp.method == "sendMessage"
    assert resp.text


@pytest.mark.asyncio
async def test_menu_back_returns_main_menu(harness):
    """menu_back callback edits message to welcome text with main menu keyboard."""
    resp = await harness.tap_button("menu_back")
    assert resp is not None
    assert resp.method == "editMessageText"
    assert resp.reply_markup is not None
