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
