"""
Tests for src/api/bazarr.py -- BazarrClient.
"""

import pytest
from unittest.mock import AsyncMock, patch

from tests.fixtures.bazarr_data import (
    BAZARR_MOVIES,
    BAZARR_MOVIES_WANTED,
    BAZARR_EPISODES_WANTED,
)


BASE = "http://localhost:6767/api/"


# ---------------------------------------------------------------------------
# __init__ error paths
# ---------------------------------------------------------------------------


class TestBazarrInit:
    def test_init_missing_addr(self):
        """ValueError when addr is missing."""
        from src.config.settings import config
        original = config["bazarr"]["server"]["addr"]
        try:
            config["bazarr"]["server"]["addr"] = None
            from src.api.bazarr import BazarrClient
            with pytest.raises(ValueError, match="address or port not configured"):
                BazarrClient()
        finally:
            config["bazarr"]["server"]["addr"] = original

    def test_init_missing_apikey(self):
        """ValueError when apikey is missing."""
        from src.config.settings import config
        original = config["bazarr"]["auth"]["apikey"]
        try:
            config["bazarr"]["auth"]["apikey"] = None
            from src.api.bazarr import BazarrClient
            with pytest.raises(ValueError, match="API key not configured"):
                BazarrClient()
        finally:
            config["bazarr"]["auth"]["apikey"] = original

    def test_init_success(self, bazarr_client):
        """Client initializes successfully with valid config."""
        assert bazarr_client.base_url == "http://localhost:6767"
        assert bazarr_client.API_VERSION == ""


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


class TestBazarrSearch:
    @pytest.mark.asyncio
    async def test_search_success_with_matches(self, aio_mock, bazarr_client):
        """search() filters movies by title match."""
        aio_mock.get(f"{BASE}movies", payload=BAZARR_MOVIES, status=200)
        results = await bazarr_client.search("inception")
        assert len(results) == 1
        assert results[0]["title"] == "Inception"

    @pytest.mark.asyncio
    async def test_search_no_matches(self, aio_mock, bazarr_client):
        """search() returns empty list when no title matches."""
        aio_mock.get(f"{BASE}movies", payload=BAZARR_MOVIES, status=200)
        results = await bazarr_client.search("nonexistent")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_empty_api_response(self, aio_mock, bazarr_client):
        """search() returns empty list when API returns no data."""
        aio_mock.get(
            f"{BASE}movies",
            payload={"data": [], "total": 0},
            status=200,
        )
        results = await bazarr_client.search("anything")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_api_returns_none(self, aio_mock, bazarr_client):
        """search() returns empty list when API returns non-dict."""
        aio_mock.get(f"{BASE}movies", payload="", status=200)
        results = await bazarr_client.search("test")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_exception(self, bazarr_client):
        """search() returns empty list on exception."""
        with patch.object(
            bazarr_client, "_request", new_callable=AsyncMock,
            side_effect=RuntimeError("unexpected"),
        ):
            results = await bazarr_client.search("test")
        assert results == []


# ---------------------------------------------------------------------------
# get_movies
# ---------------------------------------------------------------------------


class TestBazarrGetMovies:
    @pytest.mark.asyncio
    async def test_get_movies_success(self, aio_mock, bazarr_client):
        """get_movies() returns data list from response."""
        aio_mock.get(f"{BASE}movies", payload=BAZARR_MOVIES, status=200)
        results = await bazarr_client.get_movies()
        assert len(results) == 2
        assert results[0]["title"] == "Inception"

    @pytest.mark.asyncio
    async def test_get_movies_empty(self, aio_mock, bazarr_client):
        """get_movies() returns empty list when no movies."""
        aio_mock.get(
            f"{BASE}movies",
            payload={"data": [], "total": 0},
            status=200,
        )
        results = await bazarr_client.get_movies()
        assert results == []

    @pytest.mark.asyncio
    async def test_get_movies_api_returns_none(self, aio_mock, bazarr_client):
        """get_movies() returns empty list when API returns non-dict."""
        aio_mock.get(f"{BASE}movies", payload="", status=200)
        results = await bazarr_client.get_movies()
        assert results == []

    @pytest.mark.asyncio
    async def test_get_movies_exception(self, bazarr_client):
        """get_movies() returns empty list on exception."""
        with patch.object(
            bazarr_client, "_request", new_callable=AsyncMock,
            side_effect=RuntimeError("fail"),
        ):
            results = await bazarr_client.get_movies()
        assert results == []


# ---------------------------------------------------------------------------
# get_wanted_movies
# ---------------------------------------------------------------------------


class TestBazarrGetWantedMovies:
    @pytest.mark.asyncio
    async def test_wanted_movies_success(self, aio_mock, bazarr_client):
        """get_wanted_movies() returns movies missing subtitles."""
        aio_mock.get(
            f"{BASE}movies/wanted",
            payload=BAZARR_MOVIES_WANTED,
            status=200,
        )
        results = await bazarr_client.get_wanted_movies()
        assert len(results) == 1
        assert results[0]["title"] == "Inception"

    @pytest.mark.asyncio
    async def test_wanted_movies_empty(self, aio_mock, bazarr_client):
        """get_wanted_movies() returns empty list when none wanted."""
        aio_mock.get(
            f"{BASE}movies/wanted",
            payload={"data": [], "total": 0},
            status=200,
        )
        results = await bazarr_client.get_wanted_movies()
        assert results == []

    @pytest.mark.asyncio
    async def test_wanted_movies_api_returns_none(self, aio_mock, bazarr_client):
        """get_wanted_movies() returns empty list when API returns non-dict."""
        aio_mock.get(f"{BASE}movies/wanted", payload="", status=200)
        results = await bazarr_client.get_wanted_movies()
        assert results == []

    @pytest.mark.asyncio
    async def test_wanted_movies_exception(self, bazarr_client):
        """get_wanted_movies() returns empty list on exception."""
        with patch.object(
            bazarr_client, "_request", new_callable=AsyncMock,
            side_effect=RuntimeError("fail"),
        ):
            results = await bazarr_client.get_wanted_movies()
        assert results == []


# ---------------------------------------------------------------------------
# get_wanted_episodes
# ---------------------------------------------------------------------------


class TestBazarrGetWantedEpisodes:
    @pytest.mark.asyncio
    async def test_wanted_episodes_success(self, aio_mock, bazarr_client):
        """get_wanted_episodes() returns episodes missing subtitles."""
        aio_mock.get(
            f"{BASE}episodes/wanted",
            payload=BAZARR_EPISODES_WANTED,
            status=200,
        )
        results = await bazarr_client.get_wanted_episodes()
        assert len(results) == 1
        assert results[0]["seriesTitle"] == "Breaking Bad"

    @pytest.mark.asyncio
    async def test_wanted_episodes_empty(self, aio_mock, bazarr_client):
        """get_wanted_episodes() returns empty list when none wanted."""
        aio_mock.get(
            f"{BASE}episodes/wanted",
            payload={"data": [], "total": 0},
            status=200,
        )
        results = await bazarr_client.get_wanted_episodes()
        assert results == []

    @pytest.mark.asyncio
    async def test_wanted_episodes_api_returns_none(self, aio_mock, bazarr_client):
        """get_wanted_episodes() returns empty list when API returns non-dict."""
        aio_mock.get(f"{BASE}episodes/wanted", payload="", status=200)
        results = await bazarr_client.get_wanted_episodes()
        assert results == []

    @pytest.mark.asyncio
    async def test_wanted_episodes_exception(self, bazarr_client):
        """get_wanted_episodes() returns empty list on exception."""
        with patch.object(
            bazarr_client, "_request", new_callable=AsyncMock,
            side_effect=RuntimeError("fail"),
        ):
            results = await bazarr_client.get_wanted_episodes()
        assert results == []


# ---------------------------------------------------------------------------
# search_movie_subtitles
# ---------------------------------------------------------------------------


class TestBazarrSearchMovieSubtitles:
    @pytest.mark.asyncio
    async def test_search_movie_subtitles_success(self, aio_mock, bazarr_client):
        """search_movie_subtitles() returns True on success."""
        aio_mock.patch(
            f"{BASE}movies/subtitles?radarrid=1&language=fr"
            f"&forced=false&hi=false",
            status=204,
        )
        result = await bazarr_client.search_movie_subtitles(1, "fr")
        assert result is True

    @pytest.mark.asyncio
    async def test_search_movie_subtitles_failure(self, aio_mock, bazarr_client):
        """search_movie_subtitles() returns False on API failure."""
        aio_mock.patch(
            f"{BASE}movies/subtitles?radarrid=1&language=fr"
            f"&forced=false&hi=false",
            status=404,
            payload={"message": "Movie not found"},
        )
        result = await bazarr_client.search_movie_subtitles(1, "fr")
        assert result is False

    @pytest.mark.asyncio
    async def test_search_movie_subtitles_exception(self, bazarr_client):
        """search_movie_subtitles() returns False on exception."""
        with patch.object(
            bazarr_client, "_make_request", new_callable=AsyncMock,
            side_effect=RuntimeError("fail"),
        ):
            result = await bazarr_client.search_movie_subtitles(1, "fr")
        assert result is False

    @pytest.mark.asyncio
    async def test_search_movie_subtitles_with_options(self, aio_mock, bazarr_client):
        """search_movie_subtitles() passes forced and hi params."""
        aio_mock.patch(
            f"{BASE}movies/subtitles?radarrid=1&language=fr"
            f"&forced=true&hi=true",
            status=204,
        )
        result = await bazarr_client.search_movie_subtitles(
            1, "fr", forced=True, hi=True
        )
        assert result is True


# ---------------------------------------------------------------------------
# search_episode_subtitles
# ---------------------------------------------------------------------------


class TestBazarrSearchEpisodeSubtitles:
    @pytest.mark.asyncio
    async def test_search_episode_subtitles_success(self, aio_mock, bazarr_client):
        """search_episode_subtitles() returns True on success."""
        aio_mock.patch(
            f"{BASE}episodes/subtitles?seriesid=10"
            f"&episodeid=100&language=es"
            f"&forced=false&hi=false",
            status=204,
        )
        result = await bazarr_client.search_episode_subtitles(10, 100, "es")
        assert result is True

    @pytest.mark.asyncio
    async def test_search_episode_subtitles_failure(self, aio_mock, bazarr_client):
        """search_episode_subtitles() returns False on API failure."""
        aio_mock.patch(
            f"{BASE}episodes/subtitles?seriesid=10"
            f"&episodeid=100&language=es"
            f"&forced=false&hi=false",
            status=404,
        )
        result = await bazarr_client.search_episode_subtitles(10, 100, "es")
        assert result is False

    @pytest.mark.asyncio
    async def test_search_episode_subtitles_exception(self, bazarr_client):
        """search_episode_subtitles() returns False on exception."""
        with patch.object(
            bazarr_client, "_make_request", new_callable=AsyncMock,
            side_effect=RuntimeError("fail"),
        ):
            result = await bazarr_client.search_episode_subtitles(10, 100, "es")
        assert result is False
