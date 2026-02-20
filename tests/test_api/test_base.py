"""
Tests for src/api/base.py -- BaseApiClient and APIError.
"""

import asyncio
import json
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
import aiohttp
from aioresponses import aioresponses

from src.api.base import BaseApiClient, APIError, filter_root_folders


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


@pytest.fixture(autouse=True)
async def cleanup_session(client):
    """Close the client session after each test to prevent mock leakage."""
    yield
    await client.close()


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
# filter_root_folders
# ---------------------------------------------------------------------------


class TestFilterRootFolders:
    def test_no_exclusions_returns_all(self):
        paths = ["/movies", "/movies2"]
        cfg = {"paths": {"excludedRootFolders": []}}
        assert filter_root_folders(paths, cfg) == ["/movies", "/movies2"]

    def test_no_paths_config_returns_all(self):
        paths = ["/movies", "/movies2"]
        assert filter_root_folders(paths, {}) == ["/movies", "/movies2"]

    def test_full_path_exclusion(self):
        paths = ["/data/movies", "/data/movies2"]
        cfg = {
            "paths": {
                "excludedRootFolders": ["/data/movies2"],
                "narrowRootFolderNames": False,
            }
        }
        assert filter_root_folders(paths, cfg) == ["/data/movies"]

    def test_narrow_basename_exclusion(self):
        paths = ["/data/movies", "/data/movies2"]
        cfg = {
            "paths": {
                "excludedRootFolders": ["movies2"],
                "narrowRootFolderNames": True,
            }
        }
        assert filter_root_folders(paths, cfg) == ["/data/movies"]

    def test_narrow_handles_trailing_slash(self):
        paths = ["/data/movies/", "/data/movies2/"]
        cfg = {
            "paths": {
                "excludedRootFolders": ["movies2"],
                "narrowRootFolderNames": True,
            }
        }
        result = filter_root_folders(paths, cfg)
        assert "/data/movies/" in result
        assert "/data/movies2/" not in result


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
        url = "http://localhost:7878//api/v3/system/status"
        with aioresponses() as m:
            # 3 mocks needed: initial attempt + 2 retries (default max_retries=2)
            for _ in range(3):
                m.get(url, exception=aiohttp.ClientError("refused"))
            with patch("asyncio.sleep", new_callable=AsyncMock):
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


# ---------------------------------------------------------------------------
# BaseApiClient -- Session reuse
# ---------------------------------------------------------------------------


class TestBaseApiClientSession:
    def test_session_none_initially(self, client):
        """Session should be None before any request is made."""
        assert client._session is None

    @pytest.mark.asyncio
    async def test_session_created_lazily(self, client):
        """_get_session() should create a session on first call."""
        session = await client._get_session()
        assert session is not None
        assert isinstance(session, aiohttp.ClientSession)

    @pytest.mark.asyncio
    async def test_session_reused_across_calls(self, client):
        """Subsequent _get_session() calls return the same session."""
        session1 = await client._get_session()
        session2 = await client._get_session()
        assert session1 is session2

    @pytest.mark.asyncio
    async def test_close_closes_and_nullifies(self, client):
        """close() should close the session and set it to None."""
        await client._get_session()
        assert client._session is not None
        await client.close()
        assert client._session is None

    @pytest.mark.asyncio
    async def test_close_idempotent(self, client):
        """Calling close() twice should not raise."""
        await client._get_session()
        await client.close()
        await client.close()  # should not raise

    @pytest.mark.asyncio
    async def test_close_without_session(self, client):
        """close() on a fresh client (no session) should not raise."""
        await client.close()  # should not raise

    @pytest.mark.asyncio
    async def test_new_session_after_close(self, client):
        """After close(), _get_session() should create a fresh session."""
        session1 = await client._get_session()
        await client.close()
        session2 = await client._get_session()
        assert session2 is not None
        assert session1 is not session2

    @pytest.mark.asyncio
    async def test_session_reused_across_requests(self, client):
        """_make_request() should reuse the same session for multiple calls."""
        with aioresponses() as m:
            m.get(
                "http://localhost:7878//api/v3/system/status",
                payload={"status": "ok"},
                status=200,
            )
            m.get(
                "http://localhost:7878//api/v3/system/status",
                payload={"status": "ok"},
                status=200,
            )
            await client._make_request("system/status")
            session_after_first = client._session
            await client._make_request("system/status")
            session_after_second = client._session
        assert session_after_first is session_after_second


# ---------------------------------------------------------------------------
# BaseApiClient -- Timeout
# ---------------------------------------------------------------------------


class TestBaseApiClientTimeout:
    def test_default_timeout_value(self, client):
        """Client should have DEFAULT_TIMEOUT of 30 seconds."""
        assert client.request_timeout == 30

    @pytest.mark.asyncio
    async def test_default_timeout_applied_to_session(self, client):
        """Session should be created with the default timeout."""
        session = await client._get_session()
        assert session.timeout.total == 30

    def test_custom_instance_timeout(self):
        """Client created with custom timeout should respect it."""
        client = ConcreteClient("radarr", request_timeout=10)
        assert client.request_timeout == 10

    @pytest.mark.asyncio
    async def test_custom_timeout_applied_to_session(self):
        """Session should use the custom instance timeout."""
        client = ConcreteClient("radarr", request_timeout=15)
        session = await client._get_session()
        assert session.timeout.total == 15
        await client.close()

    @pytest.mark.asyncio
    async def test_per_request_timeout_override(self, client):
        """Per-request timeout kwarg should override instance default."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value='{"ok": true}')
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        session = await client._get_session()
        with patch.object(session, "request", return_value=mock_response) as mock_req:
            await client._make_request("system/status", timeout=5)
            call_kwargs = mock_req.call_args
            timeout_arg = call_kwargs.kwargs.get("timeout") or call_kwargs[1].get("timeout")
            assert timeout_arg is not None
            assert timeout_arg.total == 5


# ---------------------------------------------------------------------------
# BaseApiClient -- Retry logic
# ---------------------------------------------------------------------------

URL = "http://localhost:7878//api/v3/system/status"


class TestBaseApiClientRetry:
    @pytest.mark.asyncio
    async def test_retry_on_500_then_success(self, client):
        """500 triggers retry; second attempt succeeds."""
        with aioresponses() as m:
            m.get(URL, status=500, body="Internal Server Error")
            m.get(URL, payload={"ok": True}, status=200)
            with patch("asyncio.sleep", new_callable=AsyncMock):
                success, data, error = await client._make_request("system/status")
        assert success is True
        assert data == {"ok": True}

    @pytest.mark.asyncio
    async def test_retry_on_502_then_success(self, client):
        """502 triggers retry; second attempt succeeds."""
        with aioresponses() as m:
            m.get(URL, status=502, body="Bad Gateway")
            m.get(URL, payload={"ok": True}, status=200)
            with patch("asyncio.sleep", new_callable=AsyncMock):
                success, data, error = await client._make_request("system/status")
        assert success is True
        assert data == {"ok": True}

    @pytest.mark.asyncio
    async def test_retry_on_connection_error_then_success(self, client):
        """aiohttp.ClientError triggers retry; second attempt succeeds."""
        with aioresponses() as m:
            m.get(URL, exception=aiohttp.ClientError("refused"))
            m.get(URL, payload={"ok": True}, status=200)
            with patch("asyncio.sleep", new_callable=AsyncMock):
                success, data, error = await client._make_request("system/status")
        assert success is True
        assert data == {"ok": True}

    @pytest.mark.asyncio
    async def test_retry_on_timeout_error_then_success(self, client):
        """asyncio.TimeoutError triggers retry; second attempt succeeds."""
        with aioresponses() as m:
            m.get(URL, exception=asyncio.TimeoutError())
            m.get(URL, payload={"ok": True}, status=200)
            with patch("asyncio.sleep", new_callable=AsyncMock):
                success, data, error = await client._make_request("system/status")
        assert success is True
        assert data == {"ok": True}

    @pytest.mark.asyncio
    async def test_no_retry_on_400(self, client):
        """400 is a client error — should NOT retry."""
        with aioresponses() as m:
            m.get(URL, status=400, body="Bad Request")
            success, data, error = await client._make_request("system/status")
        assert success is False
        assert "Bad Request" in error

    @pytest.mark.asyncio
    async def test_no_retry_on_404(self, client):
        """404 is a client error — should NOT retry."""
        with aioresponses() as m:
            m.get(URL, status=404, body="Not Found")
            success, data, error = await client._make_request("system/status")
        assert success is False
        assert "Not Found" in error

    @pytest.mark.asyncio
    async def test_all_retries_exhausted_5xx(self, client):
        """All 3 attempts fail with 503 — returns error after exhaustion."""
        with aioresponses() as m:
            for _ in range(3):
                m.get(URL, status=503, body="Service Unavailable")
            with patch("asyncio.sleep", new_callable=AsyncMock):
                success, data, error = await client._make_request("system/status")
        assert success is False
        assert data is None
        assert "Service Unavailable" in error

    @pytest.mark.asyncio
    async def test_all_retries_exhausted_connection_error(self, client):
        """All 3 attempts fail with ClientError — returns connection error."""
        with aioresponses() as m:
            for _ in range(3):
                m.get(URL, exception=aiohttp.ClientError("refused"))
            with patch("asyncio.sleep", new_callable=AsyncMock):
                success, data, error = await client._make_request("system/status")
        assert success is False
        assert "Connection error:" in error

    @pytest.mark.asyncio
    async def test_respects_max_retries_setting(self, client):
        """max_retries=1 means 2 total attempts."""
        with aioresponses() as m:
            m.get(URL, status=500, body="Internal Server Error")
            m.get(URL, status=500, body="Internal Server Error")
            with patch("asyncio.sleep", new_callable=AsyncMock):
                success, data, error = await client._make_request(
                    "system/status", max_retries=1
                )
        assert success is False
        assert "Internal Server Error" in error

    @pytest.mark.asyncio
    async def test_retry_disabled_when_max_retries_zero(self, client):
        """max_retries=0 means only 1 attempt, no retries."""
        with aioresponses() as m:
            m.get(URL, status=500, body="Internal Server Error")
            success, data, error = await client._make_request(
                "system/status", max_retries=0
            )
        assert success is False
        assert "Internal Server Error" in error

    @pytest.mark.asyncio
    async def test_per_request_max_retries_override(self, client):
        """Per-request max_retries overrides instance default."""
        with aioresponses() as m:
            m.get(URL, status=500, body="err")
            m.get(URL, payload={"ok": True}, status=200)
            with patch("asyncio.sleep", new_callable=AsyncMock):
                success, data, error = await client._make_request(
                    "system/status", max_retries=1
                )
        assert success is True
        assert data == {"ok": True}

    @pytest.mark.asyncio
    async def test_exponential_backoff_sleep_values(self, client):
        """Verify backoff sleeps: 1s then 2s (1 * 2^attempt)."""
        with aioresponses() as m:
            for _ in range(3):
                m.get(URL, status=500, body="err")
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                await client._make_request("system/status")
        # 2 retries = 2 sleep calls: sleep(1.0), sleep(2.0)
        assert mock_sleep.call_count == 2
        assert mock_sleep.call_args_list[0][0][0] == 1.0
        assert mock_sleep.call_args_list[1][0][0] == 2.0

    @pytest.mark.asyncio
    async def test_no_retry_on_generic_exception(self, client):
        """Generic Exception (not ClientError/TimeoutError) should NOT retry."""
        with aioresponses() as m:
            m.get(URL, exception=RuntimeError("unexpected"))
            success, data, error = await client._make_request("system/status")
        assert success is False
        assert "Unexpected error:" in error
