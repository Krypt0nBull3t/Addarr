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
