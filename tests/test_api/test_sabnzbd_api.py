"""
Tests for src/api/sabnzbd.py -- SabnzbdClient.
"""

import pytest
import aiohttp

from tests.fixtures.sample_data import SABNZBD_QUEUE


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


class TestSabnzbdInit:
    def test_init_success(self, sabnzbd_client, sabnzbd_url):
        assert sabnzbd_client.api_url == sabnzbd_url
        assert sabnzbd_client.api_key == "test-sabnzbd-key"

    def test_init_missing_addr(self):
        """Lines 33-34: ValueError when addr is missing."""
        from src.config.settings import config
        original = config["sabnzbd"]["server"]["addr"]
        try:
            config["sabnzbd"]["server"]["addr"] = None
            from src.api.sabnzbd import SabnzbdClient
            with pytest.raises(ValueError, match="address or port not configured"):
                SabnzbdClient()
        finally:
            config["sabnzbd"]["server"]["addr"] = original

    def test_init_missing_apikey(self):
        """Lines 40-41: ValueError when apikey is missing."""
        from src.config.settings import config
        original = config["sabnzbd"]["auth"]["apikey"]
        try:
            config["sabnzbd"]["auth"]["apikey"] = None
            from src.api.sabnzbd import SabnzbdClient
            with pytest.raises(ValueError, match="API key not configured"):
                SabnzbdClient()
        finally:
            config["sabnzbd"]["auth"]["apikey"] = original


# ---------------------------------------------------------------------------
# check_status
# ---------------------------------------------------------------------------


class TestSabnzbdCheckStatus:
    @pytest.mark.asyncio
    async def test_check_status_online(self, aio_mock, sabnzbd_client, sabnzbd_url):
        url = f"{sabnzbd_url}/api?mode=queue&output=json&apikey=test-sabnzbd-key"
        aio_mock.get(
            url,
            payload=SABNZBD_QUEUE,
            status=200,
        )
        result = await sabnzbd_client.check_status()
        assert result is True

    @pytest.mark.asyncio
    async def test_check_status_offline(self, aio_mock, sabnzbd_client, sabnzbd_url):
        url = f"{sabnzbd_url}/api?mode=queue&output=json&apikey=test-sabnzbd-key"
        aio_mock.get(
            url,
            exception=aiohttp.ClientError("connection refused"),
        )
        result = await sabnzbd_client.check_status()
        assert result is False


# ---------------------------------------------------------------------------
# set_speed_limit
# ---------------------------------------------------------------------------


class TestSabnzbdSetSpeedLimit:
    @pytest.mark.asyncio
    async def test_set_speed_limit_success(self, aio_mock, sabnzbd_client, sabnzbd_url):
        url = f"{sabnzbd_url}/api?mode=config&name=speedlimit&value=50&output=json&apikey=test-sabnzbd-key"
        aio_mock.get(url, payload={"status": True}, status=200)
        result = await sabnzbd_client.set_speed_limit(50)
        assert result is True

    @pytest.mark.asyncio
    async def test_set_speed_limit_http_error(self, aio_mock, sabnzbd_client, sabnzbd_url):
        url = f"{sabnzbd_url}/api?mode=config&name=speedlimit&value=50&output=json&apikey=test-sabnzbd-key"
        aio_mock.get(url, status=500)
        result = await sabnzbd_client.set_speed_limit(50)
        assert result is False

    @pytest.mark.asyncio
    async def test_set_speed_limit_connection_error(self, aio_mock, sabnzbd_client, sabnzbd_url):
        url = f"{sabnzbd_url}/api?mode=config&name=speedlimit&value=50&output=json&apikey=test-sabnzbd-key"
        aio_mock.get(url, exception=aiohttp.ClientError("connection refused"))
        result = await sabnzbd_client.set_speed_limit(50)
        assert result is False
