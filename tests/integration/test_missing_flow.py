"""
Integration tests for the /missing command flow.

Uses the standard harness fixture. MediaService.get_missing_media is patched at
the class level because MissingHandler instantiates the singleton in __init__.
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.services.media import MediaService

from tests.integration.fixtures import MISSING_ITEMS, find_response


@pytest.mark.asyncio
async def test_missing_shows_items(harness):
    """/missing with mocked items returns text containing MissingTitle and count."""
    with patch.object(
        MediaService, "get_missing_media",
        new_callable=AsyncMock, return_value=MISSING_ITEMS,
    ):
        resp = await harness.send_command("/missing")
        assert resp is not None
        assert "MissingTitle" in resp.text
        assert "wanted items" in resp.text


@pytest.mark.asyncio
async def test_missing_empty(harness):
    """/missing with empty list returns text containing MissingEmpty."""
    with patch.object(
        MediaService, "get_missing_media",
        new_callable=AsyncMock, return_value=[],
    ):
        resp = await harness.send_command("/missing")
        assert resp is not None
        assert "MissingEmpty" in resp.text


@pytest.mark.asyncio
async def test_missing_refresh(harness):
    """missing_refresh callback re-fetches missing media and updates text."""
    with patch.object(
        MediaService, "get_missing_media",
        new_callable=AsyncMock, return_value=MISSING_ITEMS,
    ):
        # Initial command to set up user_data
        await harness.send_command("/missing")

        # Tap refresh — handler calls edit_text then query.answer()
        await harness.tap_button("missing_refresh")
        edit_resp = find_response(harness, "editMessageText")
        assert edit_resp is not None
        assert "MissingTitle" in edit_resp.text


@pytest.mark.asyncio
async def test_missing_back_returns_to_main_menu(harness):
    """missing_back returns editMessageText with Main Menu."""
    with patch.object(
        MediaService, "get_missing_media",
        new_callable=AsyncMock, return_value=MISSING_ITEMS,
    ):
        # Initial command to set up context
        await harness.send_command("/missing")

        # Tap back — handler calls edit_text then query.answer()
        await harness.tap_button("missing_back")
        edit_resp = find_response(harness, "editMessageText")
        assert edit_resp is not None
        assert "Main Menu" in edit_resp.text
