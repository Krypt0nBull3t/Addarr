"""
Integration tests for media conversation flows (movie, series, music).

Tests the full conversation lifecycle through real PTB handlers,
mocking MediaService methods on the singleton instance since the
handler holds a reference obtained at construction time.
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.services.media import MediaService

from tests.integration.fixtures import (
    MOVIE_SEARCH_RESULTS,
    MOVIE_QUALITY_RESULT,
    SERIES_SEARCH_RESULTS,
    SERIES_QUALITY_RESULT,
    MUSIC_ARTIST_RESULTS,
    MUSIC_QUALITY_RESULT,
    MUSIC_ALBUM_RESULTS,
    MUSIC_ALBUM_QUALITY_RESULT,
)

MEDIA_CONVERSATION = "media_conversation"


@pytest.mark.asyncio
async def test_movie_happy_path(harness):
    """/movie -> search -> select -> quality -> added."""
    with (
        patch.object(MediaService, "search_movies", new_callable=AsyncMock, return_value=MOVIE_SEARCH_RESULTS),
        patch.object(MediaService, "add_movie", new_callable=AsyncMock, return_value=MOVIE_QUALITY_RESULT),
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
        state = harness.get_conversation_state(MEDIA_CONVERSATION, 12345, 12345)
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
        patch.object(MediaService, "add_movie", new_callable=AsyncMock, return_value=MOVIE_QUALITY_RESULT),
    ):
        await harness.send_command("/movie")
        await harness.send_text("fight club")
        await harness.tap_button("select_550")
        resp = await harness.tap_button("quality_cancel")
        assert resp is not None
        assert "cancel" in resp.text.lower()


# --- Series tests ---


@pytest.mark.asyncio
async def test_series_happy_path(harness):
    """/series -> search -> select -> quality -> season select -> confirm -> added."""
    with (
        patch.object(MediaService, "search_series", new_callable=AsyncMock, return_value=SERIES_SEARCH_RESULTS),
        patch.object(MediaService, "add_series", new_callable=AsyncMock, return_value=SERIES_QUALITY_RESULT),
        patch.object(MediaService, "add_series_with_profile", new_callable=AsyncMock, return_value=(True, "Breaking Bad added successfully")),
    ):
        resp = await harness.send_command("/series")
        assert "Title" in resp.text

        resp = await harness.send_text("breaking bad")
        assert len(harness.responses) >= 1

        resp = await harness.tap_button("select_81189")
        assert resp is not None
        assert "quality" in resp.text.lower() or "HD-1080p" in resp.text

        # Select quality -> should show season picker
        resp = await harness.tap_button("quality_1")
        assert resp is not None
        assert "season" in resp.text.lower()

        # Select individual season, then confirm
        await harness.tap_button("season_1")
        resp = await harness.tap_button("season_confirm")
        assert resp is not None
        assert "added" in resp.text.lower() or "Breaking Bad" in resp.text


@pytest.mark.asyncio
async def test_series_monitor_all(harness):
    """Select 'Monitor All' auto-confirms with all seasons."""
    with (
        patch.object(MediaService, "search_series", new_callable=AsyncMock, return_value=SERIES_SEARCH_RESULTS),
        patch.object(MediaService, "add_series", new_callable=AsyncMock, return_value=SERIES_QUALITY_RESULT),
        patch.object(MediaService, "add_series_with_profile", new_callable=AsyncMock, return_value=(True, "Breaking Bad added")),
    ):
        await harness.send_command("/series")
        await harness.send_text("breaking bad")
        await harness.tap_button("select_81189")
        await harness.tap_button("quality_1")

        # Monitor All auto-confirms
        resp = await harness.tap_button("season_monitor_all")
        assert resp is not None
        assert "added" in resp.text.lower() or "Breaking Bad" in resp.text


# --- Music tests ---


@pytest.mark.asyncio
async def test_music_artist_happy_path(harness):
    """/music -> search -> select artist -> quality -> album monitor mode -> added."""
    with (
        patch.object(MediaService, "search_music", new_callable=AsyncMock, return_value=MUSIC_ARTIST_RESULTS),
        patch.object(MediaService, "add_music", new_callable=AsyncMock, return_value=MUSIC_QUALITY_RESULT),
        patch.object(MediaService, "add_music_with_profile", new_callable=AsyncMock, return_value=(True, "Linkin Park added successfully")),
    ):
        resp = await harness.send_command("/music")
        assert "Title" in resp.text

        resp = await harness.send_text("linkin park")
        assert len(harness.responses) >= 1

        # Select artist
        resp = await harness.tap_button("select_f59c5520-5f46-4d2c-b2c4-822eabf53419")
        assert resp is not None
        assert "quality" in resp.text.lower() or "Lossless" in resp.text

        # Select quality -> album monitor mode for artists
        resp = await harness.tap_button("quality_1")
        assert resp is not None
        assert "monitor" in resp.text.lower() or "album" in resp.text.lower()

        # Choose "Monitor All Albums"
        resp = await harness.tap_button("album_monitor_mode_all")
        assert resp is not None
        assert "added" in resp.text.lower() or "Linkin Park" in resp.text


@pytest.mark.asyncio
async def test_music_album_direct_add(harness):
    """/music -> search -> select album -> quality -> added (no album picker)."""
    with (
        patch.object(MediaService, "search_music", new_callable=AsyncMock, return_value=MUSIC_ALBUM_RESULTS),
        patch.object(MediaService, "add_music", new_callable=AsyncMock, return_value=MUSIC_ALBUM_QUALITY_RESULT),
        patch.object(MediaService, "add_music_with_profile", new_callable=AsyncMock, return_value=(True, "Hybrid Theory added")),
    ):
        resp = await harness.send_command("/music")
        assert "Title" in resp.text

        resp = await harness.send_text("hybrid theory")
        assert len(harness.responses) >= 1

        # Select album result
        resp = await harness.tap_button("select_album:b1ae2a0f")
        assert resp is not None
        assert "quality" in resp.text.lower() or "Lossless" in resp.text

        # Select quality -> direct add (album, no album picker)
        resp = await harness.tap_button("quality_1")
        assert resp is not None
        assert "added" in resp.text.lower() or "Hybrid Theory" in resp.text
