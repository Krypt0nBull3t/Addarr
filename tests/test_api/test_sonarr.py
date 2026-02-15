"""
Tests for src/api/sonarr.py -- SonarrClient.
"""

import pytest
import aiohttp

from tests.fixtures.sample_data import (
    SONARR_SEARCH_RESULTS,
    SONARR_SERIES_DETAIL,
)


BASE = "http://localhost:8989/api/v3"


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
