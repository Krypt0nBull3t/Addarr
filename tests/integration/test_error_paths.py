"""
Integration tests for error paths — API failures mid-conversation.

Handlers catch exceptions internally and send error text to the user.
These tests verify that error responses are sent, not that exceptions propagate.
"""

import re

import pytest
from unittest.mock import AsyncMock, patch

from src.services.media import MediaService
from src.services.translation import TranslationService

from tests.integration.fixtures import (
    MOVIE_SEARCH_RESULTS,
    MOVIE_QUALITY_RESULT,
    find_response,
)


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
        edit_resp = find_response(harness, "editMessageText")
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
        edit_resp = find_response(harness, "editMessageText")
        assert edit_resp is not None
        assert "DeleteFailed" in edit_resp.text


@pytest.mark.asyncio
@pytest.mark.parametrize("command,endpoint", [
    ("/movie", "localhost:7878/api/v3/movie/lookup"),
    ("/series", "localhost:8989/api/v3/series/lookup"),
    ("/music", "localhost:8686/api/v1/artist/lookup"),
])
async def test_search_server_error_shows_search_error(harness, aio_mock, command, endpoint):
    """A server that rejects the search shows SearchError, not 'no results'."""
    aio_mock.get(
        re.compile(rf"^http://{re.escape(endpoint)}\?.*$"),
        status=401, body="Unauthorized", repeat=True,
    )
    aio_mock.get(
        re.compile(r"^http://localhost:8686/api/v1/album/lookup\?.*$"),
        payload=[], repeat=True,
    )
    await harness.send_command(command)
    resp = await harness.send_text("law & order")
    assert resp.text == TranslationService().get_text("SearchError")
