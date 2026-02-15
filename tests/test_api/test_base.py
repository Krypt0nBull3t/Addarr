"""
Tests for src/api/base.py -- BaseApiClient and APIError.
"""

import json
import pytest
import aiohttp
from aioresponses import aioresponses

from src.api.base import BaseApiClient, APIError


# ---------------------------------------------------------------------------
# Concrete subclass for testing the abstract BaseApiClient
# ---------------------------------------------------------------------------


class ConcreteClient(BaseApiClient):
    """Minimal concrete implementation for testing."""

    async def search(self, term):
        return await self._make_request(f"search?term={term}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    """Create a ConcreteClient backed by the mock radarr config."""
    return ConcreteClient("radarr")


# ---------------------------------------------------------------------------
# APIError
# ---------------------------------------------------------------------------


class TestAPIError:
    def test_api_error_attributes(self):
        err = APIError("something broke", status_code=422, response_text='{"detail":"bad"}')
        assert err.message == "something broke"
        assert err.status_code == 422
        assert err.response_text == '{"detail":"bad"}'
        assert str(err) == "something broke"


# ---------------------------------------------------------------------------
# BaseApiClient -- URL / headers / parsing
# ---------------------------------------------------------------------------


class TestBaseApiClient:
    def test_build_base_url_http(self, client):
        # Mock config has ssl=False for radarr
        url = client._build_base_url()
        assert url.startswith("http://")
        assert "localhost" in url
        assert "7878" in url

    def test_build_base_url_https(self, client):
        # Temporarily flip ssl to True
        original = client.config["server"]["ssl"]
        try:
            client.config["server"]["ssl"] = True
            url = client._build_base_url()
            assert url.startswith("https://")
            assert "localhost" in url
            assert "7878" in url
        finally:
            client.config["server"]["ssl"] = original

    def test_get_headers(self, client):
        headers = client._get_headers()
        assert headers["X-Api-Key"] == "test-radarr-key"
        assert headers["Content-Type"] == "application/json"

    # -- _parse_error_response ------------------------------------------------

    def test_parse_error_response_json_array(self, client):
        text = json.dumps([{"errorMessage": "some error"}])
        result = client._parse_error_response(text)
        assert result == "some error"

    def test_parse_error_response_already_exists(self, client):
        text = json.dumps([{"errorMessage": "This movie has already been added"}])
        result = client._parse_error_response(text, title="Fight Club")
        assert result == "Fight Club is already in your library"

    def test_parse_error_response_plain_text(self, client):
        result = client._parse_error_response("Internal Server Error")
        assert result == "Internal Server Error"

    def test_parse_error_response_invalid_json(self, client):
        """Lines 73-74: JSONDecodeError falls through to return raw text."""
        # Must start with "[" to enter the JSON parsing branch
        result = client._parse_error_response("[not valid json")
        assert result == "[not valid json"


# ---------------------------------------------------------------------------
# BaseApiClient -- async _make_request
# ---------------------------------------------------------------------------


class TestBaseApiClientAsync:
    @pytest.mark.asyncio
    async def test_make_request_success(self, client):
        payload = {"id": 1, "title": "Test"}
        with aioresponses() as m:
            m.get(
                "http://localhost:7878//api/v3/system/status",
                payload=payload,
                status=200,
            )
            success, data, error = await client._make_request("system/status")

        assert success is True
        assert data == payload
        assert error is None

    @pytest.mark.asyncio
    async def test_make_request_error(self, client):
        error_body = json.dumps([{"errorMessage": "bad request"}])
        with aioresponses() as m:
            m.get(
                "http://localhost:7878//api/v3/movie",
                body=error_body,
                status=400,
            )
            success, data, error = await client._make_request("movie")

        assert success is False
        assert data is None
        assert error == "bad request"

    @pytest.mark.asyncio
    async def test_make_request_already_exists_error(self, client):
        """Line 105: 'already' in error_message triggers info log path."""
        error_body = json.dumps([{"errorMessage": "This movie has already been added"}])
        with aioresponses() as m:
            m.get(
                "http://localhost:7878//api/v3/movie",
                body=error_body,
                status=400,
            )
            success, data, error = await client._make_request("movie", title="Fight Club")

        assert success is False
        assert data is None
        assert "already in your library" in error

    @pytest.mark.asyncio
    async def test_make_request_connection_error(self, client):
        with aioresponses() as m:
            m.get(
                "http://localhost:7878//api/v3/system/status",
                exception=aiohttp.ClientError("refused"),
            )
            success, data, error = await client._make_request("system/status")

        assert success is False
        assert data is None
        assert "Connection error:" in error

    @pytest.mark.asyncio
    async def test_make_request_unexpected_exception(self, client):
        """Lines 115-118: generic Exception in _make_request."""
        with aioresponses() as m:
            m.get(
                "http://localhost:7878//api/v3/system/status",
                exception=RuntimeError("something unexpected"),
            )
            success, data, error = await client._make_request("system/status")

        assert success is False
        assert data is None
        assert "Unexpected error:" in error


# ---------------------------------------------------------------------------
# BaseApiClient -- check_status
# ---------------------------------------------------------------------------


class TestBaseApiClientCheckStatus:
    @pytest.mark.asyncio
    async def test_check_status_success(self, client):
        """Line 130: check_status returns True when status_code is 200."""
        from unittest.mock import AsyncMock, MagicMock
        mock_response = MagicMock()
        mock_response.status_code = 200
        client.get = AsyncMock(return_value=mock_response)
        result = await client.check_status()
        assert result is True

    @pytest.mark.asyncio
    async def test_check_status_exception(self, client):
        """Lines 131-133: check_status catches exceptions and returns False."""
        # check_status calls self.get() which doesn't exist on BaseApiClient,
        # so it will raise AttributeError -> caught by except -> return False
        result = await client.check_status()
        assert result is False
