"""Tests for src.setup.service_config module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.setup.service_config import (
    get_default_port,
    get_default_service_config,
    get_valid_service_config,
)


# ---------------------------------------------------------------------------
# get_default_port tests
# ---------------------------------------------------------------------------


class TestGetDefaultPort:
    """Tests for get_default_port()."""

    @pytest.mark.parametrize(
        "service,expected",
        [
            ("radarr", "7878"),
            ("sonarr", "8989"),
            ("lidarr", "8686"),
            ("transmission", "9091"),
            ("sabnzbd", "8090"),
        ],
    )
    def test_known_services(self, service, expected):
        """Each known service returns its default port."""
        assert get_default_port(service) == expected

    def test_unknown_service(self):
        """Unknown service returns fallback port 8090."""
        assert get_default_port("unknown_service") == "8090"


# ---------------------------------------------------------------------------
# get_default_service_config tests
# ---------------------------------------------------------------------------


class TestGetDefaultServiceConfig:
    """Tests for get_default_service_config()."""

    def test_radarr_has_minimum_availability(self):
        """Radarr config includes features.minimumAvailability."""
        config = get_default_service_config("radarr")
        assert config["features"]["minimumAvailability"] == "announced"
        assert config["features"]["search"] is True
        assert config["server"]["port"] == "7878"

    def test_sonarr_has_season_folder(self):
        """Sonarr config includes features.seasonFolder."""
        config = get_default_service_config("sonarr")
        assert config["features"]["seasonFolder"] is True
        assert config["server"]["port"] == "8989"

    def test_lidarr_has_metadata_profile(self):
        """Lidarr config includes metadataProfileId and album features."""
        config = get_default_service_config("lidarr")
        assert config["metadataProfileId"] == 1
        assert config["features"]["albumFolder"] is True
        assert config["features"]["monitorOption"] == "all"
        assert config["server"]["port"] == "8686"

    def test_transmission_flat_structure(self):
        """Transmission has flat config (no nested server/auth)."""
        config = get_default_service_config("transmission")
        assert config["enable"] is False
        assert config["onlyAdmin"] is True
        assert config["host"] == "localhost"
        assert config["authentication"] is False
        # Should NOT have nested server dict
        assert "server" not in config

    def test_sabnzbd_has_only_admin(self):
        """SABnzbd config includes onlyAdmin and nested server/auth."""
        config = get_default_service_config("sabnzbd")
        assert config["enable"] is False
        assert config["onlyAdmin"] is True
        assert config["server"]["addr"] == "localhost"
        assert config["server"]["port"] == 8090
        assert config["auth"]["apikey"] == ""

    def test_arr_common_fields(self):
        """All arr services share common config structure."""
        for service in ["radarr", "sonarr", "lidarr"]:
            config = get_default_service_config(service)
            assert config["enable"] is False
            assert config["server"]["addr"] == "localhost"
            assert config["auth"]["apikey"] == ""
            assert config["paths"]["excludedRootFolders"] == []
            assert config["quality"]["excludedProfiles"] == []
            assert config["tags"]["default"] == ["telegram"]
            assert config["adminRestrictions"] is False


# ---------------------------------------------------------------------------
# get_valid_service_config tests
# ---------------------------------------------------------------------------


def _mock_questionary_ask(return_value):
    """Helper: create a mock questionary question."""
    mock_q = MagicMock()
    mock_q.ask_async = AsyncMock(return_value=return_value)
    return mock_q


class TestGetValidServiceConfig:
    """Tests for get_valid_service_config()."""

    @pytest.mark.asyncio
    async def test_success_radarr(self):
        """Successful validation returns server/auth config."""
        with patch("src.setup.service_config.questionary") as mock_q, \
             patch("src.setup.service_config.validate_service_connection",
                   new_callable=AsyncMock, return_value=True), \
             patch("src.setup.service_config.get_valid_port",
                   new_callable=AsyncMock, return_value=7878):

            # text: addr
            mock_q.text.return_value = _mock_questionary_ask("192.168.1.10")
            # confirm: ssl=False
            mock_q.confirm.return_value = _mock_questionary_ask(False)
            # password: apikey
            mock_q.password.return_value = _mock_questionary_ask("my-api-key")

            result = await get_valid_service_config("radarr")

        assert result["server"]["addr"] == "192.168.1.10"
        assert result["server"]["port"] == 7878
        assert result["server"]["ssl"] is False
        assert result["auth"]["apikey"] == "my-api-key"
        # Non-sabnzbd should NOT have enable/onlyAdmin
        assert "enable" not in result

    @pytest.mark.asyncio
    async def test_success_sabnzbd(self):
        """SABnzbd success returns config with enable and onlyAdmin."""
        with patch("src.setup.service_config.questionary") as mock_q, \
             patch("src.setup.service_config.validate_service_connection",
                   new_callable=AsyncMock, return_value=True), \
             patch("src.setup.service_config.get_valid_port",
                   new_callable=AsyncMock, return_value=8090):

            mock_q.text.return_value = _mock_questionary_ask("localhost")
            mock_q.confirm.return_value = _mock_questionary_ask(False)
            mock_q.password.return_value = _mock_questionary_ask("sab-key")

            result = await get_valid_service_config("sabnzbd")

        assert result["enable"] is True
        assert result["onlyAdmin"] is True
        assert result["auth"]["apikey"] == "sab-key"

    @pytest.mark.asyncio
    async def test_retry_then_skip(self):
        """Failed validation → user declines retry → returns config with defaults."""
        with patch("src.setup.service_config.questionary") as mock_q, \
             patch("src.setup.service_config.validate_service_connection",
                   new_callable=AsyncMock, return_value=False), \
             patch("src.setup.service_config.get_valid_port",
                   new_callable=AsyncMock, return_value=7878):

            mock_q.text.return_value = _mock_questionary_ask("localhost")
            # confirm calls: ssl=False, retry=False
            confirm_mock = MagicMock()
            confirm_mock.ask_async = AsyncMock(side_effect=[False, False])
            mock_q.confirm.return_value = confirm_mock
            mock_q.password.return_value = _mock_questionary_ask("key")

            result = await get_valid_service_config("radarr")

        assert result["server"]["addr"] == "localhost"
        assert result["auth"]["apikey"] == "key"

    @pytest.mark.asyncio
    async def test_empty_addr_retries(self):
        """Empty server address triggers urlparse empty netloc, retries."""
        with patch("src.setup.service_config.questionary") as mock_q, \
             patch("src.setup.service_config.validate_service_connection",
                   new_callable=AsyncMock, return_value=True), \
             patch("src.setup.service_config.get_valid_port",
                   new_callable=AsyncMock, return_value=7878):

            # text: "" (empty, fails urlparse), then "localhost" (valid)
            text_mock = MagicMock()
            text_mock.ask_async = AsyncMock(side_effect=["", "localhost"])
            mock_q.text.return_value = text_mock
            mock_q.confirm.return_value = _mock_questionary_ask(False)
            mock_q.password.return_value = _mock_questionary_ask("key")

            result = await get_valid_service_config("radarr")

        assert result["server"]["addr"] == "localhost"

    @pytest.mark.asyncio
    async def test_urlparse_exception_retries(self):
        """urlparse exception triggers retry."""
        with patch("src.setup.service_config.questionary") as mock_q, \
             patch("src.setup.service_config.validate_service_connection",
                   new_callable=AsyncMock, return_value=True), \
             patch("src.setup.service_config.get_valid_port",
                   new_callable=AsyncMock, return_value=7878), \
             patch("src.setup.service_config.urlparse") as mock_urlparse:

            # First call raises, second call works normally
            from urllib.parse import ParseResult
            mock_urlparse.side_effect = [
                Exception("parse error"),
                ParseResult(
                    scheme="http", netloc="localhost",
                    path="", params="", query="", fragment=""
                ),
            ]

            text_mock = MagicMock()
            text_mock.ask_async = AsyncMock(
                side_effect=["bad\x00addr", "localhost"]
            )
            mock_q.text.return_value = text_mock
            mock_q.confirm.return_value = _mock_questionary_ask(False)
            mock_q.password.return_value = _mock_questionary_ask("key")

            result = await get_valid_service_config("radarr")

        assert result["server"]["addr"] == "localhost"

    @pytest.mark.asyncio
    async def test_transmission_no_apikey_prompt(self):
        """Transmission doesn't prompt for API key."""
        with patch("src.setup.service_config.questionary") as mock_q, \
             patch("src.setup.service_config.validate_service_connection",
                   new_callable=AsyncMock, return_value=True), \
             patch("src.setup.service_config.get_valid_port",
                   new_callable=AsyncMock, return_value=9091):

            mock_q.text.return_value = _mock_questionary_ask("localhost")
            mock_q.confirm.return_value = _mock_questionary_ask(False)

            result = await get_valid_service_config("transmission")

        assert result["auth"]["apikey"] == ""
        # password should not have been called
        mock_q.password.assert_not_called()
