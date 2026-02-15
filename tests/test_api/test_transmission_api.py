"""
Tests for src/api/transmission.py -- TransmissionAPI.

IMPORTANT: TransmissionAPI inherits from BaseApiClient but calls
super().__init__() without a service_name argument (known bug).
We patch BaseApiClient.__init__ to avoid the crash.

TransmissionAPI also does NOT implement the abstract ``search`` method,
so we clear ``__abstractmethods__`` on the class after import to allow
instantiation.

All methods under test are synchronous (using ``requests.post``).
"""

from unittest.mock import patch, MagicMock

import requests

from src.api.base import BaseApiClient

# Import TransmissionAPI at module level -- the class *definition* succeeds
# (ABCMeta only prevents *instantiation*, not definition).
from src.api.transmission import TransmissionAPI

# Remove abstract-method enforcement so we can instantiate it in tests.
TransmissionAPI.__abstractmethods__ = frozenset()


# ---------------------------------------------------------------------------
# Helper: create a TransmissionAPI instance safely
# ---------------------------------------------------------------------------


def _make_api(host="localhost", port=9091, username=None, password=None, ssl=False):
    """Instantiate TransmissionAPI with BaseApiClient.__init__ patched out."""
    with patch.object(BaseApiClient, "__init__", lambda self, *a, **kw: None):
        api = TransmissionAPI(
            host=host, port=port,
            username=username, password=password, ssl=ssl,
        )
    return api


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


class TestTransmissionInit:
    def test_init(self):
        api = _make_api(host="myhost", port=1234, ssl=False)
        assert api.host == "myhost"
        assert api.port == 1234
        assert api.base_url == "http://myhost:1234/transmission/rpc"

    def test_init_ssl(self):
        api = _make_api(host="myhost", port=443, ssl=True)
        assert api.base_url == "https://myhost:443/transmission/rpc"


# ---------------------------------------------------------------------------
# _get_auth
# ---------------------------------------------------------------------------


class TestTransmissionAuth:
    def test_get_auth_with_credentials(self):
        api = _make_api(username="admin", password="secret")
        auth = api._get_auth()
        assert auth == ("admin", "secret")

    def test_get_auth_without_credentials(self):
        api = _make_api()
        auth = api._get_auth()
        assert auth is None


# ---------------------------------------------------------------------------
# _make_request
# ---------------------------------------------------------------------------


class TestTransmissionMakeRequest:
    @patch("src.api.transmission.requests.post")
    def test_make_request_success(self, mock_post):
        api = _make_api()
        expected = {"result": "success", "arguments": {"version": "4.0.0"}}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = api._make_request("session-get", {})
        assert result == expected
        mock_post.assert_called_once()

    @patch("src.api.transmission.requests.post")
    def test_make_request_session_id_negotiation(self, mock_post):
        api = _make_api()

        # First call returns 409 with a session ID header
        resp_409 = MagicMock()
        resp_409.status_code = 409
        resp_409.headers = {"X-Transmission-Session-Id": "abc123"}

        # Second call succeeds
        resp_ok = MagicMock()
        resp_ok.status_code = 200
        resp_ok.json.return_value = {"result": "success"}
        resp_ok.raise_for_status.return_value = None

        mock_post.side_effect = [resp_409, resp_ok]

        result = api._make_request("session-get", {})
        assert result == {"result": "success"}
        assert api.session_id == "abc123"
        assert mock_post.call_count == 2


# ---------------------------------------------------------------------------
# get_session / set_alt_speed_enabled
# ---------------------------------------------------------------------------


class TestTransmissionDelegates:
    @patch("src.api.transmission.requests.post")
    def test_get_session(self, mock_post):
        api = _make_api()
        expected = {"result": "success", "arguments": {"version": "4.0.0"}}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = api.get_session()
        assert result == expected
        # Verify the RPC method was 'session-get'
        call_kwargs = mock_post.call_args
        assert call_kwargs[1]["json"]["method"] == "session-get"

    @patch("src.api.transmission.requests.post")
    def test_set_alt_speed_enabled(self, mock_post):
        api = _make_api()
        expected = {"result": "success", "arguments": {}}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = api.set_alt_speed_enabled(True)
        assert result == expected
        call_kwargs = mock_post.call_args
        payload = call_kwargs[1]["json"]
        assert payload["method"] == "session-set"
        assert payload["arguments"]["alt-speed-enabled"] is True


# ---------------------------------------------------------------------------
# test_connection
# ---------------------------------------------------------------------------


class TestTransmissionTestConnection:
    @patch("src.api.transmission.requests.post")
    def test_test_connection_success(self, mock_post):
        api = _make_api()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        assert api.test_connection() is True

    @patch("src.api.transmission.requests.post")
    def test_test_connection_failure(self, mock_post):
        api = _make_api()
        mock_post.side_effect = requests.exceptions.ConnectionError("refused")
        assert api.test_connection() is False
