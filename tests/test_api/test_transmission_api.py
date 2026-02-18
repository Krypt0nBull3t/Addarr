"""
Tests for src/api/transmission.py -- TransmissionClient (async).

Uses aioresponses for HTTP mocking. TransmissionClient reads config from
the global config singleton (mocked via tests/conftest.py).
"""

import aiohttp
import pytest

from src.api.transmission import TransmissionClient


RPC_URL = "http://localhost:9091/transmission/rpc"


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


class TestTransmissionInit:
    def test_init_builds_url(self, transmission_client):
        assert transmission_client.rpc_url == "http://localhost:9091/transmission/rpc"

    def test_init_ssl_url(self):
        """When ssl=True in config, URL uses https."""
        from tests.conftest import _mock_config

        original = _mock_config._config["transmission"]["ssl"]
        _mock_config._config["transmission"]["ssl"] = True
        try:
            client = TransmissionClient()
            assert client.rpc_url.startswith("https://")
        finally:
            _mock_config._config["transmission"]["ssl"] = original

    def test_init_with_auth(self):
        """When username and password are set, _auth is an aiohttp.BasicAuth."""
        from tests.conftest import _mock_config

        orig_user = _mock_config._config["transmission"]["username"]
        orig_pass = _mock_config._config["transmission"]["password"]
        _mock_config._config["transmission"]["username"] = "admin"
        _mock_config._config["transmission"]["password"] = "secret"
        try:
            client = TransmissionClient()
            assert client._auth is not None
            assert isinstance(client._auth, aiohttp.BasicAuth)
        finally:
            _mock_config._config["transmission"]["username"] = orig_user
            _mock_config._config["transmission"]["password"] = orig_pass

    def test_init_no_auth(self, transmission_client):
        """When no credentials, _auth is None."""
        assert transmission_client._auth is None


# ---------------------------------------------------------------------------
# _make_request
# ---------------------------------------------------------------------------


class TestTransmissionMakeRequest:
    @pytest.mark.asyncio
    async def test_make_request_success(self, aio_mock, transmission_client):
        expected = {"result": "success", "arguments": {"version": "4.0.0"}}
        aio_mock.post(RPC_URL, payload=expected, status=200)

        result = await transmission_client._make_request("session-get")
        assert result == expected

    @pytest.mark.asyncio
    async def test_session_id_negotiation(self, aio_mock, transmission_client):
        """409 response triggers retry with session ID from header."""
        aio_mock.post(
            RPC_URL, status=409,
            headers={"X-Transmission-Session-Id": "abc123"},
        )
        aio_mock.post(
            RPC_URL,
            payload={"result": "success"},
            status=200,
        )

        result = await transmission_client._make_request("session-get")
        assert result == {"result": "success"}
        assert transmission_client._session_id == "abc123"

    @pytest.mark.asyncio
    async def test_connection_error(self, aio_mock, transmission_client):
        """aiohttp.ClientError is raised on connection failure."""
        aio_mock.post(RPC_URL, exception=aiohttp.ClientError("refused"))

        with pytest.raises(aiohttp.ClientError):
            await transmission_client._make_request("session-get")

    @pytest.mark.asyncio
    async def test_double_409_raises(self, aio_mock, transmission_client):
        """Two consecutive 409 responses exhaust retries and raise."""
        aio_mock.post(
            RPC_URL, status=409,
            headers={"X-Transmission-Session-Id": "id1"},
        )
        aio_mock.post(
            RPC_URL, status=409,
            headers={"X-Transmission-Session-Id": "id2"},
        )

        with pytest.raises(aiohttp.ClientError, match="negotiation failed"):
            await transmission_client._make_request("session-get")


# ---------------------------------------------------------------------------
# get_session / set_alt_speed_enabled
# ---------------------------------------------------------------------------


class TestTransmissionDelegates:
    @pytest.mark.asyncio
    async def test_get_session(self, aio_mock, transmission_client):
        expected = {"result": "success", "arguments": {"version": "4.0.0"}}
        aio_mock.post(RPC_URL, payload=expected, status=200)

        result = await transmission_client.get_session()
        assert result == expected

    @pytest.mark.asyncio
    async def test_set_alt_speed_enabled_true(self, aio_mock, transmission_client):
        expected = {"result": "success", "arguments": {}}
        aio_mock.post(RPC_URL, payload=expected, status=200)

        result = await transmission_client.set_alt_speed_enabled(True)
        assert result == expected

    @pytest.mark.asyncio
    async def test_set_alt_speed_enabled_false(self, aio_mock, transmission_client):
        expected = {"result": "success", "arguments": {}}
        aio_mock.post(RPC_URL, payload=expected, status=200)

        result = await transmission_client.set_alt_speed_enabled(False)
        assert result == expected


# ---------------------------------------------------------------------------
# test_connection
# ---------------------------------------------------------------------------


class TestTransmissionTestConnection:
    @pytest.mark.asyncio
    async def test_connection_success(self, aio_mock, transmission_client):
        aio_mock.post(
            RPC_URL,
            payload={"result": "success"},
            status=200,
        )
        assert await transmission_client.test_connection() is True

    @pytest.mark.asyncio
    async def test_connection_failure(self, aio_mock, transmission_client):
        aio_mock.post(RPC_URL, exception=aiohttp.ClientError("refused"))
        assert await transmission_client.test_connection() is False
