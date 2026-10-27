"""
Integration tests for /start and the main menu.

/start only shows the menu. Each menu button must reach the handler that
owns it (MediaHandler, SettingsHandler, StartHandler), whether or not
/start was sent first.
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.bot.handlers.media import SEARCHING, SELECTING
from src.services.media import MediaService

from tests.integration.fixtures import MOVIE_SEARCH_RESULTS, MOVIE_QUALITY_RESULT

MEDIA_CONVERSATION = "media_conversation"


@pytest.mark.asyncio
async def test_start_then_movie_search_reaches_media_handler(harness):
    """/start -> Movie button -> text search -> select -> quality adds the movie."""
    with (
        patch.object(MediaService, "search_movies", new_callable=AsyncMock, return_value=MOVIE_SEARCH_RESULTS) as search,
        patch.object(MediaService, "add_movie", new_callable=AsyncMock, return_value=MOVIE_QUALITY_RESULT),
        patch.object(MediaService, "add_movie_with_profile", new_callable=AsyncMock, return_value=(True, "Fight Club added")) as add,
    ):
        await harness.send_command("/start")
        await harness.tap_button("menu_movie")
        assert harness.get_conversation_state(MEDIA_CONVERSATION) == SEARCHING

        await harness.send_text("fight club")
        search.assert_awaited_once_with("fight club")
        assert harness.get_conversation_state(MEDIA_CONVERSATION) == SELECTING

        await harness.tap_button("select_550")
        resp = await harness.tap_button("quality_1")

    add.assert_awaited_once_with("550", 1, "/movies")
    assert "Fight Club added" in resp.text
    assert harness.get_conversation_state(MEDIA_CONVERSATION) is None


@pytest.mark.asyncio
async def test_start_then_settings_opens_in_one_tap(harness):
    """/start -> Settings button opens the settings menu at once."""
    with patch("src.bot.handlers.settings.is_admin", return_value=True):
        await harness.send_command("/start")
        resp = await harness.tap_button("menu_settings")

    assert resp is not None
    assert "Settings.Menu" in resp.text


@pytest.mark.asyncio
async def test_menu_button_works_without_start(harness):
    """Main-menu keyboards shown by other screens work without /start first."""
    resp = await harness.tap_button("menu_library")

    assert resp is not None
    assert "LibraryPrompt" in resp.text


@pytest.mark.asyncio
async def test_main_menu_cancel_outside_conversation(harness):
    """/start -> Cancel button closes the menu."""
    await harness.send_command("/start")
    resp = await harness.tap_button("menu_cancel")

    assert resp is not None
    assert "Canceled" in resp.text


@pytest.mark.asyncio
async def test_menu_cancel_still_ends_media_search(harness):
    """Cancel during a search ends the media conversation, not just the menu."""
    await harness.send_command("/start")
    await harness.tap_button("menu_movie")
    await harness.tap_button("menu_cancel")

    assert harness.get_conversation_state(MEDIA_CONVERSATION) is None
