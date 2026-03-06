"""
Tests for src/services/transmission.py -- TransmissionService.

TransmissionClient reads config from the global singleton (mocked in conftest).
Service methods that call async client methods use AsyncMock.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tests.conftest import _mock_config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TRANSMISSION_SESSION = {
    "arguments": {
        "alt-speed-enabled": True,
        "version": "3.00",
    }
}


@pytest.fixture
def enabled_transmission_config():
    """Temporarily enable transmission in mock config."""
    original = _mock_config._config["transmission"]["enable"]
    _mock_config._config["transmission"]["enable"] = True
    yield
    _mock_config._config["transmission"]["enable"] = original


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTransmissionServiceSingleton:
    def test_singleton(self):
        from src.services.transmission import TransmissionService

        a = TransmissionService()
        b = TransmissionService()
        assert a is b


class TestTransmissionServiceEnabled:
    def test_is_enabled_false(self):
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        assert service.is_enabled() is False

    def test_is_enabled_true(self, enabled_transmission_config):
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        assert service.is_enabled() is True


class TestTransmissionServiceClient:
    def test_client_disabled(self):
        """When transmission is disabled, the client property returns None."""
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        assert service.client is None

    def test_client_enabled_creates_client(self, enabled_transmission_config):
        """When transmission is enabled and client is None, create one."""
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        mock_api = MagicMock()

        with patch(
            "src.services.transmission.TransmissionClient",
            return_value=mock_api,
        ):
            client = service.client

        assert client is mock_api

    def test_client_enabled_init_exception(self, enabled_transmission_config):
        """When TransmissionClient raises, client property returns None."""
        from src.services.transmission import TransmissionService

        service = TransmissionService()

        with patch(
            "src.services.transmission.TransmissionClient",
            side_effect=Exception("Connection failed"),
        ):
            client = service.client

        assert client is None


class TestTransmissionServiceNoClient:
    @pytest.mark.asyncio
    async def test_set_alt_speed_no_client(self):
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        service._client = None

        result = await service.set_alt_speed(True)
        assert result is False

    @pytest.mark.asyncio
    async def test_get_status_not_connected(self):
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        service._client = None

        status = await service.get_status()
        assert status["connected"] is False

    @pytest.mark.asyncio
    async def test_test_connection_no_client(self):
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        service._client = None

        assert await service.test_connection() is False


class TestTransmissionServiceWithMockClient:
    @pytest.mark.asyncio
    async def test_set_alt_speed_success(self):
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        mock_client = AsyncMock()
        service._client = mock_client

        result = await service.set_alt_speed(True)

        assert result is True
        mock_client.set_alt_speed_enabled.assert_awaited_once_with(True)

    @pytest.mark.asyncio
    async def test_set_alt_speed_exception(self):
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        mock_client = AsyncMock()
        mock_client.set_alt_speed_enabled.side_effect = Exception("API error")
        service._client = mock_client

        result = await service.set_alt_speed(True)

        assert result is False

    @pytest.mark.asyncio
    async def test_get_status_connected(self):
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        mock_client = AsyncMock()
        mock_client.get_session.return_value = TRANSMISSION_SESSION
        service._client = mock_client

        status = await service.get_status()

        assert status["connected"] is True
        assert status["alt_speed_enabled"] is True
        assert status["version"] == "3.00"

    @pytest.mark.asyncio
    async def test_get_status_exception(self):
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        mock_client = AsyncMock()
        mock_client.get_session.side_effect = Exception("Connection lost")
        service._client = mock_client

        status = await service.get_status()

        assert status["connected"] is False
        assert status["error"] == "Connection lost"

    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        mock_client = AsyncMock()
        mock_client.test_connection.return_value = True
        service._client = mock_client

        assert await service.test_connection() is True
        mock_client.test_connection.assert_awaited_once()


# ---------------------------------------------------------------------------
# get_queue_details
# ---------------------------------------------------------------------------

TORRENT_GET_RESPONSE = {
    "result": "success",
    "arguments": {
        "torrents": [
            {
                "id": 1,
                "name": "Ubuntu 24.04 ISO",
                "status": 4,  # Downloading
                "percentDone": 0.75,
                "rateDownload": 1048576,  # 1 MB/s
                "eta": 3600,  # 1 hour
                "sizeWhenDone": 4294967296,  # 4 GB
                "totalSize": 4294967296,
            },
            {
                "id": 2,
                "name": "Fedora Workstation",
                "status": 0,  # Stopped
                "percentDone": 0.5,
                "rateDownload": 0,
                "eta": -1,  # unknown
                "sizeWhenDone": 2147483648,  # 2 GB
                "totalSize": 2147483648,
            },
        ]
    },
}

SESSION_RESPONSE = {
    "result": "success",
    "arguments": {
        "download-dir": "/downloads",
        "version": "4.0.0",
    },
}


class TestTransmissionFormatHelpers:
    def test_format_speed_bytes(self):
        from src.services.transmission import TransmissionService
        assert TransmissionService._format_speed(500) == "500 B/s"

    def test_format_speed_kb(self):
        from src.services.transmission import TransmissionService
        assert TransmissionService._format_speed(2048) == "2.0 KB/s"

    def test_format_speed_mb(self):
        from src.services.transmission import TransmissionService
        assert TransmissionService._format_speed(1048576) == "1.0 MB/s"

    def test_format_speed_gb(self):
        from src.services.transmission import TransmissionService
        assert TransmissionService._format_speed(1073741824) == "1.0 GB/s"

    def test_format_size_bytes(self):
        from src.services.transmission import TransmissionService
        assert TransmissionService._format_size(500) == "500 B"

    def test_format_size_kb(self):
        from src.services.transmission import TransmissionService
        assert TransmissionService._format_size(2048) == "2.0 KB"

    def test_format_size_mb(self):
        from src.services.transmission import TransmissionService
        assert TransmissionService._format_size(1048576) == "1.0 MB"

    def test_format_size_gb(self):
        from src.services.transmission import TransmissionService
        assert TransmissionService._format_size(4294967296) == "4.00 GB"

    def test_format_eta_unknown(self):
        from src.services.transmission import TransmissionService
        assert TransmissionService._format_eta(-1) == "Unknown"

    def test_format_eta_seconds(self):
        from src.services.transmission import TransmissionService
        assert TransmissionService._format_eta(45) == "45s"

    def test_format_eta_minutes(self):
        from src.services.transmission import TransmissionService
        assert TransmissionService._format_eta(125) == "2m 5s"

    def test_format_eta_hours(self):
        from src.services.transmission import TransmissionService
        assert TransmissionService._format_eta(3665) == "1h 1m"


class TestTransmissionQueueDetails:
    @pytest.mark.asyncio
    async def test_get_queue_details_returns_correct_shape(self):
        """get_queue_details() returns dict matching SABnzbd shape."""
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        mock_client = AsyncMock()
        mock_client.get_torrents.return_value = TORRENT_GET_RESPONSE
        mock_client.get_session.return_value = SESSION_RESPONSE
        service._client = mock_client

        result = await service.get_queue_details()

        assert isinstance(result, dict)
        assert "paused" in result
        assert "speed" in result
        assert "size_remaining" in result
        assert "items_count" in result
        assert "items" in result
        assert result["items_count"] == 2

        # Check first item has correct keys
        item = result["items"][0]
        assert item["nzo_id"] == 1
        assert item["title"] == "Ubuntu 24.04 ISO"
        assert item["status"] == "Downloading"
        assert item["progress"] == 75  # 0.75 * 100
        assert "size" in item
        assert "timeleft" in item

    @pytest.mark.asyncio
    async def test_get_queue_details_maps_status_codes(self):
        """Status codes mapped: 0=Stopped, 4=Downloading, 6=Seeding."""
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        mock_client = AsyncMock()
        mock_client.get_torrents.return_value = TORRENT_GET_RESPONSE
        mock_client.get_session.return_value = SESSION_RESPONSE
        service._client = mock_client

        result = await service.get_queue_details()

        assert result["items"][0]["status"] == "Downloading"
        assert result["items"][1]["status"] == "Stopped"

    @pytest.mark.asyncio
    async def test_get_queue_details_paused_when_all_stopped(self):
        """paused=True when all torrents have status 0 (Stopped)."""
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        stopped_response = {
            "result": "success",
            "arguments": {
                "torrents": [
                    {"id": 1, "name": "A", "status": 0, "percentDone": 1.0,
                     "rateDownload": 0, "eta": -1, "sizeWhenDone": 100,
                     "totalSize": 100},
                ]
            },
        }
        mock_client = AsyncMock()
        mock_client.get_torrents.return_value = stopped_response
        mock_client.get_session.return_value = SESSION_RESPONSE
        service._client = mock_client

        result = await service.get_queue_details()
        assert result["paused"] is True

    @pytest.mark.asyncio
    async def test_get_queue_details_empty_on_error(self):
        """Returns empty dict shape on exception."""
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        mock_client = AsyncMock()
        mock_client.get_torrents.side_effect = Exception("Connection lost")
        service._client = mock_client

        result = await service.get_queue_details()

        assert result["items_count"] == 0
        assert result["items"] == []

    @pytest.mark.asyncio
    async def test_get_queue_details_empty_when_no_torrents(self):
        """Returns correct shape when no torrents exist."""
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        mock_client = AsyncMock()
        mock_client.get_torrents.return_value = {
            "result": "success",
            "arguments": {"torrents": []},
        }
        mock_client.get_session.return_value = SESSION_RESPONSE
        service._client = mock_client

        result = await service.get_queue_details()

        assert result["items_count"] == 0
        assert result["items"] == []
        assert result["paused"] is False

    @pytest.mark.asyncio
    async def test_get_queue_details_no_client(self):
        """Returns False/empty when client is None."""
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        service._client = None

        result = await service.get_queue_details()

        assert result["items_count"] == 0
        assert result["items"] == []


# ---------------------------------------------------------------------------
# pause_item / resume_item / pause_queue / resume_queue
# ---------------------------------------------------------------------------


class TestTransmissionQueueControl:
    @pytest.mark.asyncio
    async def test_pause_item_success(self):
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        mock_client = AsyncMock()
        mock_client.pause_torrent.return_value = {"result": "success"}
        service._client = mock_client

        result = await service.pause_item(42)
        assert result is True
        mock_client.pause_torrent.assert_awaited_once_with(42)

    @pytest.mark.asyncio
    async def test_resume_item_success(self):
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        mock_client = AsyncMock()
        mock_client.resume_torrent.return_value = {"result": "success"}
        service._client = mock_client

        result = await service.resume_item(7)
        assert result is True
        mock_client.resume_torrent.assert_awaited_once_with(7)

    @pytest.mark.asyncio
    async def test_pause_queue_success(self):
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        mock_client = AsyncMock()
        mock_client.stop_all.return_value = {"result": "success"}
        service._client = mock_client

        result = await service.pause_queue()
        assert result is True
        mock_client.stop_all.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_resume_queue_success(self):
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        mock_client = AsyncMock()
        mock_client.start_all.return_value = {"result": "success"}
        service._client = mock_client

        result = await service.resume_queue()
        assert result is True
        mock_client.start_all.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_pause_item_no_client(self):
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        service._client = None
        assert await service.pause_item(1) is False

    @pytest.mark.asyncio
    async def test_resume_item_no_client(self):
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        service._client = None
        assert await service.resume_item(1) is False

    @pytest.mark.asyncio
    async def test_pause_queue_no_client(self):
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        service._client = None
        assert await service.pause_queue() is False

    @pytest.mark.asyncio
    async def test_resume_queue_no_client(self):
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        service._client = None
        assert await service.resume_queue() is False

    @pytest.mark.asyncio
    async def test_pause_item_exception(self):
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        mock_client = AsyncMock()
        mock_client.pause_torrent.side_effect = Exception("fail")
        service._client = mock_client

        assert await service.pause_item(1) is False

    @pytest.mark.asyncio
    async def test_resume_item_exception(self):
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        mock_client = AsyncMock()
        mock_client.resume_torrent.side_effect = Exception("fail")
        service._client = mock_client

        assert await service.resume_item(1) is False

    @pytest.mark.asyncio
    async def test_pause_queue_exception(self):
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        mock_client = AsyncMock()
        mock_client.stop_all.side_effect = Exception("fail")
        service._client = mock_client

        assert await service.pause_queue() is False

    @pytest.mark.asyncio
    async def test_resume_queue_exception(self):
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        mock_client = AsyncMock()
        mock_client.start_all.side_effect = Exception("fail")
        service._client = mock_client

        assert await service.resume_queue() is False
