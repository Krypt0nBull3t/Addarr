"""
Integration tests for the movie search -> select -> quality -> added flow.

Tests the full conversation lifecycle through real PTB handlers,
mocking MediaService methods on the singleton instance since the
handler holds a reference obtained at construction time.
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.services.media import MediaService


MOVIE_SEARCH_RESULTS = [
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

QUALITY_SELECTION_RESULT = {
    "type": "quality_selection",
    "profiles": [
        {"id": 1, "name": "HD-1080p"},
        {"id": 2, "name": "Ultra-HD"},
    ],
    "root_folder": "/movies",
    "movie": {"tmdbId": 550, "title": "Fight Club"},
}


@pytest.mark.asyncio
async def test_movie_happy_path(harness):
    """/movie -> search -> select -> quality -> added."""
    with (
        patch.object(MediaService, "search_movies", new_callable=AsyncMock, return_value=MOVIE_SEARCH_RESULTS),
        patch.object(MediaService, "add_movie", new_callable=AsyncMock, return_value=QUALITY_SELECTION_RESULT),
        patch.object(MediaService, "add_movie_with_profile", new_callable=AsyncMock, return_value=(True, "Fight Club added successfully")),
    ):
        # Step 1: /movie -> SEARCHING
        resp = await harness.send_command("/movie")
        assert resp is not None
        assert "Title" in resp.text

        # Step 2: Type search query -> SELECTING
        resp = await harness.send_text("fight club")
        assert resp is not None
        assert len(harness.responses) >= 1

        # Step 3: Select the result -> QUALITY_SELECT
        resp = await harness.tap_button("select_550")
        assert resp is not None
        assert "quality" in resp.text.lower() or "HD-1080p" in resp.text

        # Step 4: Select quality profile -> END
        resp = await harness.tap_button("quality_1")
        assert resp is not None
        assert "added" in resp.text.lower() or "Fight Club" in resp.text


@pytest.mark.asyncio
async def test_movie_no_results(harness):
    """/movie -> search with no results -> conversation ends."""
    with patch.object(MediaService, "search_movies", new_callable=AsyncMock, return_value=[]):
        await harness.send_command("/movie")
        resp = await harness.send_text("xyznonexistent")
        assert resp is not None
        assert "no" in resp.text.lower() or "not found" in resp.text.lower()

        # Conversation should have ended
        state = harness.get_conversation_state("media_conversation", 12345, 12345)
        assert state is None


@pytest.mark.asyncio
async def test_movie_cancel_at_search(harness):
    """/movie -> cancel at SEARCHING state."""
    await harness.send_command("/movie")
    resp = await harness.tap_button("menu_cancel")
    assert resp is not None
    assert "cancel" in resp.text.lower()


@pytest.mark.asyncio
async def test_movie_cancel_at_selection(harness):
    """Search -> results shown -> cancel at SELECTING state."""
    with patch.object(MediaService, "search_movies", new_callable=AsyncMock, return_value=MOVIE_SEARCH_RESULTS):
        await harness.send_command("/movie")
        await harness.send_text("fight club")
        resp = await harness.tap_button("select_cancel")
        assert resp is not None
        assert "cancel" in resp.text.lower()


@pytest.mark.asyncio
async def test_movie_cancel_at_quality(harness):
    """Select result -> quality shown -> cancel at QUALITY_SELECT state."""
    with (
        patch.object(MediaService, "search_movies", new_callable=AsyncMock, return_value=MOVIE_SEARCH_RESULTS),
        patch.object(MediaService, "add_movie", new_callable=AsyncMock, return_value=QUALITY_SELECTION_RESULT),
    ):
        await harness.send_command("/movie")
        await harness.send_text("fight club")
        await harness.tap_button("select_550")
        resp = await harness.tap_button("quality_cancel")
        assert resp is not None
        assert "cancel" in resp.text.lower()
