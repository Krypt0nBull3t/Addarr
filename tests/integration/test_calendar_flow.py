"""
Integration tests for the /upcoming (calendar) command flow.

Uses the standard harness fixture. MediaService.get_upcoming is patched at the
class level because CalendarHandler instantiates the singleton in __init__.
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.services.media import MediaService

from tests.integration.fixtures import CALENDAR_ITEMS, find_response


@pytest.mark.asyncio
async def test_upcoming_shows_items(harness):
    """/upcoming with mocked items returns text containing CalendarTitle and releases."""
    with patch.object(
        MediaService, "get_upcoming",
        new_callable=AsyncMock, return_value=CALENDAR_ITEMS,
    ):
        resp = await harness.send_command("/upcoming")
        assert resp is not None
        assert "CalendarTitle" in resp.text
        assert "releases" in resp.text
        assert str(len(CALENDAR_ITEMS)) in resp.text


@pytest.mark.asyncio
async def test_upcoming_empty_calendar(harness):
    """/upcoming with empty list returns text containing CalendarEmpty."""
    with patch.object(
        MediaService, "get_upcoming",
        new_callable=AsyncMock, return_value=[],
    ):
        resp = await harness.send_command("/upcoming")
        assert resp is not None
        assert "CalendarEmpty" in resp.text


@pytest.mark.asyncio
async def test_calendar_period_change(harness):
    """cal_period_30 callback re-fetches with 30 days and updates text."""
    mock_upcoming = AsyncMock(return_value=CALENDAR_ITEMS)
    with patch.object(MediaService, "get_upcoming", mock_upcoming):
        # Initial command to set up user_data
        await harness.send_command("/upcoming")

        # Tap period change button
        await harness.tap_button("cal_period_30")
        edit_resp = find_response(harness, "editMessageText")
        assert edit_resp is not None
        assert "30 days" in edit_resp.text

        # Verify get_upcoming was called with 30
        mock_upcoming.assert_any_call(30)


@pytest.mark.asyncio
async def test_calendar_refresh(harness):
    """cal_refresh callback re-fetches and updates text with CalendarTitle."""
    with patch.object(
        MediaService, "get_upcoming",
        new_callable=AsyncMock, return_value=CALENDAR_ITEMS,
    ):
        # Initial command to set up context
        await harness.send_command("/upcoming")

        # Tap refresh
        await harness.tap_button("cal_refresh")
        edit_resp = find_response(harness, "editMessageText")
        assert edit_resp is not None
        assert "CalendarTitle" in edit_resp.text


@pytest.mark.asyncio
async def test_calendar_back_returns_to_main_menu(harness):
    """cal_back returns editMessageText with Main Menu."""
    with patch.object(
        MediaService, "get_upcoming",
        new_callable=AsyncMock, return_value=CALENDAR_ITEMS,
    ):
        # Initial command to set up context
        await harness.send_command("/upcoming")

        # Tap back
        await harness.tap_button("cal_back")
        edit_resp = find_response(harness, "editMessageText")
        assert edit_resp is not None
        assert "Main Menu" in edit_resp.text
