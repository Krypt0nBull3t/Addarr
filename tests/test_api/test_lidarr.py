"""
Tests for src/api/lidarr.py -- LidarrClient.

NOTE: Lidarr uses /api/v1/ (not v3).
"""

import json
import pytest
import aiohttp

from tests.fixtures.sample_data import (
    LIDARR_SEARCH_RESULTS,
    LIDARR_METADATA_PROFILES,
)


BASE = "http://localhost:8686/api/v1"

ARTIST_ID = "f59c5520-5f46-4d2c-b2c4-822eabf53419"


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
