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
