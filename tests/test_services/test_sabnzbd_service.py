"""
Tests for src/services/sabnzbd.py -- SABnzbdService.

The mock config has sabnzbd.enable=False by default, so instantiating
SABnzbdService() will raise ValueError. Tests that need a working service
use the enabled_sabnzbd_config fixture.
"""

import re

import pytest
from aioresponses import aioresponses

from tests.conftest import _mock_config


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SABNZBD_QUEUE = {
    "queue": {
        "slots": [
            {"status": "Downloading", "filename": "test.nzb"},
        ],
        "noofslots": 3,
        "speed": "5.2 MB/s",
        "size": "1.2 GB",
    }
}

# Pattern to match SABnzbd API URLs regardless of query param ordering
SABNZBD_API_PATTERN = re.compile(r"^http://localhost:8090//api\?.*$")


@pytest.fixture
def enabled_sabnzbd_config():
    """Temporarily enable sabnzbd in mock config."""
    original = _mock_config._config["sabnzbd"]["enable"]
    _mock_config._config["sabnzbd"]["enable"] = True
    yield
    _mock_config._config["sabnzbd"]["enable"] = original


@pytest.fixture
def sabnzbd_service(enabled_sabnzbd_config):
    """Create a SABnzbdService with sabnzbd enabled."""
    from src.services.sabnzbd import SABnzbdService

    return SABnzbdService()


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


class TestSABnzbdServiceInit:
    def test_init_disabled_raises(self):
        from src.services.sabnzbd import SABnzbdService

        with pytest.raises(ValueError, match="SABnzbd is not enabled"):
            SABnzbdService()

    def test_init_success(self, enabled_sabnzbd_config):
        from src.services.sabnzbd import SABnzbdService

        service = SABnzbdService()
        assert service.api_key == "test-sabnzbd-key"
        assert "localhost" in service.base_url
        assert "8090" in service.base_url

    def test_init_no_api_key(self, enabled_sabnzbd_config):
        """When api key is missing, should raise ValueError."""
        from src.services.sabnzbd import SABnzbdService

        original_apikey = _mock_config._config["sabnzbd"]["auth"]["apikey"]
        _mock_config._config["sabnzbd"]["auth"]["apikey"] = None
        try:
            with pytest.raises(ValueError, match="API key not configured"):
                SABnzbdService()
        finally:
            _mock_config._config["sabnzbd"]["auth"]["apikey"] = original_apikey


# ---------------------------------------------------------------------------
# get_status
# ---------------------------------------------------------------------------


class TestGetStatus:
    @pytest.mark.asyncio
    async def test_get_status_success(self, sabnzbd_service):
        with aioresponses() as m:
            m.get(
                SABNZBD_API_PATTERN,
                payload=SABNZBD_QUEUE,
                status=200,
            )
            status = await sabnzbd_service.get_status()

        assert status["active"] == 1
        assert status["queued"] == 3
        assert status["speed"] == "5.2 MB/s"
        assert status["size"] == "1.2 GB"

    @pytest.mark.asyncio
    async def test_get_status_http_error(self, sabnzbd_service):
        with aioresponses() as m:
            m.get(
                SABNZBD_API_PATTERN,
                status=500,
            )
            status = await sabnzbd_service.get_status()

        assert status["active"] == 0
        assert status["queued"] == 0
        assert status["speed"] == "0 KB/s"

    @pytest.mark.asyncio
    async def test_get_status_error(self, sabnzbd_service):
        with aioresponses() as m:
            m.get(
                SABNZBD_API_PATTERN,
                exception=Exception("Connection refused"),
            )
            status = await sabnzbd_service.get_status()

        assert status["active"] == 0
        assert status["queued"] == 0


# ---------------------------------------------------------------------------
# add_nzb
# ---------------------------------------------------------------------------


class TestAddNzb:
    @pytest.mark.asyncio
    async def test_add_nzb_success(self, sabnzbd_service):
        with aioresponses() as m:
            m.get(
                SABNZBD_API_PATTERN,
                payload={"status": True, "nzo_ids": ["SABnzbd_nzo_abc"]},
                status=200,
            )
            result = await sabnzbd_service.add_nzb(
                "http://example.com/test.nzb", name="test", category="movies"
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_add_nzb_http_error(self, sabnzbd_service):
        with aioresponses() as m:
            m.get(
                SABNZBD_API_PATTERN,
                status=500,
            )
            result = await sabnzbd_service.add_nzb("http://example.com/test.nzb")

        assert result is False

    @pytest.mark.asyncio
    async def test_add_nzb_failure(self, sabnzbd_service):
        with aioresponses() as m:
            m.get(
                SABNZBD_API_PATTERN,
                exception=Exception("Connection refused"),
            )
            result = await sabnzbd_service.add_nzb("http://example.com/test.nzb")

        assert result is False


# ---------------------------------------------------------------------------
# set_speed_limit
# ---------------------------------------------------------------------------


class TestSetSpeedLimit:
    @pytest.mark.asyncio
    async def test_set_speed_limit_success(self, sabnzbd_service):
        with aioresponses() as m:
            m.get(SABNZBD_API_PATTERN, payload={"status": True}, status=200)
            result = await sabnzbd_service.set_speed_limit(50)

        assert result is True

    @pytest.mark.asyncio
    async def test_set_speed_limit_http_error(self, sabnzbd_service):
        with aioresponses() as m:
            m.get(SABNZBD_API_PATTERN, status=500)
            result = await sabnzbd_service.set_speed_limit(50)

        assert result is False

    @pytest.mark.asyncio
    async def test_set_speed_limit_connection_error(self, sabnzbd_service):
        with aioresponses() as m:
            m.get(
                SABNZBD_API_PATTERN,
                exception=Exception("Connection refused"),
            )
            result = await sabnzbd_service.set_speed_limit(50)

        assert result is False


# ---------------------------------------------------------------------------
# pause_queue
# ---------------------------------------------------------------------------


class TestPauseQueue:
    @pytest.mark.asyncio
    async def test_pause_queue_success(self, sabnzbd_service):
        with aioresponses() as m:
            m.get(SABNZBD_API_PATTERN, payload={"status": True}, status=200)
            result = await sabnzbd_service.pause_queue()

        assert result is True

    @pytest.mark.asyncio
    async def test_pause_queue_http_error(self, sabnzbd_service):
        with aioresponses() as m:
            m.get(SABNZBD_API_PATTERN, status=500)
            result = await sabnzbd_service.pause_queue()

        assert result is False

    @pytest.mark.asyncio
    async def test_pause_queue_connection_error(self, sabnzbd_service):
        with aioresponses() as m:
            m.get(
                SABNZBD_API_PATTERN,
                exception=Exception("Connection refused"),
            )
            result = await sabnzbd_service.pause_queue()

        assert result is False


# ---------------------------------------------------------------------------
# resume_queue
# ---------------------------------------------------------------------------


class TestResumeQueue:
    @pytest.mark.asyncio
    async def test_resume_queue_success(self, sabnzbd_service):
        with aioresponses() as m:
            m.get(SABNZBD_API_PATTERN, payload={"status": True}, status=200)
            result = await sabnzbd_service.resume_queue()

        assert result is True

    @pytest.mark.asyncio
    async def test_resume_queue_http_error(self, sabnzbd_service):
        with aioresponses() as m:
            m.get(SABNZBD_API_PATTERN, status=500)
            result = await sabnzbd_service.resume_queue()

        assert result is False

    @pytest.mark.asyncio
    async def test_resume_queue_connection_error(self, sabnzbd_service):
        with aioresponses() as m:
            m.get(
                SABNZBD_API_PATTERN,
                exception=Exception("Connection refused"),
            )
            result = await sabnzbd_service.resume_queue()

        assert result is False


# ---------------------------------------------------------------------------
# get_history
# ---------------------------------------------------------------------------


SABNZBD_HISTORY_RESPONSE = {
    "history": {
        "noofslots": 2,
        "slots": [
            {
                "status": "Completed",
                "nzb_name": "Ubuntu.22.04.nzb",
                "name": "Ubuntu 22.04",
                "category": "software",
                "size": "2.1 GB",
                "completed": 1700000000,
            },
            {
                "status": "Completed",
                "nzb_name": "Fedora.39.nzb",
                "name": "Fedora 39",
                "category": "software",
                "size": "1.8 GB",
                "completed": 1700001000,
            },
        ],
    }
}


class TestGetHistory:
    @pytest.mark.asyncio
    async def test_get_history_success(self, sabnzbd_service):
        with aioresponses() as m:
            m.get(
                SABNZBD_API_PATTERN,
                payload=SABNZBD_HISTORY_RESPONSE,
                status=200,
            )
            result = await sabnzbd_service.get_history()

        assert result["total"] == 2
        assert len(result["items"]) == 2
        assert result["items"][0]["name"] == "Ubuntu 22.04"

    @pytest.mark.asyncio
    async def test_get_history_http_error(self, sabnzbd_service):
        with aioresponses() as m:
            m.get(SABNZBD_API_PATTERN, status=500)
            result = await sabnzbd_service.get_history()

        assert result == {"total": 0, "items": []}

    @pytest.mark.asyncio
    async def test_get_history_connection_error(self, sabnzbd_service):
        with aioresponses() as m:
            m.get(
                SABNZBD_API_PATTERN,
                exception=Exception("Connection refused"),
            )
            result = await sabnzbd_service.get_history()

        assert result == {"total": 0, "items": []}
