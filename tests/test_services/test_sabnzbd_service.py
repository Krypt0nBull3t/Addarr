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
    async def test_add_nzb_failure(self, sabnzbd_service):
        with aioresponses() as m:
            m.get(
                SABNZBD_API_PATTERN,
                exception=Exception("Connection refused"),
            )
            result = await sabnzbd_service.add_nzb("http://example.com/test.nzb")

        assert result is False
