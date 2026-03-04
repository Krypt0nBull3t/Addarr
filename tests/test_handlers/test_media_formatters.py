"""
Tests for src/bot/handlers/media/formatters.py — standalone formatter functions.

These functions were extracted from MediaHandler and operate purely on
message objects and result dicts without any service dependencies.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

from src.bot.handlers.media.formatters import (
    build_result_caption,
    show_result,
    show_list,
    show_list_detail,
    send_response,
)


# ---------------------------------------------------------------------------
# build_result_caption
# ---------------------------------------------------------------------------


def test_build_result_caption_movie():
    """Movie result with year, IMDB rating, and genres."""
    result = {
        "title": "Test Movie",
        "overview": "A great movie",
        "year": 2024,
        "ratings": {"imdb": "8.5", "rottenTomatoes": "92"},
        "studio": "Test Studio",
        "runtime": 120,
        "genres": ["Drama", "Thriller"],
    }

    caption = build_result_caption(result)

    assert "*Test Movie*" in caption
    assert "A great movie" in caption
    assert "2024" in caption
    assert "8.5/10" in caption
    assert "92%" in caption
    assert "Test Studio" in caption
    assert "120 minutes" in caption
    assert "Drama" in caption
    assert "Thriller" in caption


def test_build_result_caption_series():
    """Series result with network and seasons."""
    result = {
        "title": "Test Series",
        "overview": "A great series",
        "year": 2023,
        "ratings": {"tmdb": "7.8", "votes": 1500},
        "studio": "HBO",
        "network": "HBO Max",
        "genres": ["Sci-Fi"],
    }

    caption = build_result_caption(result)

    assert "*Test Series*" in caption
    assert "7.8/10" in caption
    assert "1,500 votes" in caption
    assert "HBO Max" in caption


def test_build_result_caption_album():
    """Album result with artist and release date."""
    result = {
        "title": "Test Album",
        "music_type": "album",
        "artist_name": "Test Artist",
        "release_date": "2024-01-15T00:00:00Z",
    }

    caption = build_result_caption(result)

    assert "*💿 Test Album*" in caption
    assert "Test Artist" in caption
    assert "2024-01-15" in caption


def test_build_result_caption_song():
    """Song result with album and artist."""
    result = {
        "title": "Test Song",
        "music_type": "song",
        "album_title": "Test Album",
        "artist_name": "Test Artist",
    }

    caption = build_result_caption(result)

    assert "*🎵 Test Song*" in caption
    assert "Test Album" in caption
    assert "Test Artist" in caption


def test_build_result_caption_with_index():
    """Counter line appended when index/total provided."""
    result = {
        "title": "Test Movie",
        "overview": "Overview",
    }

    caption = build_result_caption(result, index=2, total=5)

    assert "Result 3 of 5" in caption


def test_build_result_caption_long_overview_truncated():
    """Overview > 300 chars truncated to 297 + '...'."""
    result = {
        "title": "Test Movie",
        "overview": "A" * 350,
    }

    caption = build_result_caption(result)

    assert "A" * 297 + "..." in caption
    assert "A" * 298 not in caption


# ---------------------------------------------------------------------------
# send_response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_response_with_photo(make_message):
    """send_response uses edit_caption when message has photo."""
    message = make_message()
    message.photo = [MagicMock()]

    await send_response(message, "Test text")

    message.edit_caption.assert_called_once()


@pytest.mark.asyncio
async def test_send_response_without_photo(make_message):
    """send_response uses edit_text when no photo."""
    message = make_message()
    message.photo = None

    await send_response(message, "Test text")

    message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_send_response_with_reply_markup(make_message):
    """send_response passes markup through."""
    message = make_message()
    message.photo = None
    markup = MagicMock()

    await send_response(message, "Test text", reply_markup=markup)

    message.edit_text.assert_called_once_with(
        text="Test text", reply_markup=markup
    )


@pytest.mark.asyncio
async def test_send_response_fallback_on_error(make_message):
    """send_response falls back to reply_text on exception."""
    message = make_message()
    message.photo = None
    message.edit_text = AsyncMock(side_effect=Exception("Edit failed"))

    await send_response(message, "Test text")

    message.reply_text.assert_called_once()
