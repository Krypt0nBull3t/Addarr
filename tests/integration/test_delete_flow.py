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
        await harness.tap_button("delete_item_550")
        edit_resp = find_response(harness, "editMessageText")
        assert edit_resp is not None
        assert "ThisDelete" in edit_resp.text

        # Step 4: Confirm deletion → shows "DeleteSuccess"
        await harness.tap_button("delete_confirm")
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
