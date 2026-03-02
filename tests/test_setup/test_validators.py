"""Tests for src.setup.validators module."""

import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import aiohttp
import pytest
from aioresponses import aioresponses

from src.setup.validators import validate_service_connection, get_valid_port


# ---------------------------------------------------------------------------
# validate_service_connection tests
# ---------------------------------------------------------------------------


class TestValidateServiceConnection:
    """Tests for validate_service_connection()."""

    @pytest.mark.asyncio
    async def test_radarr_success(self):
        """Successful connection to radarr returns True."""
        with aioresponses() as m:
            m.get(
                "http://localhost:7878/api/v3/system/status",
                payload={"version": "4.0.0"},
            )
            result = await validate_service_connection(
                "radarr", "localhost", 7878, False, "test-api-key"
            )
        assert result is True

    @pytest.mark.asyncio
    async def test_sonarr_success(self):
        """Successful connection to sonarr returns True."""
        with aioresponses() as m:
            m.get(
                "http://localhost:8989/api/v3/system/status",
                payload={"version": "3.0.0"},
            )
            result = await validate_service_connection(
                "sonarr", "localhost", 8989, False, "test-api-key"
            )
        assert result is True

    @pytest.mark.asyncio
    async def test_lidarr_success(self):
        """Successful connection to lidarr (v1 API) returns True."""
        with aioresponses() as m:
            m.get(
                "http://localhost:8686/api/v1/system/status",
                payload={"version": "1.0.0"},
            )
            result = await validate_service_connection(
                "lidarr", "localhost", 8686, False, "test-api-key"
            )
        assert result is True

    @pytest.mark.asyncio
    async def test_connection_timeout(self):
        """TimeoutError returns False."""
        with aioresponses() as m:
            m.get(
                "http://localhost:7878/api/v3/system/status",
                exception=asyncio.TimeoutError(),
            )
            result = await validate_service_connection(
                "radarr", "localhost", 7878, False, "key"
            )
        assert result is False

    @pytest.mark.asyncio
    async def test_connection_client_error(self):
        """aiohttp.ClientError returns False."""
        with aioresponses() as m:
            m.get(
                "http://localhost:7878/api/v3/system/status",
                exception=aiohttp.ClientError("connection refused"),
            )
            result = await validate_service_connection(
                "radarr", "localhost", 7878, False, "key"
            )
        assert result is False

    @pytest.mark.asyncio
    async def test_bad_status_code(self):
        """Non-200 status returns False for arr services."""
        with aioresponses() as m:
            m.get(
                "http://localhost:7878/api/v3/system/status",
                status=401,
            )
            result = await validate_service_connection(
                "radarr", "localhost", 7878, False, "bad-key"
            )
        assert result is False

    @pytest.mark.asyncio
    async def test_response_missing_expected_keys(self):
        """200 response without expected keys returns False."""
        with aioresponses() as m:
            m.get(
                "http://localhost:7878/api/v3/system/status",
                payload={"unexpected": "data"},
            )
            result = await validate_service_connection(
                "radarr", "localhost", 7878, False, "key"
            )
        assert result is False

    @pytest.mark.asyncio
    async def test_transmission_409_success(self):
        """Transmission 409 (session ID challenge) counts as success."""
        with aioresponses() as m:
            m.get(
                "http://localhost:9091/transmission/rpc",
                status=409,
            )
            result = await validate_service_connection(
                "transmission", "localhost", 9091, False
            )
        assert result is True

    @pytest.mark.asyncio
    async def test_transmission_500_failure(self):
        """Transmission 500 is not in expected_status list."""
        with aioresponses() as m:
            m.get(
                "http://localhost:9091/transmission/rpc",
                status=500,
            )
            result = await validate_service_connection(
                "transmission", "localhost", 9091, False
            )
        assert result is False

    @pytest.mark.asyncio
    async def test_unknown_service_returns_false(self):
        """Unknown service name returns False immediately."""
        result = await validate_service_connection(
            "unknown_service", "localhost", 8080, False
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_invalid_json_response(self):
        """200 response with invalid JSON body returns False."""
        with aioresponses() as m:
            m.get(
                "http://localhost:7878/api/v3/system/status",
                body="not valid json{{{",
                content_type="application/json",
            )
            result = await validate_service_connection(
                "radarr", "localhost", 7878, False, "key"
            )
        assert result is False

    @pytest.mark.asyncio
    async def test_unexpected_exception(self):
        """Generic unexpected exception returns False."""
        with aioresponses() as m:
            m.get(
                "http://localhost:7878/api/v3/system/status",
                exception=RuntimeError("something unexpected"),
            )
            result = await validate_service_connection(
                "radarr", "localhost", 7878, False, "key"
            )
        assert result is False

    @pytest.mark.asyncio
    async def test_ssl_uses_https(self):
        """When ssl=True, URL uses https protocol."""
        with aioresponses() as m:
            m.get(
                "https://localhost:7878/api/v3/system/status",
                payload={"version": "4.0.0"},
            )
            result = await validate_service_connection(
                "radarr", "localhost", 7878, True, "key"
            )
        assert result is True


# ---------------------------------------------------------------------------
# get_valid_port tests
# ---------------------------------------------------------------------------


class TestGetValidPort:
    """Tests for get_valid_port()."""

    @pytest.mark.asyncio
    async def test_valid_port_input(self):
        """Valid port string returns integer."""
        mock_question = MagicMock()
        mock_question.ask_async = AsyncMock(return_value="8989")
        with patch("src.setup.validators.questionary") as mock_q:
            mock_q.text.return_value = mock_question
            result = await get_valid_port("Enter port:", "8989")
        assert result == 8989

    @pytest.mark.asyncio
    async def test_invalid_then_valid(self):
        """Non-numeric input retries until valid port given."""
        mock_question = MagicMock()
        mock_question.ask_async = AsyncMock(side_effect=["abc", "8989"])
        with patch("src.setup.validators.questionary") as mock_q:
            mock_q.text.return_value = mock_question
            result = await get_valid_port("Enter port:", "8989")
        assert result == 8989
        assert mock_question.ask_async.call_count == 2

    @pytest.mark.asyncio
    async def test_out_of_range_then_valid(self):
        """Port outside 1-65535 retries until valid port given."""
        mock_question = MagicMock()
        mock_question.ask_async = AsyncMock(side_effect=["99999", "443"])
        with patch("src.setup.validators.questionary") as mock_q:
            mock_q.text.return_value = mock_question
            result = await get_valid_port("Enter port:", "443")
        assert result == 443
        assert mock_question.ask_async.call_count == 2

    @pytest.mark.asyncio
    async def test_zero_port_rejected(self):
        """Port 0 is out of range, retries."""
        mock_question = MagicMock()
        mock_question.ask_async = AsyncMock(side_effect=["0", "80"])
        with patch("src.setup.validators.questionary") as mock_q:
            mock_q.text.return_value = mock_question
            result = await get_valid_port("Enter port:", "80")
        assert result == 80
