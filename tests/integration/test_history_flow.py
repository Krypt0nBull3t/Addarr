"""
Integration tests for the /history command flow.

Uses the standard harness fixture. MediaService.get_history is patched at the
class level because HistoryHandler instantiates the singleton in __init__.
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.services.media import MediaService

from tests.integration.fixtures import HISTORY_ITEMS


def _find_response(harness, method):
    """Find the first captured response matching the given API method."""
    for r in harness.responses:
        if r.method == method:
            return r
    return None


@pytest.mark.asyncio
async def test_history_command_shows_items(harness):
    """/history with mocked items returns text containing HistoryTitle and count."""
    with patch.object(
        MediaService, "get_history",
        new_callable=AsyncMock, return_value=HISTORY_ITEMS,
    ):
        resp = await harness.send_command("/history")
        assert resp is not None
        assert "HistoryTitle" in resp.text
        assert str(len(HISTORY_ITEMS)) in resp.text


@pytest.mark.asyncio
async def test_history_command_empty_results(harness):
    """/history with empty list returns text containing HistoryEmpty."""
    with patch.object(
        MediaService, "get_history",
        new_callable=AsyncMock, return_value=[],
    ):
        resp = await harness.send_command("/history")
        assert resp is not None
        assert "HistoryEmpty" in resp.text


@pytest.mark.asyncio
async def test_history_refresh_refetches(harness):
    """hist_refresh callback re-fetches history and updates text."""
    with patch.object(
        MediaService, "get_history",
        new_callable=AsyncMock, return_value=HISTORY_ITEMS,
    ):
        # Initial command to set up user_data
        await harness.send_command("/history")

        # Tap refresh — handler calls edit_text then query.answer()
        await harness.tap_button("hist_refresh")
        edit_resp = _find_response(harness, "editMessageText")
        assert edit_resp is not None
        assert "HistoryTitle" in edit_resp.text


@pytest.mark.asyncio
async def test_history_back_returns_to_main_menu(harness):
    """hist_back returns editMessageText with Main Menu."""
    with patch.object(
        MediaService, "get_history",
        new_callable=AsyncMock, return_value=HISTORY_ITEMS,
    ):
        # Initial command to set up context
        await harness.send_command("/history")

        # Tap back — handler calls edit_text then query.answer()
        await harness.tap_button("hist_back")
        edit_resp = _find_response(harness, "editMessageText")
        assert edit_resp is not None
        assert "Main Menu" in edit_resp.text
