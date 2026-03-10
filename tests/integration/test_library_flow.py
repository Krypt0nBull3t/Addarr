"""
Integration tests for the /allMovies, /allSeries, /allMusic library flows.

Uses the standard harness fixture. MediaService methods are patched at the
class level because LibraryHandler instantiates the singleton in __init__.
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.services.media import MediaService

from tests.integration.fixtures import LIBRARY_MOVIES, LIBRARY_SERIES


def _find_response(harness, method):
    """Find the first captured response matching the given API method."""
    for r in harness.responses:
        if r.method == method:
            return r
    return None


@pytest.mark.asyncio
async def test_all_movies_shows_paginated_list(harness):
    """/allMovies with 15 movies returns paginated sendMessage."""
    with patch.object(
        MediaService, "get_movies",
        new_callable=AsyncMock, return_value=LIBRARY_MOVIES,
    ):
        resp = await harness.send_command("/allMovies")
        assert resp is not None
        assert "Movies" in resp.text
        assert "15 total" in resp.text
        assert resp.reply_markup is not None


@pytest.mark.asyncio
async def test_all_series_shows_list(harness):
    """/allSeries with 5 series returns sendMessage with count."""
    with patch.object(
        MediaService, "get_series",
        new_callable=AsyncMock, return_value=LIBRARY_SERIES,
    ):
        resp = await harness.send_command("/allSeries")
        assert resp is not None
        assert "Series" in resp.text
        assert "5 total" in resp.text


@pytest.mark.asyncio
async def test_pagination_via_lib_callback(harness):
    """/allMovies then tap lib_m_1 shows page 2 via editMessageText."""
    with patch.object(
        MediaService, "get_movies",
        new_callable=AsyncMock, return_value=LIBRARY_MOVIES,
    ):
        # Initial command caches items in user_data
        await harness.send_command("/allMovies")

        # Navigate to page 2
        await harness.tap_button("lib_m_1")
        edit_resp = _find_response(harness, "editMessageText")
        assert edit_resp is not None
        assert "Page 2" in edit_resp.text


@pytest.mark.asyncio
async def test_empty_library(harness):
    """/allMovies with empty list returns LibraryEmpty text."""
    with patch.object(
        MediaService, "get_movies",
        new_callable=AsyncMock, return_value=[],
    ):
        resp = await harness.send_command("/allMovies")
        assert resp is not None
        assert "LibraryEmpty" in resp.text
