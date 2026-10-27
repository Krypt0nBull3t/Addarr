"""
Tests for src/bot/handlers/media/formatters.py — standalone formatter functions.

These functions were extracted from MediaHandler and operate purely on
message objects and result dicts without any service dependencies.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

from src.bot.handlers.media.formatters import (
    _build_external_links,
    build_result_caption,
    send_response,
    show_list_detail,
    show_result,
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

    assert "<b>Test Movie</b>" in caption
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

    assert "<b>Test Series</b>" in caption
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

    assert "<b>💿 Test Album</b>" in caption
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

    assert "<b>🎵 Test Song</b>" in caption
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


def test_build_result_caption_escapes_api_text():
    """Markup characters in API text are escaped, so Telegram cannot reject them."""
    result = {
        "title": "M*A*S*H <3",
        "overview": "Tom & Jerry_fan",
        "studio": "Snake_Case <Studio>",
        "genres": ["R&B", "Rock"],
    }

    caption = build_result_caption(result)

    assert "<b>M*A*S*H &lt;3</b>" in caption
    assert "<i>Tom &amp; Jerry_fan</i>" in caption
    assert "Snake_Case &lt;Studio&gt;" in caption
    assert "R&amp;B, Rock" in caption


def test_build_result_caption_escapes_network():
    """Network name from the API is escaped."""
    result = {
        "title": "*NSYNC Live",
        "overview": "Overview",
        "studio": "A&E",
        "network": "<Net>",
    }

    caption = build_result_caption(result)

    assert "<b>*NSYNC Live</b>" in caption
    assert "📺 Network: &lt;Net&gt; (A&amp;E)" in caption


def test_build_result_caption_album_escapes_api_text():
    """Album caption escapes title, artist, release date, and overview."""
    result = {
        "title": "Songs & <Stuff>",
        "music_type": "album",
        "artist_name": "*NSYNC",
        "release_date": "2024<01>15",
        "overview": "Rock & roll",
    }

    caption = build_result_caption(result)

    assert "<b>💿 Songs &amp; &lt;Stuff&gt;</b>" in caption
    assert "🎤 Artist: *NSYNC" in caption
    assert "📅 Released: 2024&lt;01&gt;15" in caption
    assert "<i>Rock &amp; roll</i>" in caption


def test_build_result_caption_song_escapes_api_text():
    """Song caption escapes title, album, and artist."""
    result = {
        "title": "A <B>",
        "music_type": "song",
        "album_title": "C & D",
        "artist_name": "E_F <G>",
    }

    caption = build_result_caption(result)

    assert "<b>🎵 A &lt;B&gt;</b>" in caption
    assert "💿 Album: C &amp; D" in caption
    assert "🎤 Artist: E_F &lt;G&gt;" in caption


# ---------------------------------------------------------------------------
# _build_external_links
# ---------------------------------------------------------------------------


def test_build_external_links_movie():
    """Movie with IMDB and TMDB links."""
    result = {
        "external_ids": {"imdb": "tt0137523", "tmdb": 550},
    }

    links = _build_external_links(result)

    assert '<a href="https://www.imdb.com/title/tt0137523/">IMDB</a>' in links
    assert '<a href="https://www.themoviedb.org/movie/550">TMDB</a>' in links
    assert links.startswith("\n")
    assert " | " in links


def test_build_external_links_series_with_imdb():
    """Series with TVDB and IMDB links."""
    result = {
        "external_ids": {"tvdb": 81189, "imdb": "tt0903747"},
    }

    links = _build_external_links(result)

    assert '<a href="https://thetvdb.com/?id=81189&amp;tab=series">TVDB</a>' in links
    assert '<a href="https://www.imdb.com/title/tt0903747/">IMDB</a>' in links


def test_build_external_links_series_tvdb_only():
    """Series with TVDB only (no IMDB)."""
    result = {
        "external_ids": {"tvdb": 295759, "imdb": None},
    }

    links = _build_external_links(result)

    assert ">TVDB</a>" in links
    assert "IMDB" not in links


def test_build_external_links_album():
    """Album with MusicBrainz release-group link."""
    result = {
        "music_type": "album",
        "external_ids": {"musicbrainz": "album-id-abc"},
    }

    links = _build_external_links(result)

    assert '<a href="https://musicbrainz.org/release-group/album-id-abc">MusicBrainz</a>' in links


def test_build_external_links_artist():
    """Artist with MusicBrainz artist link."""
    result = {
        "music_type": "artist",
        "external_ids": {"musicbrainz": "some-mbid-123"},
    }

    links = _build_external_links(result)

    assert '<a href="https://musicbrainz.org/artist/some-mbid-123">MusicBrainz</a>' in links


def test_build_external_links_song():
    """Song with MusicBrainz release-group link (uses album ID)."""
    result = {
        "music_type": "song",
        "external_ids": {"musicbrainz": "album-id-abc"},
    }

    links = _build_external_links(result)

    assert '<a href="https://musicbrainz.org/release-group/album-id-abc">MusicBrainz</a>' in links


def test_build_external_links_no_key():
    """Result without external_ids key returns empty string."""
    result = {"title": "Test"}

    links = _build_external_links(result)

    assert links == ""


def test_build_external_links_empty_dict():
    """Result with empty external_ids returns empty string."""
    result = {"external_ids": {}}

    links = _build_external_links(result)

    assert links == ""


def test_build_external_links_all_none():
    """Result with all None IDs returns empty string."""
    result = {"external_ids": {"imdb": None, "tmdb": None}}

    links = _build_external_links(result)

    assert links == ""


def test_build_external_links_tmdb_with_tvdb_uses_tv_path():
    """When both tmdb and tvdb are present, TMDB link uses /tv/ path."""
    result = {
        "external_ids": {"tmdb": 1396, "tvdb": 81189, "imdb": None},
    }

    links = _build_external_links(result)

    assert '<a href="https://www.themoviedb.org/tv/1396">TMDB</a>' in links


# ---------------------------------------------------------------------------
# build_result_caption with external links
# ---------------------------------------------------------------------------


def test_build_result_caption_movie_with_links():
    """Movie caption includes external links before counter."""
    result = {
        "title": "Test Movie",
        "overview": "Overview",
        "external_ids": {"imdb": "tt0137523", "tmdb": 550},
    }

    caption = build_result_caption(result, index=0, total=1)

    assert ">IMDB</a>" in caption
    assert ">TMDB</a>" in caption
    # Links should appear before counter
    links_pos = caption.index(">IMDB</a>")
    counter_pos = caption.index("Result 1 of 1")
    assert links_pos < counter_pos


def test_build_result_caption_album_with_links():
    """Album caption includes MusicBrainz link."""
    result = {
        "title": "Test Album",
        "music_type": "album",
        "artist_name": "Test Artist",
        "release_date": "2024-01-15T00:00:00Z",
        "external_ids": {"musicbrainz": "album-id-abc"},
    }

    caption = build_result_caption(result)

    assert ">MusicBrainz</a>" in caption


def test_build_result_caption_song_with_links():
    """Song caption includes MusicBrainz link."""
    result = {
        "title": "Test Song",
        "music_type": "song",
        "album_title": "Test Album",
        "artist_name": "Test Artist",
        "external_ids": {"musicbrainz": "album-id-abc"},
    }

    caption = build_result_caption(result)

    assert ">MusicBrainz</a>" in caption


# ---------------------------------------------------------------------------
# show_result / show_list_detail parse mode
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_show_result_sends_html_caption(make_message):
    """Card view sends the HTML caption with parse_mode HTML."""
    message = make_message()
    result = {"id": "1", "title": "M*A*S*H", "overview": "O", "poster": None}

    await show_result(message, result, 0, 1)

    call = message.reply_text.call_args
    assert "<b>M*A*S*H</b>" in call.args[0]
    assert call.kwargs["parse_mode"] == "HTML"


@pytest.mark.asyncio
async def test_show_list_detail_sends_html_caption(make_message):
    """List detail view sends the HTML caption with parse_mode HTML."""
    message = make_message()
    result = {
        "id": "1",
        "title": "*NSYNC",
        "overview": "O",
        "poster": "https://example.com/p.jpg",
    }

    await show_list_detail(message, result)

    call = message.reply_photo.call_args
    assert "<b>*NSYNC</b>" in call.kwargs["caption"]
    assert call.kwargs["parse_mode"] == "HTML"


HOSTILE_TITLE = "M*A*S*H <b>&"
ESCAPED_TITLE = "<b>M*A*S*H &lt;b&gt;&amp;</b>"


@pytest.mark.asyncio
@pytest.mark.parametrize("show", ["card", "list_detail"])
@pytest.mark.parametrize("path", ["photo", "photo_failed", "text"])
async def test_every_caption_send_uses_html(make_message, show, path):
    """Every send of the built caption escapes the title and uses parse_mode HTML.

    Search, card navigation (nav_prev/nav_next) and list selection all send
    the caption through show_result or show_list_detail.
    """
    message = make_message()
    if path == "photo_failed":
        message.reply_photo = AsyncMock(side_effect=Exception("bad photo"))
    result = {
        "id": "1",
        "title": HOSTILE_TITLE,
        "overview": "O",
        "poster": None if path == "text" else "https://example.com/p.jpg",
    }

    if show == "card":
        await show_result(message, result, 0, 2)
    else:
        await show_list_detail(message, result)

    send = message.reply_text if path != "photo" else message.reply_photo
    call = send.call_args
    caption = call.kwargs.get("caption") or call.args[0]
    assert ESCAPED_TITLE in caption
    assert call.kwargs["parse_mode"] == "HTML"


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
