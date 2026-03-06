"""
Integration tests for cancel at every conversation stage.

Parametrized tests ensuring cancel works at SEARCHING, SELECTING,
QUALITY_SELECT stages and /cancel command fallback.
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.services.media import MediaService


SEARCH_RESULTS = [
    {
        "id": "550",
        "title": "Fight Club (1999)",
        "overview": "An insomniac office worker...",
        "year": 1999,
        "poster": None,
        "ratings": {"imdb": 8.8, "rottenTomatoes": 79},
        "studio": "Fox 2000 Pictures",
        "status": "released",
        "runtime": 139,
        "genres": ["Drama", "Thriller"],
        "data": {"tmdbId": 550, "title": "Fight Club"},
    },
]

QUALITY_RESULT = {
    "type": "quality_selection",
    "profiles": [{"id": 1, "name": "HD-1080p"}],
    "root_folder": "/movies",
    "movie": {"tmdbId": 550, "title": "Fight Club"},
}


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel_at", ["searching", "selecting", "quality"])
async def test_cancel_movie_at_every_state(harness, cancel_at):
    """Cancel at each conversation stage returns cancel message."""
    with (
        patch.object(MediaService, "search_movies", new_callable=AsyncMock, return_value=SEARCH_RESULTS),
        patch.object(MediaService, "add_movie", new_callable=AsyncMock, return_value=QUALITY_RESULT),
    ):
        await harness.send_command("/movie")

        if cancel_at == "searching":
            resp = await harness.tap_button("menu_cancel")
        elif cancel_at == "selecting":
            await harness.send_text("fight club")
            resp = await harness.tap_button("select_cancel")
        elif cancel_at == "quality":
            await harness.send_text("fight club")
            await harness.tap_button("select_550")
            resp = await harness.tap_button("quality_cancel")

        assert resp is not None
        assert "cancel" in resp.text.lower()

        # Conversation should have ended
        state = harness.get_conversation_state("media_conversation", 12345, 12345)
        assert state is None


@pytest.mark.asyncio
async def test_cancel_command_fallback(harness):
    """Send /cancel during conversation, assert conversation ends."""
    await harness.send_command("/movie")
    resp = await harness.send_command("/cancel")
    assert resp is not None
    assert "cancel" in resp.text.lower()

    state = harness.get_conversation_state("media_conversation", 12345, 12345)
    assert state is None
