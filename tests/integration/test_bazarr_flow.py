"""
Integration tests for the /subtitles (Bazarr) command flow.

Uses bazarr_harness which registers BazarrHandler with BazarrService.is_enabled
patched to True. BazarrService methods are patched at class level.
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.services.bazarr import BazarrService

from tests.integration.fixtures import BAZARR_WANTED_MOVIES


def _find_response(harness, method):
    """Find the first captured response matching the given API method."""
    for r in harness.responses:
        if r.method == method:
            return r
    return None


@pytest.mark.asyncio
async def test_subtitles_menu_when_enabled(bazarr_harness):
    """/subtitles shows menu with keyboard when bazarr is enabled."""
    resp = await bazarr_harness.send_command("/subtitles")
    assert resp is not None
    assert "BazarrMenu" in resp.text
    assert resp.reply_markup is not None


@pytest.mark.asyncio
async def test_bazarr_wanted_movies_shows_list(bazarr_harness):
    """bazarr_wanted_movies callback shows formatted movie list."""
    with patch.object(
        BazarrService, "get_wanted_movies",
        new_callable=AsyncMock, return_value=BAZARR_WANTED_MOVIES,
    ):
        # Enter menu first
        await bazarr_harness.send_command("/subtitles")

        # Tap wanted movies
        await bazarr_harness.tap_button("bazarr_wanted_movies")
        edit_resp = _find_response(bazarr_harness, "editMessageText")
        assert edit_resp is not None
        assert "Fight Club" in edit_resp.text
        assert "English" in edit_resp.text


@pytest.mark.asyncio
async def test_bazarr_cancel_sends_cancelled(bazarr_harness):
    """bazarr_cancel callback sends cancelled message."""
    # Enter menu first
    await bazarr_harness.send_command("/subtitles")

    # Tap cancel
    await bazarr_harness.tap_button("bazarr_cancel")
    edit_resp = _find_response(bazarr_harness, "editMessageText")
    assert edit_resp is not None
    assert "BazarrCancelled" in edit_resp.text
