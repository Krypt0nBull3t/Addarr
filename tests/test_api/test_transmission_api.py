"""
Tests for src/api/transmission.py -- TransmissionClient (async).

Uses aioresponses for HTTP mocking. TransmissionClient reads config from
the global config singleton (mocked via tests/conftest.py).
"""

import aiohttp
import pytest
from yarl import URL

from src.api.transmission import TransmissionClient


RPC_URL = "http://localhost:9091/transmission/rpc"
RPC_URL_KEY = ("POST", URL(RPC_URL))


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


# ---------------------------------------------------------------------------
# get_torrents
# ---------------------------------------------------------------------------


class TestGetTorrents:
    @pytest.mark.asyncio
    async def test_get_torrents_success(self, aio_mock, transmission_client):
        """get_torrents() returns parsed torrent list from torrent-get RPC."""
        expected = {
            "result": "success",
            "arguments": {
                "torrents": [
                    {
                        "id": 1,
                        "name": "Ubuntu ISO",
                        "status": 4,
                        "percentDone": 0.75,
                        "rateDownload": 1048576,
                        "eta": 3600,
                        "sizeWhenDone": 4294967296,
                        "totalSize": 4294967296,
                    }
                ]
            },
        }
        aio_mock.post(RPC_URL, payload=expected, status=200)

        result = await transmission_client.get_torrents()
        assert result == expected

    @pytest.mark.asyncio
    async def test_get_torrents_sends_fields(self, aio_mock, transmission_client):
        """get_torrents() requests specific torrent fields in payload."""
        aio_mock.post(
            RPC_URL,
            payload={"result": "success", "arguments": {"torrents": []}},
            status=200,
        )

        await transmission_client.get_torrents()

        # Verify the request payload included the fields argument
        call = aio_mock.requests[RPC_URL_KEY]
        request_body = call[0].kwargs["json"]
        assert request_body["method"] == "torrent-get"
        assert "fields" in request_body["arguments"]
        expected_fields = {
            "id", "name", "status", "percentDone",
            "rateDownload", "eta", "sizeWhenDone", "totalSize",
        }
        assert set(request_body["arguments"]["fields"]) >= expected_fields


# ---------------------------------------------------------------------------
# pause_torrent / resume_torrent / stop_all / start_all
# ---------------------------------------------------------------------------


class TestTorrentControl:
    @pytest.mark.asyncio
    async def test_pause_torrent(self, aio_mock, transmission_client):
        """pause_torrent(id) sends torrent-stop with ids: [id]."""
        aio_mock.post(
            RPC_URL,
            payload={"result": "success", "arguments": {}},
            status=200,
        )

        result = await transmission_client.pause_torrent(42)
        assert result["result"] == "success"

        call = aio_mock.requests[RPC_URL_KEY]
        body = call[0].kwargs["json"]
        assert body["method"] == "torrent-stop"
        assert body["arguments"]["ids"] == [42]

    @pytest.mark.asyncio
    async def test_resume_torrent(self, aio_mock, transmission_client):
        """resume_torrent(id) sends torrent-start with ids: [id]."""
        aio_mock.post(
            RPC_URL,
            payload={"result": "success", "arguments": {}},
            status=200,
        )

        result = await transmission_client.resume_torrent(7)
        assert result["result"] == "success"

        call = aio_mock.requests[RPC_URL_KEY]
        body = call[0].kwargs["json"]
        assert body["method"] == "torrent-start"
        assert body["arguments"]["ids"] == [7]

    @pytest.mark.asyncio
    async def test_stop_all(self, aio_mock, transmission_client):
        """stop_all() sends torrent-stop with no ids argument."""
        aio_mock.post(
            RPC_URL,
            payload={"result": "success", "arguments": {}},
            status=200,
        )

        result = await transmission_client.stop_all()
        assert result["result"] == "success"

        call = aio_mock.requests[RPC_URL_KEY]
        body = call[0].kwargs["json"]
        assert body["method"] == "torrent-stop"
        assert "ids" not in body["arguments"]

    @pytest.mark.asyncio
    async def test_start_all(self, aio_mock, transmission_client):
        """start_all() sends torrent-start with no ids argument."""
        aio_mock.post(
            RPC_URL,
            payload={"result": "success", "arguments": {}},
            status=200,
        )

        result = await transmission_client.start_all()
        assert result["result"] == "success"

        call = aio_mock.requests[RPC_URL_KEY]
        body = call[0].kwargs["json"]
        assert body["method"] == "torrent-start"
        assert "ids" not in body["arguments"]
