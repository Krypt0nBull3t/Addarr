"""
Tests for src/api/radarr.py -- RadarrClient.
"""

import re
import json
import pytest
import aiohttp

from tests.fixtures.sample_data import (
    RADARR_SEARCH_RESULTS,
    RADARR_MOVIE_DETAIL,
    RADARR_QUALITY_PROFILES,
    RADARR_SYSTEM_STATUS,
)


BASE = "http://localhost:7878/api/v3"


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


class TestRadarrSearch:
    @pytest.mark.asyncio
    async def test_search_success(self, aio_mock, radarr_client):
        aio_mock.get(
            f"{BASE}/movie/lookup?term=test",
            payload=RADARR_SEARCH_RESULTS,
            status=200,
        )
        results = await radarr_client.search("test")
        assert len(results) == 2
        assert results[0]["title"] == "Fight Club"
        assert results[1]["title"] == "Pulp Fiction"

    @pytest.mark.asyncio
    async def test_search_no_results(self, aio_mock, radarr_client):
        aio_mock.get(
            f"{BASE}/movie/lookup?term=zzzzz",
            payload=[],
            status=200,
        )
        results = await radarr_client.search("zzzzz")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_connection_error(self, aio_mock, radarr_client):
        aio_mock.get(
            f"{BASE}/movie/lookup?term=test",
            exception=aiohttp.ClientError("refused"),
        )
        results = await radarr_client.search("test")
        assert results == []


# ---------------------------------------------------------------------------
# get_movie
# ---------------------------------------------------------------------------


class TestRadarrGetMovie:
    @pytest.mark.asyncio
    async def test_get_movie_success(self, aio_mock, radarr_client):
        aio_mock.get(
            f"{BASE}/movie/lookup/tmdb/550",
            payload=RADARR_MOVIE_DETAIL,
            status=200,
        )
        result = await radarr_client.get_movie("550")
        assert result is not None
        assert result["title"] == "Fight Club"
        assert result["tmdbId"] == 550

    @pytest.mark.asyncio
    async def test_get_movie_fallback_search(self, aio_mock, radarr_client):
        # Direct lookup returns 404 -> None
        aio_mock.get(
            f"{BASE}/movie/lookup/tmdb/550",
            status=404,
            body="Not found",
        )
        # Fallback search returns result in a list
        aio_mock.get(
            f"{BASE}/movie/lookup?term=tmdb:550",
            payload=[RADARR_MOVIE_DETAIL],
            status=200,
        )
        result = await radarr_client.get_movie("550")
        assert result is not None
        assert result["title"] == "Fight Club"

    @pytest.mark.asyncio
    async def test_get_movie_not_found(self, aio_mock, radarr_client):
        aio_mock.get(
            f"{BASE}/movie/lookup/tmdb/999999",
            status=404,
            body="Not found",
        )
        aio_mock.get(
            f"{BASE}/movie/lookup?term=tmdb:999999",
            payload=[],
            status=200,
        )
        result = await radarr_client.get_movie("999999")
        assert result is None


# ---------------------------------------------------------------------------
# get_root_folders
# ---------------------------------------------------------------------------


class TestRadarrRootFolders:
    @pytest.mark.asyncio
    async def test_get_root_folders(self, aio_mock, radarr_client):
        aio_mock.get(
            f"{BASE}/rootFolder",
            payload=[{"path": "/movies", "freeSpace": 1000}],
            status=200,
        )
        folders = await radarr_client.get_root_folders()
        assert folders == ["/movies"]

    @pytest.mark.asyncio
    async def test_get_root_folders_empty(self, aio_mock, radarr_client):
        aio_mock.get(
            f"{BASE}/rootFolder",
            status=500,
            body="error",
        )
        folders = await radarr_client.get_root_folders()
        assert folders == []


# ---------------------------------------------------------------------------
# get_quality_profiles
# ---------------------------------------------------------------------------


class TestRadarrQualityProfiles:
    @pytest.mark.asyncio
    async def test_get_quality_profiles(self, aio_mock, radarr_client):
        aio_mock.get(
            f"{BASE}/qualityProfile",
            payload=RADARR_QUALITY_PROFILES,
            status=200,
        )
        profiles = await radarr_client.get_quality_profiles()
        assert len(profiles) == 2
        assert profiles[0]["id"] == 1
        assert profiles[0]["name"] == "HD-1080p"
        assert profiles[1]["id"] == 2
        assert profiles[1]["name"] == "Ultra-HD"


# ---------------------------------------------------------------------------
# add_movie
# ---------------------------------------------------------------------------


class TestRadarrAddMovie:
    @pytest.mark.asyncio
    async def test_add_movie_success(self, aio_mock, radarr_client):
        # 1. Lookup by tmdb ID
        aio_mock.get(
            f"{BASE}/movie/lookup?term=tmdb:550",
            payload=[RADARR_MOVIE_DETAIL],
            status=200,
        )
        # 2. Quality profiles check
        aio_mock.get(
            f"{BASE}/qualityProfile",
            payload=RADARR_QUALITY_PROFILES,
            status=200,
        )
        # 3. POST movie
        aio_mock.post(
            f"{BASE}/movie",
            payload={"id": 1, "title": "Fight Club"},
            status=200,
        )
        success, message = await radarr_client.add_movie(550, "/movies", 1)
        assert success is True
        assert "Successfully added" in message
        assert "Fight Club" in message

    @pytest.mark.asyncio
    async def test_add_movie_already_exists(self, aio_mock, radarr_client):
        # 1. Lookup
        aio_mock.get(
            f"{BASE}/movie/lookup?term=tmdb:550",
            payload=[RADARR_MOVIE_DETAIL],
            status=200,
        )
        # 2. Quality profiles
        aio_mock.get(
            f"{BASE}/qualityProfile",
            payload=RADARR_QUALITY_PROFILES,
            status=200,
        )
        # 3. POST returns already-exists error
        aio_mock.post(
            f"{BASE}/movie",
            payload=[{"errorMessage": "This movie has already been added"}],
            status=400,
        )
        success, message = await radarr_client.add_movie(550, "/movies", 1)
        assert success is False
        assert "already in your library" in message


# ---------------------------------------------------------------------------
# check_status
# ---------------------------------------------------------------------------


class TestRadarrCheckStatus:
    @pytest.mark.asyncio
    async def test_check_status_online(self, aio_mock, radarr_client):
        aio_mock.get(
            f"{BASE}/system/status",
            payload=RADARR_SYSTEM_STATUS,
            status=200,
        )
        result = await radarr_client.check_status()
        assert result is True

    @pytest.mark.asyncio
    async def test_check_status_offline(self, aio_mock, radarr_client):
        aio_mock.get(
            f"{BASE}/system/status",
            exception=aiohttp.ClientError("connection refused"),
        )
        result = await radarr_client.check_status()
        assert result is False
