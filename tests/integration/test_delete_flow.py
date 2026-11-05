"""
Integration tests for the /delete command flow.

Uses the standard harness fixture. MediaService methods are patched at the
class level because DeleteHandler instantiates the singleton in __init__.
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.services.media import MediaService

from tests.integration.fixtures import find_response


@pytest.mark.asyncio
async def test_delete_happy_path_movie(harness):
    """Full delete flow: /delete → type → item → confirm → success."""
    movies = [{"id": "550", "title": "Fight Club"}]
    movie_detail = {"id": "550", "title": "Fight Club"}

    with patch.object(
        MediaService, "get_movies",
        new_callable=AsyncMock, return_value=movies,
    ), patch.object(
        MediaService, "get_movie",
        new_callable=AsyncMock, return_value=movie_detail,
    ), patch.object(
        MediaService, "delete_movie",
        new_callable=AsyncMock, return_value=True,
    ):
        # Step 1: /delete shows type selection keyboard
        resp = await harness.send_command("/delete")
        assert resp is not None
        assert resp.method == "sendMessage"
        assert resp.reply_markup is not None

        # Step 2: Tap movie type → shows item list with "Select"
        await harness.tap_button("delete_type_movie")
        edit_resp = find_response(harness, "editMessageText")
        assert edit_resp is not None
        assert "Select" in edit_resp.text

        # Step 3: Tap item → shows confirmation with "ThisDelete"
        await harness.tap_button("delete_item_movie_550")
        edit_resp = find_response(harness, "editMessageText")
        assert edit_resp is not None
        assert "ThisDelete" in edit_resp.text

        # Step 4: Confirm deletion → shows "DeleteSuccess"
        await harness.tap_button("delete_confirm_movie_550")
        edit_resp = find_response(harness, "editMessageText")
        assert edit_resp is not None
        assert "DeleteSuccess" in edit_resp.text


@pytest.mark.asyncio
async def test_delete_cancel(harness):
    """/delete then cancel → editMessageText with 'End'."""
    # Step 1: /delete shows type selection keyboard
    resp = await harness.send_command("/delete")
    assert resp is not None
    assert resp.method == "sendMessage"

    # Step 2: Tap cancel → shows "End"
    await harness.tap_button("delete_cancel")
    edit_resp = find_response(harness, "editMessageText")
    assert edit_resp is not None
    assert "End" in edit_resp.text


@pytest.mark.asyncio
async def test_delete_type_empty_library(harness):
    """Selecting movie type with empty library → editMessageText with 'NoExist'."""
    with patch.object(
        MediaService, "get_movies",
        new_callable=AsyncMock, return_value=[],
    ):
        # Step 1: /delete
        await harness.send_command("/delete")

        # Step 2: Tap movie type with empty library → shows "NoExist"
        await harness.tap_button("delete_type_movie")
        edit_resp = find_response(harness, "editMessageText")
        assert edit_resp is not None
        assert "NoExist" in edit_resp.text


@pytest.mark.asyncio
async def test_delete_stale_movie_list_acts_on_the_movie(harness):
    """A movie button from an old list still acts on the movie (issue 196).

    Radarr and Sonarr ids collide. After the user opens the series list, a tap
    on the older movie list must still load and delete the movie, never the
    series with the same id.
    """
    movies = [{"id": "42", "title": "Some Movie"}]
    series = [{"id": "42", "title": "Some Series"}]

    with patch.object(
        MediaService, "get_movies",
        new_callable=AsyncMock, return_value=movies,
    ), patch.object(
        MediaService, "get_series",
        new_callable=AsyncMock, return_value=series,
    ) as get_series, patch.object(
        MediaService, "get_movie",
        new_callable=AsyncMock, return_value=movies[0],
    ) as get_movie, patch.object(
        MediaService, "delete_movie",
        new_callable=AsyncMock, return_value=True,
    ) as delete_movie, patch.object(
        MediaService, "delete_series",
        new_callable=AsyncMock, return_value=True,
    ) as delete_series:
        await harness.send_command("/delete")
        await harness.tap_button("delete_type_movie")
        await harness.tap_button("delete_type_series")
        get_series.reset_mock()

        # Tap the movie button of the first list.
        await harness.tap_button("delete_item_movie_42")
        edit_resp = find_response(harness, "editMessageText")
        assert "ThisDelete" in edit_resp.text
        get_movie.assert_awaited_once_with("42")
        get_series.assert_not_called()

        await harness.tap_button("delete_confirm_movie_42")
        edit_resp = find_response(harness, "editMessageText")
        assert "DeleteSuccess" in edit_resp.text
        delete_movie.assert_awaited_once_with("42")
        delete_series.assert_not_called()
