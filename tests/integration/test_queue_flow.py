"""
Integration tests for the /queue command flow.

Uses the standard harness fixture. MediaService.get_queue_media is patched at
the class level because QueueHandler instantiates the singleton in __init__.
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.services.media import MediaService

from tests.integration.fixtures import QUEUE_ITEMS


def _find_response(harness, method):
    """Find the first captured response matching the given API method."""
    for r in harness.responses:
        if r.method == method:
            return r
    return None


@pytest.mark.asyncio
async def test_queue_shows_items(harness):
    """/queue with mocked items returns text containing QueueTitle and count."""
    with patch.object(
        MediaService, "get_queue_media",
        new_callable=AsyncMock, return_value=QUEUE_ITEMS,
    ):
        resp = await harness.send_command("/queue")
        assert resp is not None
        assert "QueueTitle" in resp.text
        assert "queue items" in resp.text


@pytest.mark.asyncio
async def test_queue_empty(harness):
    """/queue with empty list returns text containing QueueEmpty."""
    with patch.object(
        MediaService, "get_queue_media",
        new_callable=AsyncMock, return_value=[],
    ):
        resp = await harness.send_command("/queue")
        assert resp is not None
        assert "QueueEmpty" in resp.text


@pytest.mark.asyncio
async def test_queue_refresh(harness):
    """queue_refresh callback re-fetches queue media and updates text."""
    with patch.object(
        MediaService, "get_queue_media",
        new_callable=AsyncMock, return_value=QUEUE_ITEMS,
    ):
        # Initial command to set up user_data
        await harness.send_command("/queue")

        # Tap refresh — handler calls edit_text then query.answer()
        await harness.tap_button("queue_refresh")
        edit_resp = _find_response(harness, "editMessageText")
        assert edit_resp is not None
        assert "QueueTitle" in edit_resp.text


@pytest.mark.asyncio
async def test_queue_back_returns_to_main_menu(harness):
    """queue_back returns editMessageText with Main Menu."""
    with patch.object(
        MediaService, "get_queue_media",
        new_callable=AsyncMock, return_value=QUEUE_ITEMS,
    ):
        # Initial command to set up context
        await harness.send_command("/queue")

        # Tap back — handler calls edit_text then query.answer()
        await harness.tap_button("queue_back")
        edit_resp = _find_response(harness, "editMessageText")
        assert edit_resp is not None
        assert "Main Menu" in edit_resp.text
