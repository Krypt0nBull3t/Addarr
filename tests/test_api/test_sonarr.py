"""
Tests for src/api/sonarr.py -- SonarrClient.
"""

import pytest
import aiohttp
from unittest.mock import patch
from aioresponses import CallbackResult

from tests.fixtures.sample_data import (
    SONARR_SEARCH_RESULTS,
    SONARR_SERIES_DETAIL,
)


BASE = "http://localhost:8989/api/v3"


# ---------------------------------------------------------------------------
# __init__ error paths
# ---------------------------------------------------------------------------


class TestSonarrInit:
    def test_init_missing_addr(self):
        """Lines 35-36: ValueError when addr is missing."""
        from src.config.settings import config
        original = config["sonarr"]["server"]["addr"]
        try:
            config["sonarr"]["server"]["addr"] = None
            from src.api.sonarr import SonarrClient
            with pytest.raises(ValueError, match="address or port not configured"):
                SonarrClient()
        finally:
            config["sonarr"]["server"]["addr"] = original

    def test_init_missing_apikey(self):
        """Lines 42-43: ValueError when apikey is missing."""
        from src.config.settings import config
        original = config["sonarr"]["auth"]["apikey"]
        try:
            config["sonarr"]["auth"]["apikey"] = None
            from src.api.sonarr import SonarrClient
            with pytest.raises(ValueError, match="API key not configured"):
                SonarrClient()
        finally:
            config["sonarr"]["auth"]["apikey"] = original


# ---------------------------------------------------------------------------
# _make_request
# ---------------------------------------------------------------------------


class TestSonarrMakeRequest:
    @pytest.mark.asyncio
    async def test_make_request_generic_exception(self, aio_mock, sonarr_client):
        """Lines 71-73: generic Exception in _make_request."""
        aio_mock.get(
            f"{BASE}/system/status",
            exception=RuntimeError("unexpected"),
        )
        result = await sonarr_client._make_request("system/status")
        assert result is None


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


class TestSonarrSearch:
    @pytest.mark.asyncio
    async def test_search_success(self, aio_mock, sonarr_client):
        aio_mock.get(
            f"{BASE}/series/lookup?term=test",
            payload=SONARR_SEARCH_RESULTS,
            status=200,
        )
        results = await sonarr_client.search("test")
        assert len(results) == 2
        assert results[0]["title"] == "Breaking Bad"
        assert results[1]["title"] == "Severance"

    @pytest.mark.asyncio
    async def test_search_no_results(self, aio_mock, sonarr_client):
        aio_mock.get(
            f"{BASE}/series/lookup?term=zzzzz",
            payload=[],
            status=200,
        )
        results = await sonarr_client.search("zzzzz")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_exception(self, sonarr_client):
        """Lines 88-90: Exception during search."""
        with patch.object(sonarr_client, "_make_request", side_effect=Exception("boom")):
            results = await sonarr_client.search("test")
        assert results == []


# ---------------------------------------------------------------------------
# get_root_folders
# ---------------------------------------------------------------------------


class TestSonarrRootFolders:
    @pytest.mark.asyncio
    async def test_get_root_folders_success(self, aio_mock, sonarr_client):
        """Lines 94-98: successful get_root_folders."""
        aio_mock.get(
            f"{BASE}/rootFolder",
            payload=[{"path": "/tv"}, {"path": "/tv2"}],
            status=200,
        )
        folders = await sonarr_client.get_root_folders()
        assert folders == ["/tv", "/tv2"]

    @pytest.mark.asyncio
    async def test_get_root_folders_empty(self, aio_mock, sonarr_client):
        """Lines 98: returns empty when API returns None."""
        aio_mock.get(
            f"{BASE}/rootFolder",
            status=500,
            body="error",
        )
        folders = await sonarr_client.get_root_folders()
        assert folders == []

    @pytest.mark.asyncio
    async def test_get_root_folders_exception(self, sonarr_client):
        """Lines 99-101: Exception in get_root_folders."""
        with patch.object(sonarr_client, "_make_request", side_effect=Exception("boom")):
            folders = await sonarr_client.get_root_folders()
        assert folders == []

    @pytest.mark.asyncio
    async def test_get_root_folders_excludes_by_basename_when_narrow(self, aio_mock):
        """narrowRootFolderNames makes excludedRootFolders match by basename."""
        from src.config.settings import config
        orig_paths = config._config["sonarr"]["paths"].copy()
        config._config["sonarr"]["paths"]["excludedRootFolders"] = ["tv2"]
        config._config["sonarr"]["paths"]["narrowRootFolderNames"] = True
        try:
            from src.api.sonarr import SonarrClient
            client = SonarrClient()
            aio_mock.get(
                f"{BASE}/rootFolder",
                payload=[{"path": "/data/tv"}, {"path": "/data/tv2"}],
                status=200,
            )
            folders = await client.get_root_folders()
            assert "/data/tv" in folders
            assert "/data/tv2" not in folders
        finally:
            config._config["sonarr"]["paths"] = orig_paths

    @pytest.mark.asyncio
    async def test_get_root_folders_excludes_by_full_path_when_not_narrow(self, aio_mock):
        """Without narrowRootFolderNames, excludedRootFolders matches full path."""
        from src.config.settings import config
        orig_paths = config._config["sonarr"]["paths"].copy()
        config._config["sonarr"]["paths"]["excludedRootFolders"] = ["/data/tv2"]
        config._config["sonarr"]["paths"]["narrowRootFolderNames"] = False
        try:
            from src.api.sonarr import SonarrClient
            client = SonarrClient()
            aio_mock.get(
                f"{BASE}/rootFolder",
                payload=[{"path": "/data/tv"}, {"path": "/data/tv2"}],
                status=200,
            )
            folders = await client.get_root_folders()
            assert "/data/tv" in folders
            assert "/data/tv2" not in folders
        finally:
            config._config["sonarr"]["paths"] = orig_paths


# ---------------------------------------------------------------------------
# get_quality_profiles
# ---------------------------------------------------------------------------


class TestSonarrQualityProfiles:
    @pytest.mark.asyncio
    async def test_get_quality_profiles_success(self, aio_mock, sonarr_client):
        """Lines 105-108: successful get_quality_profiles."""
        aio_mock.get(
            f"{BASE}/qualityProfile",
            payload=[
                {"id": 1, "name": "HD-1080p"},
                {"id": 2, "name": "Ultra-HD"},
            ],
            status=200,
        )
        profiles = await sonarr_client.get_quality_profiles()
        assert len(profiles) == 2
        assert profiles[0]["id"] == 1
        assert profiles[0]["name"] == "HD-1080p"

    @pytest.mark.asyncio
    async def test_get_quality_profiles_empty(self, aio_mock, sonarr_client):
        """Lines 109: returns empty when API returns None."""
        aio_mock.get(
            f"{BASE}/qualityProfile",
            status=500,
            body="error",
        )
        profiles = await sonarr_client.get_quality_profiles()
        assert profiles == []

    @pytest.mark.asyncio
    async def test_get_quality_profiles_exception(self, sonarr_client):
        """Lines 110-112: Exception in get_quality_profiles."""
        with patch.object(sonarr_client, "_make_request", side_effect=Exception("boom")):
            profiles = await sonarr_client.get_quality_profiles()
        assert profiles == []


# ---------------------------------------------------------------------------
# get_series
# ---------------------------------------------------------------------------


class TestSonarrGetSeries:
    @pytest.mark.asyncio
    async def test_get_series_success(self, aio_mock, sonarr_client):
        aio_mock.get(
            f"{BASE}/series/lookup/tvdb/81189",
            payload=SONARR_SERIES_DETAIL,
            status=200,
        )
        result = await sonarr_client.get_series("81189")
        assert result is not None
        assert result["title"] == "Breaking Bad"
        assert result["tvdbId"] == 81189

    @pytest.mark.asyncio
    async def test_get_series_fallback_search(self, aio_mock, sonarr_client):
        # Direct lookup fails
        aio_mock.get(
            f"{BASE}/series/lookup/tvdb/81189",
            status=404,
            body="Not found",
        )
        # Fallback search succeeds
        aio_mock.get(
            f"{BASE}/series/lookup?term=tvdb:81189",
            payload=[SONARR_SERIES_DETAIL],
            status=200,
        )
        result = await sonarr_client.get_series("81189")
        assert result is not None
        assert result["title"] == "Breaking Bad"

    @pytest.mark.asyncio
    async def test_get_series_not_found(self, aio_mock, sonarr_client):
        """Lines 222-223: both lookups return nothing."""
        aio_mock.get(
            f"{BASE}/series/lookup/tvdb/999999",
            status=404,
            body="Not found",
        )
        aio_mock.get(
            f"{BASE}/series/lookup?term=tvdb:999999",
            payload=[],
            status=200,
        )
        result = await sonarr_client.get_series("999999")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_series_exception(self, sonarr_client):
        """Lines 225-227: Exception in get_series."""
        with patch.object(sonarr_client, "_make_request", side_effect=Exception("boom")):
            result = await sonarr_client.get_series("81189")
        assert result is None


# ---------------------------------------------------------------------------
# get_seasons
# ---------------------------------------------------------------------------


class TestSonarrGetSeasons:
    @pytest.mark.asyncio
    async def test_get_seasons(self, aio_mock, sonarr_client):
        aio_mock.get(
            f"{BASE}/series/lookup?term=tvdb:81189",
            payload=SONARR_SEARCH_RESULTS[:1],  # First result has 3 seasons
            status=200,
        )
        seasons = await sonarr_client.get_seasons("81189")
        assert len(seasons) == 3
        assert seasons[0]["seasonNumber"] == 0
        assert seasons[1]["seasonNumber"] == 1
        assert seasons[2]["seasonNumber"] == 2

    @pytest.mark.asyncio
    async def test_get_seasons_empty(self, aio_mock, sonarr_client):
        aio_mock.get(
            f"{BASE}/series/lookup?term=tvdb:999999",
            payload=[],
            status=200,
        )
        seasons = await sonarr_client.get_seasons("999999")
        assert seasons == []

    @pytest.mark.asyncio
    async def test_get_seasons_exception(self, sonarr_client):
        """Lines 129-131: Exception in get_seasons."""
        with patch.object(sonarr_client, "_make_request", side_effect=Exception("boom")):
            seasons = await sonarr_client.get_seasons("81189")
        assert seasons == []


# ---------------------------------------------------------------------------
# add_series
# ---------------------------------------------------------------------------


class TestSonarrAddSeries:
    @pytest.mark.asyncio
    async def test_add_series_success(self, aio_mock, sonarr_client):
        # 1. Lookup by tvdb ID
        aio_mock.get(
            f"{BASE}/series/lookup?term=tvdb:81189",
            payload=SONARR_SEARCH_RESULTS[:1],
            status=200,
        )
        # 2. POST series
        aio_mock.post(
            f"{BASE}/series",
            payload={"id": 1, "title": "Breaking Bad"},
            status=200,
        )
        success, message = await sonarr_client.add_series(81189, "/tv", 1)
        assert success is True
        assert "Successfully added" in message
        assert "Breaking Bad" in message

    @pytest.mark.asyncio
    async def test_add_series_with_seasons(self, aio_mock, sonarr_client):
        """Line 157: add_series with seasons parameter."""
        aio_mock.get(
            f"{BASE}/series/lookup?term=tvdb:81189",
            payload=SONARR_SEARCH_RESULTS[:1],
            status=200,
        )
        aio_mock.post(
            f"{BASE}/series",
            payload={"id": 1, "title": "Breaking Bad"},
            status=200,
        )
        seasons = [{"seasonNumber": 1, "monitored": True}]
        success, message = await sonarr_client.add_series(81189, "/tv", 1, seasons=seasons)
        assert success is True
        assert "Successfully added" in message

    @pytest.mark.asyncio
    async def test_add_series_already_exists(self, aio_mock, sonarr_client):
        # 1. Lookup
        aio_mock.get(
            f"{BASE}/series/lookup?term=tvdb:81189",
            payload=SONARR_SEARCH_RESULTS[:1],
            status=200,
        )
        # 2. POST returns already-exists error
        aio_mock.post(
            f"{BASE}/series",
            payload=[{"errorMessage": "This series has already been added"}],
            status=400,
        )
        success, message = await sonarr_client.add_series(81189, "/tv", 1)
        assert success is False
        assert "already in your library" in message

    @pytest.mark.asyncio
    async def test_add_series_lookup_not_found(self, aio_mock, sonarr_client):
        """Lines 139-140: lookup returns empty list."""
        aio_mock.get(
            f"{BASE}/series/lookup?term=tvdb:999",
            payload=[],
            status=200,
        )
        success, message = await sonarr_client.add_series(999, "/tv", 1)
        assert success is False
        assert "not found" in message.lower()

    @pytest.mark.asyncio
    async def test_add_series_api_error_non_already(self, aio_mock, sonarr_client):
        """Lines 181-182: error array with non-'already' message."""
        aio_mock.get(
            f"{BASE}/series/lookup?term=tvdb:81189",
            payload=SONARR_SEARCH_RESULTS[:1],
            status=200,
        )
        aio_mock.post(
            f"{BASE}/series",
            payload=[{"errorMessage": "Some other error"}],
            status=400,
        )
        success, message = await sonarr_client.add_series(81189, "/tv", 1)
        assert success is False
        assert message == "Some other error"

    @pytest.mark.asyncio
    async def test_add_series_json_decode_error_success(self, aio_mock, sonarr_client):
        """Lines 184-190: JSONDecodeError then status 201 fallback."""
        aio_mock.get(
            f"{BASE}/series/lookup?term=tvdb:81189",
            payload=SONARR_SEARCH_RESULTS[:1],
            status=200,
        )
        aio_mock.post(
            f"{BASE}/series",
            body="not json",
            status=201,
        )
        success, message = await sonarr_client.add_series(81189, "/tv", 1)
        assert success is True
        assert "Successfully added" in message

    @pytest.mark.asyncio
    async def test_add_series_json_decode_error_failure(self, aio_mock, sonarr_client):
        """Lines 191-193: JSONDecodeError then non-success status."""
        aio_mock.get(
            f"{BASE}/series/lookup?term=tvdb:81189",
            payload=SONARR_SEARCH_RESULTS[:1],
            status=200,
        )
        aio_mock.post(
            f"{BASE}/series",
            body="not json",
            status=500,
        )
        success, message = await sonarr_client.add_series(81189, "/tv", 1)
        assert success is False
        assert "Failed to add" in message

    @pytest.mark.asyncio
    async def test_add_series_client_error(self, aio_mock, sonarr_client):
        """Lines 195-197: ClientError during POST."""
        aio_mock.get(
            f"{BASE}/series/lookup?term=tvdb:81189",
            payload=SONARR_SEARCH_RESULTS[:1],
            status=200,
        )
        aio_mock.post(
            f"{BASE}/series",
            exception=aiohttp.ClientError("connection lost"),
        )
        success, message = await sonarr_client.add_series(81189, "/tv", 1)
        assert success is False
        assert "Connection error" in message

    @pytest.mark.asyncio
    async def test_add_series_inner_generic_exception(self, aio_mock, sonarr_client):
        """Lines 198-200: generic Exception during POST."""
        aio_mock.get(
            f"{BASE}/series/lookup?term=tvdb:81189",
            payload=SONARR_SEARCH_RESULTS[:1],
            status=200,
        )
        aio_mock.post(
            f"{BASE}/series",
            exception=RuntimeError("unexpected"),
        )
        success, message = await sonarr_client.add_series(81189, "/tv", 1)
        assert success is False

    @pytest.mark.asyncio
    async def test_add_series_outer_exception(self, sonarr_client):
        """Lines 202-204: outer Exception in add_series."""
        with patch.object(sonarr_client, "_make_request", side_effect=Exception("outer boom")):
            success, message = await sonarr_client.add_series(81189, "/tv", 1)
        assert success is False
        assert "outer boom" in message

    @pytest.mark.asyncio
    async def test_add_series_includes_season_folder_from_config(self, aio_mock):
        """add_series POST body should include seasonFolder from config."""
        from src.config.settings import config
        config._config["sonarr"]["features"]["seasonFolder"] = True
        try:
            from src.api.sonarr import SonarrClient
            client = SonarrClient()

            aio_mock.get(
                f"{BASE}/series/lookup?term=tvdb:81189",
                payload=SONARR_SEARCH_RESULTS[:1],
                status=200,
            )

            posted_data = {}

            def capture(url, **kwargs):
                posted_data.update(kwargs.get("json", {}))
                return CallbackResult(
                    payload={"id": 1, "title": "Breaking Bad"}, status=200
                )

            aio_mock.post(f"{BASE}/series", callback=capture)

            success, _ = await client.add_series(81189, "/tv", 1)
            assert success is True
            assert "seasonFolder" in posted_data, "POST body must include seasonFolder"
            assert posted_data["seasonFolder"] is True
        finally:
            config._config["sonarr"]["features"]["seasonFolder"] = True


# ---------------------------------------------------------------------------
# check_status
# ---------------------------------------------------------------------------


class TestSonarrCheckStatus:
    @pytest.mark.asyncio
    async def test_check_status_online(self, aio_mock, sonarr_client):
        aio_mock.get(
            f"{BASE}/system/status",
            payload={"version": "4.0.0", "appName": "Sonarr"},
            status=200,
        )
        result = await sonarr_client.check_status()
        assert result is True

    @pytest.mark.asyncio
    async def test_check_status_offline(self, aio_mock, sonarr_client):
        aio_mock.get(
            f"{BASE}/system/status",
            exception=aiohttp.ClientError("connection refused"),
        )
        result = await sonarr_client.check_status()
        assert result is False

    @pytest.mark.asyncio
    async def test_check_status_exception(self, sonarr_client):
        """Lines 234-236: Exception in check_status."""
        with patch.object(sonarr_client, "_make_request", side_effect=Exception("boom")):
            result = await sonarr_client.check_status()
        assert result is False
