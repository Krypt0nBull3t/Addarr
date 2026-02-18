"""
Tests for src/api/lidarr.py -- LidarrClient.

NOTE: Lidarr uses /api/v1/ (not v3).
"""

import pytest
import aiohttp
from unittest.mock import patch
from aioresponses import CallbackResult

from tests.fixtures.sample_data import (
    LIDARR_SEARCH_RESULTS,
    LIDARR_METADATA_PROFILES,
    LIDARR_LIBRARY_ARTISTS,
    LIDARR_LIBRARY_ARTIST_DETAIL,
)


BASE = "http://localhost:8686/api/v1"

ARTIST_ID = "f59c5520-5f46-4d2c-b2c4-822eabf53419"


# ---------------------------------------------------------------------------
# __init__ error paths
# ---------------------------------------------------------------------------


class TestLidarrInit:
    def test_init_missing_addr(self):
        """Lines 35-36: ValueError when addr is missing."""
        from src.config.settings import config
        original = config["lidarr"]["server"]["addr"]
        try:
            config["lidarr"]["server"]["addr"] = None
            from src.api.lidarr import LidarrClient
            with pytest.raises(ValueError, match="address or port not configured"):
                LidarrClient()
        finally:
            config["lidarr"]["server"]["addr"] = original

    def test_init_missing_apikey(self):
        """Lines 42-43: ValueError when apikey is missing."""
        from src.config.settings import config
        original = config["lidarr"]["auth"]["apikey"]
        try:
            config["lidarr"]["auth"]["apikey"] = None
            from src.api.lidarr import LidarrClient
            with pytest.raises(ValueError, match="API key not configured"):
                LidarrClient()
        finally:
            config["lidarr"]["auth"]["apikey"] = original


# ---------------------------------------------------------------------------
# _make_request
# ---------------------------------------------------------------------------


class TestLidarrMakeRequest:
    @pytest.mark.asyncio
    async def test_make_request_non_200(self, aio_mock, lidarr_client):
        """Lines 64-66: non-200 status in _make_request."""
        aio_mock.get(
            f"{BASE}/system/status",
            status=500,
            body="Internal Server Error",
        )
        result = await lidarr_client._make_request("system/status")
        assert result is None

    @pytest.mark.asyncio
    async def test_make_request_generic_exception(self, aio_mock, lidarr_client):
        """Lines 71-73: generic Exception in _make_request."""
        aio_mock.get(
            f"{BASE}/system/status",
            exception=RuntimeError("unexpected"),
        )
        result = await lidarr_client._make_request("system/status")
        assert result is None


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


class TestLidarrSearch:
    @pytest.mark.asyncio
    async def test_search_success(self, aio_mock, lidarr_client):
        aio_mock.get(
            f"{BASE}/artist/lookup?term=test",
            payload=LIDARR_SEARCH_RESULTS,
            status=200,
        )
        results = await lidarr_client.search("test")
        assert len(results) == 2
        assert results[0]["artistName"] == "Linkin Park"
        assert results[1]["artistName"] == "Radiohead"

    @pytest.mark.asyncio
    async def test_search_no_results(self, aio_mock, lidarr_client):
        aio_mock.get(
            f"{BASE}/artist/lookup?term=zzzzz",
            payload=[],
            status=200,
        )
        results = await lidarr_client.search("zzzzz")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_exception(self, lidarr_client):
        """Lines 88-90: Exception during search."""
        with patch.object(lidarr_client, "_make_request", side_effect=Exception("boom")):
            results = await lidarr_client.search("test")
        assert results == []


# ---------------------------------------------------------------------------
# get_artist
# ---------------------------------------------------------------------------


class TestLidarrGetArtist:
    @pytest.mark.asyncio
    async def test_get_artist_success(self, aio_mock, lidarr_client):
        aio_mock.get(
            f"{BASE}/artist/lookup?term=lidarr:{ARTIST_ID}",
            payload=LIDARR_SEARCH_RESULTS[:1],
            status=200,
        )
        result = await lidarr_client.get_artist(ARTIST_ID)
        assert result is not None
        assert result["artistName"] == "Linkin Park"

    @pytest.mark.asyncio
    async def test_get_artist_fallback(self, aio_mock, lidarr_client):
        # Direct lidarr: lookup returns empty
        aio_mock.get(
            f"{BASE}/artist/lookup?term=lidarr:{ARTIST_ID}",
            payload=[],
            status=200,
        )
        # Fallback search returns results and we match by foreignArtistId
        aio_mock.get(
            f"{BASE}/artist/lookup?term={ARTIST_ID}",
            payload=LIDARR_SEARCH_RESULTS,
            status=200,
        )
        result = await lidarr_client.get_artist(ARTIST_ID)
        assert result is not None
        assert result["foreignArtistId"] == ARTIST_ID
        assert result["artistName"] == "Linkin Park"

    @pytest.mark.asyncio
    async def test_get_artist_fallback_no_exact_match_uses_first(self, aio_mock, lidarr_client):
        """Lines 113-115: fallback returns results but no exact ID match, uses first."""
        aio_mock.get(
            f"{BASE}/artist/lookup?term=lidarr:unknown-id",
            payload=[],
            status=200,
        )
        aio_mock.get(
            f"{BASE}/artist/lookup?term=unknown-id",
            payload=LIDARR_SEARCH_RESULTS,
            status=200,
        )
        result = await lidarr_client.get_artist("unknown-id")
        assert result is not None
        # No exact match so uses first result
        assert result["artistName"] == "Linkin Park"

    @pytest.mark.asyncio
    async def test_get_artist_not_found(self, aio_mock, lidarr_client):
        aio_mock.get(
            f"{BASE}/artist/lookup?term=lidarr:nonexistent",
            payload=[],
            status=200,
        )
        aio_mock.get(
            f"{BASE}/artist/lookup?term=nonexistent",
            payload=[],
            status=200,
        )
        result = await lidarr_client.get_artist("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_artist_exception(self, lidarr_client):
        """Lines 120-122: Exception in get_artist."""
        with patch.object(lidarr_client, "_make_request", side_effect=Exception("boom")):
            result = await lidarr_client.get_artist(ARTIST_ID)
        assert result is None


# ---------------------------------------------------------------------------
# add_artist
# ---------------------------------------------------------------------------


class TestLidarrAddArtist:
    @pytest.mark.asyncio
    async def test_add_artist_success(self, aio_mock, lidarr_client):
        # 1. Lookup by lidarr: prefix
        aio_mock.get(
            f"{BASE}/artist/lookup?term=lidarr:{ARTIST_ID}",
            payload=LIDARR_SEARCH_RESULTS[:1],
            status=200,
        )
        # 2. POST artist
        aio_mock.post(
            f"{BASE}/artist",
            payload={"id": 1, "artistName": "Linkin Park"},
            status=200,
        )
        success, message = await lidarr_client.add_artist(
            ARTIST_ID, root_folder="/music", quality_profile_id=1
        )
        assert success is True
        assert "Successfully added" in message
        assert "Linkin Park" in message

    @pytest.mark.asyncio
    async def test_add_artist_already_exists(self, aio_mock, lidarr_client):
        # 1. Lookup
        aio_mock.get(
            f"{BASE}/artist/lookup?term=lidarr:{ARTIST_ID}",
            payload=LIDARR_SEARCH_RESULTS[:1],
            status=200,
        )
        # 2. POST returns already-exists error
        aio_mock.post(
            f"{BASE}/artist",
            payload=[{"errorMessage": "This artist already exists"}],
            status=400,
        )
        success, message = await lidarr_client.add_artist(
            ARTIST_ID, root_folder="/music", quality_profile_id=1
        )
        assert success is False
        assert "already in your library" in message

    @pytest.mark.asyncio
    async def test_add_artist_fallback_lookup(self, aio_mock, lidarr_client):
        """Lines 131-134: lidarr: prefix fails, fallback succeeds."""
        aio_mock.get(
            f"{BASE}/artist/lookup?term=lidarr:{ARTIST_ID}",
            status=500,
            body="error",
        )
        aio_mock.get(
            f"{BASE}/artist/lookup?term={ARTIST_ID}",
            payload=LIDARR_SEARCH_RESULTS,
            status=200,
        )
        aio_mock.post(
            f"{BASE}/artist",
            payload={"id": 1, "artistName": "Linkin Park"},
            status=200,
        )
        success, message = await lidarr_client.add_artist(
            ARTIST_ID, root_folder="/music", quality_profile_id=1
        )
        assert success is True
        assert "Successfully added" in message

    @pytest.mark.asyncio
    async def test_add_artist_both_lookups_fail(self, aio_mock, lidarr_client):
        """Lines 133-134: both lookups return None."""
        aio_mock.get(
            f"{BASE}/artist/lookup?term=lidarr:nonexistent",
            status=500,
            body="error",
        )
        aio_mock.get(
            f"{BASE}/artist/lookup?term=nonexistent",
            status=500,
            body="error",
        )
        success, message = await lidarr_client.add_artist("nonexistent")
        assert success is False
        assert "not found" in message.lower()

    @pytest.mark.asyncio
    async def test_add_artist_no_exact_match_uses_first(self, aio_mock, lidarr_client):
        """Line 145: no exact foreignArtistId match, uses first result."""
        aio_mock.get(
            f"{BASE}/artist/lookup?term=lidarr:unknown-id",
            payload=LIDARR_SEARCH_RESULTS,
            status=200,
        )
        aio_mock.post(
            f"{BASE}/artist",
            payload={"id": 1, "artistName": "Linkin Park"},
            status=200,
        )
        success, message = await lidarr_client.add_artist("unknown-id")
        assert success is True
        assert "Linkin Park" in message

    @pytest.mark.asyncio
    async def test_add_artist_falsy_first_element(self, aio_mock, lidarr_client):
        """Lines 148-149: lookup returns list with falsy element (empty dict).
        The for loop finds no match, fallback sets artist = lookup_response[0] = {},
        but {} is falsy, so `if not artist` is True -> 'Artist not found'.
        """
        aio_mock.get(
            f"{BASE}/artist/lookup?term=lidarr:empty",
            payload=[{}],
            status=200,
        )
        success, message = await lidarr_client.add_artist("empty")
        assert success is False
        assert "not found" in message.lower()

    @pytest.mark.asyncio
    async def test_add_artist_api_error_non_already(self, aio_mock, lidarr_client):
        """Lines 185-186: error array with non-'already exists' message."""
        aio_mock.get(
            f"{BASE}/artist/lookup?term=lidarr:{ARTIST_ID}",
            payload=LIDARR_SEARCH_RESULTS[:1],
            status=200,
        )
        aio_mock.post(
            f"{BASE}/artist",
            payload=[{"errorMessage": "Some other error"}],
            status=400,
        )
        success, message = await lidarr_client.add_artist(
            ARTIST_ID, root_folder="/music", quality_profile_id=1
        )
        assert success is False
        assert message == "Some other error"

    @pytest.mark.asyncio
    async def test_add_artist_json_decode_error_success(self, aio_mock, lidarr_client):
        """Lines 188-194: JSONDecodeError then status 201 fallback."""
        aio_mock.get(
            f"{BASE}/artist/lookup?term=lidarr:{ARTIST_ID}",
            payload=LIDARR_SEARCH_RESULTS[:1],
            status=200,
        )
        aio_mock.post(
            f"{BASE}/artist",
            body="not json",
            status=201,
        )
        success, message = await lidarr_client.add_artist(
            ARTIST_ID, root_folder="/music", quality_profile_id=1
        )
        assert success is True
        assert "Successfully added" in message

    @pytest.mark.asyncio
    async def test_add_artist_json_decode_error_failure(self, aio_mock, lidarr_client):
        """Lines 195-197: JSONDecodeError then non-success status."""
        aio_mock.get(
            f"{BASE}/artist/lookup?term=lidarr:{ARTIST_ID}",
            payload=LIDARR_SEARCH_RESULTS[:1],
            status=200,
        )
        aio_mock.post(
            f"{BASE}/artist",
            body="not json",
            status=500,
        )
        success, message = await lidarr_client.add_artist(
            ARTIST_ID, root_folder="/music", quality_profile_id=1
        )
        assert success is False
        assert "Failed to add" in message

    @pytest.mark.asyncio
    async def test_add_artist_client_error(self, aio_mock, lidarr_client):
        """Lines 199-201: ClientError during POST."""
        aio_mock.get(
            f"{BASE}/artist/lookup?term=lidarr:{ARTIST_ID}",
            payload=LIDARR_SEARCH_RESULTS[:1],
            status=200,
        )
        aio_mock.post(
            f"{BASE}/artist",
            exception=aiohttp.ClientError("connection lost"),
        )
        success, message = await lidarr_client.add_artist(
            ARTIST_ID, root_folder="/music", quality_profile_id=1
        )
        assert success is False
        assert "Connection error" in message

    @pytest.mark.asyncio
    async def test_add_artist_inner_generic_exception(self, aio_mock, lidarr_client):
        """Lines 202-204: generic Exception during POST."""
        aio_mock.get(
            f"{BASE}/artist/lookup?term=lidarr:{ARTIST_ID}",
            payload=LIDARR_SEARCH_RESULTS[:1],
            status=200,
        )
        aio_mock.post(
            f"{BASE}/artist",
            exception=RuntimeError("unexpected"),
        )
        success, message = await lidarr_client.add_artist(
            ARTIST_ID, root_folder="/music", quality_profile_id=1
        )
        assert success is False

    @pytest.mark.asyncio
    async def test_add_artist_outer_exception(self, lidarr_client):
        """Lines 206-208: outer Exception in add_artist."""
        with patch.object(lidarr_client, "_make_request", side_effect=Exception("outer boom")):
            success, message = await lidarr_client.add_artist(ARTIST_ID)
        assert success is False
        assert "outer boom" in message

    @pytest.mark.asyncio
    async def test_add_artist_includes_monitor_option_from_config(self, aio_mock):
        """add_artist POST body should include monitorOption from config."""
        from src.config.settings import config
        config._config["lidarr"]["features"]["monitorOption"] = "future"
        try:
            from src.api.lidarr import LidarrClient
            client = LidarrClient()

            aio_mock.get(
                f"{BASE}/artist/lookup?term=lidarr:{ARTIST_ID}",
                payload=LIDARR_SEARCH_RESULTS[:1],
                status=200,
            )

            posted_data = {}

            def capture(url, **kwargs):
                posted_data.update(kwargs.get("json", {}))
                return CallbackResult(
                    payload={"id": 1, "artistName": "Linkin Park"}, status=200
                )

            aio_mock.post(f"{BASE}/artist", callback=capture)

            success, _ = await client.add_artist(ARTIST_ID, "/music", 1)
            assert success is True
            assert posted_data["addOptions"]["monitor"] == "future", (
                "POST body addOptions.monitor must match config monitorOption"
            )
        finally:
            config._config["lidarr"]["features"]["monitorOption"] = "all"

    @pytest.mark.asyncio
    async def test_add_artist_includes_album_folder_from_config(self, aio_mock):
        """add_artist POST body should include albumFolder from config."""
        from src.config.settings import config
        config._config["lidarr"]["features"]["albumFolder"] = True
        try:
            from src.api.lidarr import LidarrClient
            client = LidarrClient()

            aio_mock.get(
                f"{BASE}/artist/lookup?term=lidarr:{ARTIST_ID}",
                payload=LIDARR_SEARCH_RESULTS[:1],
                status=200,
            )

            posted_data = {}

            def capture(url, **kwargs):
                posted_data.update(kwargs.get("json", {}))
                return CallbackResult(
                    payload={"id": 1, "artistName": "Linkin Park"}, status=200
                )

            aio_mock.post(f"{BASE}/artist", callback=capture)

            success, _ = await client.add_artist(ARTIST_ID, "/music", 1)
            assert success is True
            assert "albumFolder" in posted_data, "POST body must include albumFolder"
            assert posted_data["albumFolder"] is True
        finally:
            config._config["lidarr"]["features"]["albumFolder"] = True

    @pytest.mark.asyncio
    async def test_add_artist_reads_metadata_profile_id_from_config(self, aio_mock):
        """add_artist POST body should use metadataProfileId from config."""
        from src.config.settings import config
        config._config["lidarr"]["metadataProfileId"] = 5
        try:
            from src.api.lidarr import LidarrClient
            client = LidarrClient()

            aio_mock.get(
                f"{BASE}/artist/lookup?term=lidarr:{ARTIST_ID}",
                payload=LIDARR_SEARCH_RESULTS[:1],
                status=200,
            )

            posted_data = {}

            def capture(url, **kwargs):
                posted_data.update(kwargs.get("json", {}))
                return CallbackResult(
                    payload={"id": 1, "artistName": "Linkin Park"}, status=200
                )

            aio_mock.post(f"{BASE}/artist", callback=capture)

            success, _ = await client.add_artist(ARTIST_ID, "/music", 1)
            assert success is True
            assert posted_data["metadataProfileId"] == 5, (
                "POST body metadataProfileId must match config value"
            )
        finally:
            config._config["lidarr"]["metadataProfileId"] = 1


# ---------------------------------------------------------------------------
# get_root_folders
# ---------------------------------------------------------------------------


class TestLidarrRootFolders:
    @pytest.mark.asyncio
    async def test_get_root_folders_success(self, aio_mock, lidarr_client):
        """Lines 212-215: successful get_root_folders."""
        aio_mock.get(
            f"{BASE}/rootFolder",
            payload=[{"path": "/music"}, {"path": "/music2"}],
            status=200,
        )
        folders = await lidarr_client.get_root_folders()
        assert folders == ["/music", "/music2"]

    @pytest.mark.asyncio
    async def test_get_root_folders_empty(self, aio_mock, lidarr_client):
        """Line 216: returns empty when API returns None."""
        aio_mock.get(
            f"{BASE}/rootFolder",
            status=500,
            body="error",
        )
        folders = await lidarr_client.get_root_folders()
        assert folders == []

    @pytest.mark.asyncio
    async def test_get_root_folders_exception(self, lidarr_client):
        """Lines 217-219: Exception in get_root_folders."""
        with patch.object(lidarr_client, "_make_request", side_effect=Exception("boom")):
            folders = await lidarr_client.get_root_folders()
        assert folders == []

    @pytest.mark.asyncio
    async def test_get_root_folders_excludes_by_basename_when_narrow(self, aio_mock):
        """narrowRootFolderNames makes excludedRootFolders match by basename."""
        from src.config.settings import config
        orig_paths = config._config["lidarr"]["paths"].copy()
        config._config["lidarr"]["paths"]["excludedRootFolders"] = ["music2"]
        config._config["lidarr"]["paths"]["narrowRootFolderNames"] = True
        try:
            from src.api.lidarr import LidarrClient
            client = LidarrClient()
            aio_mock.get(
                f"{BASE}/rootFolder",
                payload=[{"path": "/data/music"}, {"path": "/data/music2"}],
                status=200,
            )
            folders = await client.get_root_folders()
            assert "/data/music" in folders
            assert "/data/music2" not in folders
        finally:
            config._config["lidarr"]["paths"] = orig_paths

    @pytest.mark.asyncio
    async def test_get_root_folders_excludes_by_full_path_when_not_narrow(self, aio_mock):
        """Without narrowRootFolderNames, excludedRootFolders matches full path."""
        from src.config.settings import config
        orig_paths = config._config["lidarr"]["paths"].copy()
        config._config["lidarr"]["paths"]["excludedRootFolders"] = ["/data/music2"]
        config._config["lidarr"]["paths"]["narrowRootFolderNames"] = False
        try:
            from src.api.lidarr import LidarrClient
            client = LidarrClient()
            aio_mock.get(
                f"{BASE}/rootFolder",
                payload=[{"path": "/data/music"}, {"path": "/data/music2"}],
                status=200,
            )
            folders = await client.get_root_folders()
            assert "/data/music" in folders
            assert "/data/music2" not in folders
        finally:
            config._config["lidarr"]["paths"] = orig_paths


# ---------------------------------------------------------------------------
# get_metadata_profiles
# ---------------------------------------------------------------------------


class TestLidarrMetadataProfiles:
    @pytest.mark.asyncio
    async def test_get_metadata_profiles(self, aio_mock, lidarr_client):
        aio_mock.get(
            f"{BASE}/metadataprofile",
            payload=LIDARR_METADATA_PROFILES,
            status=200,
        )
        profiles = await lidarr_client.get_metadata_profiles()
        assert len(profiles) == 2
        assert profiles[0]["id"] == 1
        assert profiles[0]["name"] == "Standard"
        assert profiles[1]["id"] == 2
        assert profiles[1]["name"] == "None"

    @pytest.mark.asyncio
    async def test_get_metadata_profiles_empty(self, aio_mock, lidarr_client):
        """Lines 253: returns empty when API returns None."""
        aio_mock.get(
            f"{BASE}/metadataprofile",
            status=500,
            body="error",
        )
        profiles = await lidarr_client.get_metadata_profiles()
        assert profiles == []

    @pytest.mark.asyncio
    async def test_get_metadata_profiles_exception(self, lidarr_client):
        """Lines 254-256: Exception in get_metadata_profiles."""
        with patch.object(lidarr_client, "_make_request", side_effect=Exception("boom")):
            profiles = await lidarr_client.get_metadata_profiles()
        assert profiles == []


# ---------------------------------------------------------------------------
# get_quality_profiles
# ---------------------------------------------------------------------------


class TestLidarrQualityProfiles:
    @pytest.mark.asyncio
    async def test_get_quality_profiles(self, aio_mock, lidarr_client):
        aio_mock.get(
            f"{BASE}/qualityprofile",
            payload=[
                {"id": 1, "name": "Lossless", "upgradeAllowed": True},
                {"id": 2, "name": "Standard", "upgradeAllowed": False},
            ],
            status=200,
        )
        profiles = await lidarr_client.get_quality_profiles()
        assert len(profiles) == 2
        assert profiles[0]["id"] == 1
        assert profiles[0]["name"] == "Lossless"

    @pytest.mark.asyncio
    async def test_get_quality_profiles_empty(self, aio_mock, lidarr_client):
        """Lines 228-229: empty quality profiles."""
        aio_mock.get(
            f"{BASE}/qualityprofile",
            status=500,
            body="error",
        )
        profiles = await lidarr_client.get_quality_profiles()
        assert profiles == []

    @pytest.mark.asyncio
    async def test_get_quality_profiles_exception(self, lidarr_client):
        """Lines 243-245: Exception in get_quality_profiles."""
        with patch.object(lidarr_client, "_make_request", side_effect=Exception("boom")):
            profiles = await lidarr_client.get_quality_profiles()
        assert profiles == []


# ---------------------------------------------------------------------------
# check_status
# ---------------------------------------------------------------------------


class TestLidarrCheckStatus:
    @pytest.mark.asyncio
    async def test_check_status_online(self, aio_mock, lidarr_client):
        aio_mock.get(
            f"{BASE}/system/status",
            payload={"version": "2.0.0", "appName": "Lidarr"},
            status=200,
        )
        result = await lidarr_client.check_status()
        assert result is True

    @pytest.mark.asyncio
    async def test_check_status_offline(self, aio_mock, lidarr_client):
        aio_mock.get(
            f"{BASE}/system/status",
            exception=aiohttp.ClientError("connection refused"),
        )
        result = await lidarr_client.check_status()
        assert result is False

    @pytest.mark.asyncio
    async def test_check_status_exception(self, lidarr_client):
        """Lines 263-265: Exception in check_status."""
        with patch.object(lidarr_client, "_make_request", side_effect=Exception("boom")):
            result = await lidarr_client.check_status()
        assert result is False


# ---------------------------------------------------------------------------
# get_artists
# ---------------------------------------------------------------------------


class TestGetArtists:
    @pytest.mark.asyncio
    async def test_get_artists_success(self, aio_mock, lidarr_client):
        aio_mock.get(
            f"{BASE}/artist",
            payload=LIDARR_LIBRARY_ARTISTS,
            status=200,
        )
        results = await lidarr_client.get_artists()
        assert len(results) == 2
        assert results[0]["artistName"] == "Linkin Park"
        assert results[1]["artistName"] == "Radiohead"

    @pytest.mark.asyncio
    async def test_get_artists_empty(self, aio_mock, lidarr_client):
        aio_mock.get(
            f"{BASE}/artist",
            payload=[],
            status=200,
        )
        results = await lidarr_client.get_artists()
        assert results == []

    @pytest.mark.asyncio
    async def test_get_artists_connection_error(self, aio_mock, lidarr_client):
        aio_mock.get(
            f"{BASE}/artist",
            exception=aiohttp.ClientError("refused"),
        )
        results = await lidarr_client.get_artists()
        assert results == []

    @pytest.mark.asyncio
    async def test_get_artists_exception(self, lidarr_client):
        with patch.object(lidarr_client, "_make_request", side_effect=Exception("boom")):
            results = await lidarr_client.get_artists()
        assert results == []


# ---------------------------------------------------------------------------
# get_artist_by_id
# ---------------------------------------------------------------------------


class TestGetArtistById:
    @pytest.mark.asyncio
    async def test_get_artist_by_id_success(self, aio_mock, lidarr_client):
        aio_mock.get(
            f"{BASE}/artist/1",
            payload=LIDARR_LIBRARY_ARTIST_DETAIL,
            status=200,
        )
        result = await lidarr_client.get_artist_by_id(1)
        assert result is not None
        assert result["artistName"] == "Linkin Park"
        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_get_artist_by_id_not_found(self, aio_mock, lidarr_client):
        aio_mock.get(
            f"{BASE}/artist/999",
            status=404,
            body="Not found",
        )
        result = await lidarr_client.get_artist_by_id(999)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_artist_by_id_exception(self, lidarr_client):
        with patch.object(lidarr_client, "_make_request", side_effect=Exception("boom")):
            result = await lidarr_client.get_artist_by_id(1)
        assert result is None


# ---------------------------------------------------------------------------
# delete_artist
# ---------------------------------------------------------------------------


class TestDeleteArtist:
    @pytest.mark.asyncio
    async def test_delete_artist_success(self, aio_mock, lidarr_client):
        aio_mock.delete(
            "http://localhost:8686/api/v1/artist/1",
            status=200,
            body="",
        )
        result = await lidarr_client.delete_artist(1)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_artist_not_found(self, aio_mock, lidarr_client):
        aio_mock.delete(
            "http://localhost:8686/api/v1/artist/999",
            status=404,
            body="Not found",
        )
        result = await lidarr_client.delete_artist(999)
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_artist_connection_error(self, aio_mock, lidarr_client):
        aio_mock.delete(
            "http://localhost:8686/api/v1/artist/1",
            exception=aiohttp.ClientError("refused"),
        )
        result = await lidarr_client.delete_artist(1)
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_artist_exception(self, aio_mock, lidarr_client):
        aio_mock.delete(
            "http://localhost:8686/api/v1/artist/1",
            exception=RuntimeError("unexpected"),
        )
        result = await lidarr_client.delete_artist(1)
        assert result is False
