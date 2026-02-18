"""
Tests for src/api/radarr.py -- RadarrClient.
"""

import pytest
import aiohttp
from unittest.mock import patch

from tests.fixtures.sample_data import (
    RADARR_SEARCH_RESULTS,
    RADARR_MOVIE_DETAIL,
    RADARR_QUALITY_PROFILES,
    RADARR_SYSTEM_STATUS,
    RADARR_LIBRARY_MOVIES,
    RADARR_LIBRARY_MOVIE_DETAIL,
)


BASE = "http://localhost:7878/api/v3"


# ---------------------------------------------------------------------------
# __init__ error paths
# ---------------------------------------------------------------------------


class TestRadarrInit:
    def test_init_missing_addr(self):
        """Lines 35-36: ValueError when addr is missing."""
        from src.config.settings import config
        original = config["radarr"]["server"]["addr"]
        try:
            config["radarr"]["server"]["addr"] = None
            from src.api.radarr import RadarrClient
            with pytest.raises(ValueError, match="address or port not configured"):
                RadarrClient()
        finally:
            config["radarr"]["server"]["addr"] = original

    def test_init_missing_apikey(self):
        """Lines 42-43: ValueError when apikey is missing."""
        from src.config.settings import config
        original = config["radarr"]["auth"]["apikey"]
        try:
            config["radarr"]["auth"]["apikey"] = None
            from src.api.radarr import RadarrClient
            with pytest.raises(ValueError, match="API key not configured"):
                RadarrClient()
        finally:
            config["radarr"]["auth"]["apikey"] = original


# ---------------------------------------------------------------------------
# _make_request
# ---------------------------------------------------------------------------


class TestRadarrMakeRequest:
    @pytest.mark.asyncio
    async def test_make_request_generic_exception(self, aio_mock, radarr_client):
        """Lines 71-73: generic Exception in _make_request."""
        aio_mock.get(
            f"{BASE}/system/status",
            exception=RuntimeError("unexpected"),
        )
        result = await radarr_client._make_request("system/status")
        assert result is None


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

    @pytest.mark.asyncio
    async def test_search_exception(self, radarr_client):
        """Lines 88-90: Exception during search."""
        with patch.object(radarr_client, "_make_request", side_effect=Exception("boom")):
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

    @pytest.mark.asyncio
    async def test_get_movie_exception(self, radarr_client):
        """Lines 111-113: Exception in get_movie."""
        with patch.object(radarr_client, "_make_request", side_effect=Exception("boom")):
            result = await radarr_client.get_movie("550")
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

    @pytest.mark.asyncio
    async def test_get_root_folders_exception(self, radarr_client):
        """Lines 122-124: Exception in get_root_folders."""
        with patch.object(radarr_client, "_make_request", side_effect=Exception("boom")):
            folders = await radarr_client.get_root_folders()
        assert folders == []

    @pytest.mark.asyncio
    async def test_get_root_folders_excludes_by_basename_when_narrow(self, aio_mock):
        """narrowRootFolderNames makes excludedRootFolders match by basename."""
        from src.config.settings import config
        orig_paths = config._config["radarr"]["paths"].copy()
        config._config["radarr"]["paths"]["excludedRootFolders"] = ["movies2"]
        config._config["radarr"]["paths"]["narrowRootFolderNames"] = True
        try:
            from src.api.radarr import RadarrClient
            client = RadarrClient()
            aio_mock.get(
                f"{BASE}/rootFolder",
                payload=[
                    {"path": "/data/movies", "freeSpace": 1000},
                    {"path": "/data/movies2", "freeSpace": 500},
                ],
                status=200,
            )
            folders = await client.get_root_folders()
            assert "/data/movies" in folders
            assert "/data/movies2" not in folders
        finally:
            config._config["radarr"]["paths"] = orig_paths

    @pytest.mark.asyncio
    async def test_get_root_folders_excludes_by_full_path_when_not_narrow(self, aio_mock):
        """Without narrowRootFolderNames, excludedRootFolders matches full path."""
        from src.config.settings import config
        orig_paths = config._config["radarr"]["paths"].copy()
        config._config["radarr"]["paths"]["excludedRootFolders"] = ["/data/movies2"]
        config._config["radarr"]["paths"]["narrowRootFolderNames"] = False
        try:
            from src.api.radarr import RadarrClient
            client = RadarrClient()
            aio_mock.get(
                f"{BASE}/rootFolder",
                payload=[
                    {"path": "/data/movies", "freeSpace": 1000},
                    {"path": "/data/movies2", "freeSpace": 500},
                ],
                status=200,
            )
            folders = await client.get_root_folders()
            assert "/data/movies" in folders
            assert "/data/movies2" not in folders
        finally:
            config._config["radarr"]["paths"] = orig_paths

    @pytest.mark.asyncio
    async def test_get_root_folders_narrow_handles_trailing_slash(self, aio_mock):
        """narrowRootFolderNames matches basename even with trailing slashes."""
        from src.config.settings import config
        orig_paths = config._config["radarr"]["paths"].copy()
        config._config["radarr"]["paths"]["excludedRootFolders"] = ["movies2"]
        config._config["radarr"]["paths"]["narrowRootFolderNames"] = True
        try:
            from src.api.radarr import RadarrClient
            client = RadarrClient()
            aio_mock.get(
                f"{BASE}/rootFolder",
                payload=[
                    {"path": "/data/movies/", "freeSpace": 1000},
                    {"path": "/data/movies2/", "freeSpace": 500},
                ],
                status=200,
            )
            folders = await client.get_root_folders()
            assert "/data/movies/" in folders
            assert "/data/movies2/" not in folders
        finally:
            config._config["radarr"]["paths"] = orig_paths

    @pytest.mark.asyncio
    async def test_get_root_folders_empty_exclusion_returns_all(self, aio_mock):
        """Empty excludedRootFolders returns all folders unfiltered."""
        from src.config.settings import config
        orig_paths = config._config["radarr"]["paths"].copy()
        config._config["radarr"]["paths"]["excludedRootFolders"] = []
        config._config["radarr"]["paths"]["narrowRootFolderNames"] = True
        try:
            from src.api.radarr import RadarrClient
            client = RadarrClient()
            aio_mock.get(
                f"{BASE}/rootFolder",
                payload=[
                    {"path": "/data/movies", "freeSpace": 1000},
                    {"path": "/data/movies2", "freeSpace": 500},
                ],
                status=200,
            )
            folders = await client.get_root_folders()
            assert len(folders) == 2
        finally:
            config._config["radarr"]["paths"] = orig_paths


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

    @pytest.mark.asyncio
    async def test_get_quality_profiles_empty(self, aio_mock, radarr_client):
        """Lines 133-134: empty quality profiles."""
        aio_mock.get(
            f"{BASE}/qualityProfile",
            status=500,
            body="error",
        )
        profiles = await radarr_client.get_quality_profiles()
        assert profiles == []

    @pytest.mark.asyncio
    async def test_get_quality_profiles_exception(self, radarr_client):
        """Lines 148-150: Exception in get_quality_profiles."""
        with patch.object(radarr_client, "_make_request", side_effect=Exception("boom")):
            profiles = await radarr_client.get_quality_profiles()
        assert profiles == []


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

    @pytest.mark.asyncio
    async def test_add_movie_lookup_not_found(self, aio_mock, radarr_client):
        """Lines 158-159: lookup returns empty list."""
        aio_mock.get(
            f"{BASE}/movie/lookup?term=tmdb:999",
            payload=[],
            status=200,
        )
        success, message = await radarr_client.add_movie(999, "/movies", 1)
        assert success is False
        assert "not found" in message.lower()

    @pytest.mark.asyncio
    async def test_add_movie_invalid_quality_profile(self, aio_mock, radarr_client):
        """Lines 166-167: invalid quality profile ID."""
        aio_mock.get(
            f"{BASE}/movie/lookup?term=tmdb:550",
            payload=[RADARR_MOVIE_DETAIL],
            status=200,
        )
        aio_mock.get(
            f"{BASE}/qualityProfile",
            payload=RADARR_QUALITY_PROFILES,
            status=200,
        )
        success, message = await radarr_client.add_movie(550, "/movies", 999)
        assert success is False
        assert "Invalid quality profile" in message

    @pytest.mark.asyncio
    async def test_add_movie_api_error_non_already(self, aio_mock, radarr_client):
        """Lines 202-203: error array with non-'already' message."""
        aio_mock.get(
            f"{BASE}/movie/lookup?term=tmdb:550",
            payload=[RADARR_MOVIE_DETAIL],
            status=200,
        )
        aio_mock.get(
            f"{BASE}/qualityProfile",
            payload=RADARR_QUALITY_PROFILES,
            status=200,
        )
        aio_mock.post(
            f"{BASE}/movie",
            payload=[{"errorMessage": "Some other API error"}],
            status=400,
        )
        success, message = await radarr_client.add_movie(550, "/movies", 1)
        assert success is False
        assert message == "Some other API error"

    @pytest.mark.asyncio
    async def test_add_movie_json_decode_error_success(self, aio_mock, radarr_client):
        """Lines 205-211: JSONDecodeError then status 201 fallback."""
        aio_mock.get(
            f"{BASE}/movie/lookup?term=tmdb:550",
            payload=[RADARR_MOVIE_DETAIL],
            status=200,
        )
        aio_mock.get(
            f"{BASE}/qualityProfile",
            payload=RADARR_QUALITY_PROFILES,
            status=200,
        )
        aio_mock.post(
            f"{BASE}/movie",
            body="not json",
            status=201,
        )
        success, message = await radarr_client.add_movie(550, "/movies", 1)
        assert success is True
        assert "Successfully added" in message

    @pytest.mark.asyncio
    async def test_add_movie_json_decode_error_failure(self, aio_mock, radarr_client):
        """Lines 212-214: JSONDecodeError then non-success status."""
        aio_mock.get(
            f"{BASE}/movie/lookup?term=tmdb:550",
            payload=[RADARR_MOVIE_DETAIL],
            status=200,
        )
        aio_mock.get(
            f"{BASE}/qualityProfile",
            payload=RADARR_QUALITY_PROFILES,
            status=200,
        )
        aio_mock.post(
            f"{BASE}/movie",
            body="not json",
            status=500,
        )
        success, message = await radarr_client.add_movie(550, "/movies", 1)
        assert success is False
        assert "Failed to add" in message

    @pytest.mark.asyncio
    async def test_add_movie_client_error(self, aio_mock, radarr_client):
        """Lines 216-218: ClientError during POST."""
        aio_mock.get(
            f"{BASE}/movie/lookup?term=tmdb:550",
            payload=[RADARR_MOVIE_DETAIL],
            status=200,
        )
        aio_mock.get(
            f"{BASE}/qualityProfile",
            payload=RADARR_QUALITY_PROFILES,
            status=200,
        )
        aio_mock.post(
            f"{BASE}/movie",
            exception=aiohttp.ClientError("connection lost"),
        )
        success, message = await radarr_client.add_movie(550, "/movies", 1)
        assert success is False
        assert "Connection error" in message

    @pytest.mark.asyncio
    async def test_add_movie_inner_generic_exception(self, aio_mock, radarr_client):
        """Lines 219-221: generic Exception during POST."""
        aio_mock.get(
            f"{BASE}/movie/lookup?term=tmdb:550",
            payload=[RADARR_MOVIE_DETAIL],
            status=200,
        )
        aio_mock.get(
            f"{BASE}/qualityProfile",
            payload=RADARR_QUALITY_PROFILES,
            status=200,
        )
        aio_mock.post(
            f"{BASE}/movie",
            exception=RuntimeError("unexpected"),
        )
        success, message = await radarr_client.add_movie(550, "/movies", 1)
        assert success is False

    @pytest.mark.asyncio
    async def test_add_movie_outer_exception(self, radarr_client):
        """Lines 223-225: outer Exception in add_movie."""
        with patch.object(radarr_client, "_make_request", side_effect=Exception("outer boom")):
            success, message = await radarr_client.add_movie(550, "/movies", 1)
        assert success is False
        assert "outer boom" in message


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

    @pytest.mark.asyncio
    async def test_check_status_exception(self, radarr_client):
        """Lines 232-234: Exception in check_status."""
        with patch.object(radarr_client, "_make_request", side_effect=Exception("boom")):
            result = await radarr_client.check_status()
        assert result is False


# ---------------------------------------------------------------------------
# get_movies
# ---------------------------------------------------------------------------


class TestGetMovies:
    @pytest.mark.asyncio
    async def test_get_movies_success(self, aio_mock, radarr_client):
        aio_mock.get(
            f"{BASE}/movie",
            payload=RADARR_LIBRARY_MOVIES,
            status=200,
        )
        results = await radarr_client.get_movies()
        assert len(results) == 2
        assert results[0]["title"] == "Fight Club"
        assert results[1]["title"] == "Pulp Fiction"

    @pytest.mark.asyncio
    async def test_get_movies_empty(self, aio_mock, radarr_client):
        aio_mock.get(
            f"{BASE}/movie",
            payload=[],
            status=200,
        )
        results = await radarr_client.get_movies()
        assert results == []

    @pytest.mark.asyncio
    async def test_get_movies_connection_error(self, aio_mock, radarr_client):
        aio_mock.get(
            f"{BASE}/movie",
            exception=aiohttp.ClientError("refused"),
        )
        results = await radarr_client.get_movies()
        assert results == []

    @pytest.mark.asyncio
    async def test_get_movies_exception(self, radarr_client):
        with patch.object(radarr_client, "_make_request", side_effect=Exception("boom")):
            results = await radarr_client.get_movies()
        assert results == []


# ---------------------------------------------------------------------------
# get_movie_by_id
# ---------------------------------------------------------------------------


class TestGetMovieById:
    @pytest.mark.asyncio
    async def test_get_movie_by_id_success(self, aio_mock, radarr_client):
        aio_mock.get(
            f"{BASE}/movie/1",
            payload=RADARR_LIBRARY_MOVIE_DETAIL,
            status=200,
        )
        result = await radarr_client.get_movie_by_id(1)
        assert result is not None
        assert result["title"] == "Fight Club"
        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_get_movie_by_id_not_found(self, aio_mock, radarr_client):
        aio_mock.get(
            f"{BASE}/movie/999",
            status=404,
            body="Not found",
        )
        result = await radarr_client.get_movie_by_id(999)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_movie_by_id_exception(self, radarr_client):
        with patch.object(radarr_client, "_make_request", side_effect=Exception("boom")):
            result = await radarr_client.get_movie_by_id(1)
        assert result is None


# ---------------------------------------------------------------------------
# delete_movie
# ---------------------------------------------------------------------------


class TestDeleteMovie:
    @pytest.mark.asyncio
    async def test_delete_movie_success(self, aio_mock, radarr_client):
        aio_mock.delete(
            "http://localhost:7878/api/v3/movie/1?deleteFiles=true",
            status=200,
            body="",
        )
        result = await radarr_client.delete_movie(1)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_movie_not_found(self, aio_mock, radarr_client):
        aio_mock.delete(
            "http://localhost:7878/api/v3/movie/999?deleteFiles=true",
            status=404,
            body="Not found",
        )
        result = await radarr_client.delete_movie(999)
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_movie_connection_error(self, aio_mock, radarr_client):
        aio_mock.delete(
            "http://localhost:7878/api/v3/movie/1?deleteFiles=true",
            exception=aiohttp.ClientError("refused"),
        )
        result = await radarr_client.delete_movie(1)
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_movie_exception(self, aio_mock, radarr_client):
        aio_mock.delete(
            "http://localhost:7878/api/v3/movie/1?deleteFiles=true",
            exception=RuntimeError("unexpected"),
        )
        result = await radarr_client.delete_movie(1)
        assert result is False
