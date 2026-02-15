"""
Tests for src/services/transmission.py -- TransmissionService.

The TransmissionAPI inherits from BaseApiClient which reads config in __init__.
We mock TransmissionAPI at the import site to avoid that side effect.
"""

import pytest
from unittest.mock import MagicMock, patch

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
        # enable is False, so client property won't try to create a client
        assert service.client is None


class TestTransmissionServiceNoClient:
    def test_set_alt_speed_no_client(self):
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        service._client = None

        result = service.set_alt_speed(True)
        assert result is False

    def test_get_status_not_connected(self):
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        service._client = None

        status = service.get_status()
        assert status["connected"] is False

    def test_test_connection_no_client(self):
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        service._client = None

        assert service.test_connection() is False


class TestTransmissionServiceWithMockClient:
    def test_set_alt_speed_success(self):
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        mock_client = MagicMock()
        service._client = mock_client

        result = service.set_alt_speed(True)

        assert result is True
        mock_client.set_alt_speed_enabled.assert_called_once_with(True)

    def test_get_status_connected(self):
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        mock_client = MagicMock()
        mock_client.get_session.return_value = TRANSMISSION_SESSION
        service._client = mock_client

        status = service.get_status()

        assert status["connected"] is True
        assert status["alt_speed_enabled"] is True
        assert status["version"] == "3.00"

    def test_test_connection_success(self):
        from src.services.transmission import TransmissionService

        service = TransmissionService()
        mock_client = MagicMock()
        mock_client.test_connection.return_value = True
        service._client = mock_client

        assert service.test_connection() is True
        mock_client.test_connection.assert_called_once()
