"""
Integration tests for error paths — API failures mid-conversation.

Handlers catch exceptions internally and send error text to the user.
These tests verify that error responses are sent, not that exceptions propagate.
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.services.media import MediaService

from tests.integration.fixtures import (
    MOVIE_SEARCH_RESULTS,
    MOVIE_QUALITY_RESULT,
    SERIES_SEARCH_RESULTS,
)


def _find_response(harness, method):
    """Find the first captured response matching the given API method."""
    for r in harness.responses:
        if r.method == method:
            return r
    return None


@pytest.mark.asyncio
async def test_movie_add_raises_exception_shows_error(harness):
    """Movie search OK, but add_movie_with_profile raises → error response."""
    with (
        patch.object(
            MediaService, "search_movies",
            new_callable=AsyncMock, return_value=MOVIE_SEARCH_RESULTS,
        ),
        patch.object(
            MediaService, "add_movie",
            new_callable=AsyncMock, return_value=MOVIE_QUALITY_RESULT,
        ),
        patch.object(
            MediaService, "add_movie_with_profile",
            new_callable=AsyncMock, side_effect=Exception("API timeout"),
        ),
    ):
        await harness.send_command("/movie")
        await harness.send_text("fight club")
        await harness.tap_button("select_550")

        # Quality select triggers add which raises
        await harness.tap_button("quality_1")
        # Handler catches exception and sends error text
        edit_resp = _find_response(harness, "editMessageText")
        assert edit_resp is not None
        assert "Error" in edit_resp.text or "error" in edit_resp.text.lower()


@pytest.mark.asyncio
async def test_series_search_raises_exception_shows_error(harness):
    """Series search raises exception → error response sent."""
    with patch.object(
        MediaService, "search_series",
        new_callable=AsyncMock, side_effect=Exception("Connection refused"),
    ):
        await harness.send_command("/series")

        # Type search text — handler catches the search exception
        resp = await harness.send_text("breaking bad")
        assert resp is not None
        assert "Error" in resp.text or "error" in resp.text.lower()


@pytest.mark.asyncio
async def test_delete_confirm_returns_false_shows_failure(harness):
    """Delete confirm with delete_movie returning False → failure text."""
    movies = [{"id": "550", "title": "Fight Club"}]
    movie_detail = {"id": "550", "title": "Fight Club"}

    with (
        patch.object(
            MediaService, "get_movies",
            new_callable=AsyncMock, return_value=movies,
        ),
        patch.object(
            MediaService, "get_movie",
            new_callable=AsyncMock, return_value=movie_detail,
        ),
        patch.object(
            MediaService, "delete_movie",
            new_callable=AsyncMock, return_value=False,
        ),
    ):
        await harness.send_command("/delete")
        await harness.tap_button("delete_type_movie")
        await harness.tap_button("delete_item_550")

        # Confirm deletion — returns False
        await harness.tap_button("delete_confirm")
        edit_resp = _find_response(harness, "editMessageText")
        assert edit_resp is not None
        assert "DeleteFailed" in edit_resp.text
