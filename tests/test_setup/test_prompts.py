"""Tests for src.setup.prompts module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.setup.prompts import (
    select_services,
    configure_language,
    configure_telegram,
    configure_access_control,
    configure_logging,
    configure_arr_features,
    configure_required_value,
)


def _mock_questionary_ask(return_value):
    """Helper: create a mock questionary question that returns a value on ask_async."""
    mock_q = MagicMock()
    mock_q.ask_async = AsyncMock(return_value=return_value)
    return mock_q


# ---------------------------------------------------------------------------
# select_services tests
# ---------------------------------------------------------------------------


class TestSelectServices:
    """Tests for select_services()."""

    @pytest.mark.asyncio
    async def test_media_only(self):
        """Selecting media services only, declining download clients."""
        with patch("src.setup.prompts.questionary") as mock_q:
            # First checkbox: select radarr
            mock_q.checkbox.return_value = _mock_questionary_ask(["radarr"])
            mock_q.Choice = MagicMock(side_effect=lambda name, value: value)
            # Confirm: decline download clients
            mock_q.confirm.return_value = _mock_questionary_ask(False)

            result = await select_services()

        assert result == ["radarr"]

    @pytest.mark.asyncio
    async def test_with_download_clients(self):
        """Selecting media services + download clients."""
        with patch("src.setup.prompts.questionary") as mock_q:
            mock_q.Choice = MagicMock(side_effect=lambda name, value: value)

            # First checkbox: sonarr
            # Confirm: yes to download clients
            # Second checkbox: transmission
            checkbox_mock = MagicMock()
            checkbox_mock.ask_async = AsyncMock(
                side_effect=[["sonarr"], ["transmission"]]
            )
            mock_q.checkbox.return_value = checkbox_mock
            mock_q.confirm.return_value = _mock_questionary_ask(True)

            result = await select_services()

        assert result == ["sonarr", "transmission"]

    @pytest.mark.asyncio
    async def test_download_client_none_skipped(self):
        """Selecting 'none' for download clients returns empty list for clients."""
        with patch("src.setup.prompts.questionary") as mock_q:
            mock_q.Choice = MagicMock(side_effect=lambda name, value: value)

            # First checkbox: radarr
            # Confirm: yes to download clients
            # Second checkbox: "none"
            checkbox_mock = MagicMock()
            checkbox_mock.ask_async = AsyncMock(
                side_effect=[["radarr"], ["none"]]
            )
            mock_q.checkbox.return_value = checkbox_mock
            mock_q.confirm.return_value = _mock_questionary_ask(True)

            result = await select_services()

        # Only media service, no download clients
        assert result == ["radarr"]

    @pytest.mark.asyncio
    async def test_empty_retries(self):
        """Empty selection retries until at least one service selected."""
        with patch("src.setup.prompts.questionary") as mock_q:
            mock_q.Choice = MagicMock(side_effect=lambda name, value: value)

            # First checkbox: empty, second: radarr
            checkbox_mock = MagicMock()
            checkbox_mock.ask_async = AsyncMock(
                side_effect=[[], ["radarr"]]
            )
            mock_q.checkbox.return_value = checkbox_mock
            mock_q.confirm.return_value = _mock_questionary_ask(False)

            result = await select_services()

        assert result == ["radarr"]


# ---------------------------------------------------------------------------
# configure_language tests
# ---------------------------------------------------------------------------


class TestConfigureLanguage:
    """Tests for configure_language()."""

    @pytest.mark.asyncio
    async def test_returns_selected_language(self):
        """Returns the language value selected by user."""
        with patch("src.setup.prompts.questionary") as mock_q:
            mock_q.select.return_value = _mock_questionary_ask("en-us")

            result = await configure_language()

        assert result == "en-us"

    @pytest.mark.asyncio
    async def test_returns_non_english_language(self):
        """Returns non-English language value."""
        with patch("src.setup.prompts.questionary") as mock_q:
            mock_q.select.return_value = _mock_questionary_ask("de-de")

            result = await configure_language()

        assert result == "de-de"


# ---------------------------------------------------------------------------
# configure_telegram tests
# ---------------------------------------------------------------------------


class TestConfigureTelegram:
    """Tests for configure_telegram()."""

    @pytest.mark.asyncio
    async def test_returns_dict_with_token_and_password(self):
        """Returns dict with token and password keys."""
        with patch("src.setup.prompts.questionary") as mock_q:
            mock_q.password.return_value = _mock_questionary_ask("my-token")
            # password is called twice: token then password
            password_mock = MagicMock()
            password_mock.ask_async = AsyncMock(
                side_effect=["bot-token-123", "chat-password"]
            )
            mock_q.password.return_value = password_mock

            result = await configure_telegram()

        assert result == {"token": "bot-token-123", "password": "chat-password"}


# ---------------------------------------------------------------------------
# configure_access_control tests
# ---------------------------------------------------------------------------


class TestConfigureAccessControl:
    """Tests for configure_access_control()."""

    @pytest.mark.asyncio
    async def test_with_allowlist(self):
        """Enables allowlist with admin and allowed user IDs."""
        with patch("src.setup.prompts.questionary") as mock_q:
            # confirm calls: enableAdmin=True, enableAllowlist=True
            confirm_mock = MagicMock()
            confirm_mock.ask_async = AsyncMock(side_effect=[True, True])
            mock_q.confirm.return_value = confirm_mock

            # text calls: admin ID "111", empty, allowed user "222", empty
            text_mock = MagicMock()
            text_mock.ask_async = AsyncMock(
                side_effect=["111", "", "222", ""]
            )
            mock_q.text.return_value = text_mock

            result = await configure_access_control()

        assert result["security"]["enableAdmin"] is True
        assert result["security"]["enableAllowlist"] is True
        assert result["admins"] == [111]
        assert result["allow_list"] == [222]

    @pytest.mark.asyncio
    async def test_invalid_admin_id_retries(self):
        """Non-numeric admin ID is rejected, then valid ID accepted."""
        with patch("src.setup.prompts.questionary") as mock_q:
            confirm_mock = MagicMock()
            confirm_mock.ask_async = AsyncMock(side_effect=[True, False])
            mock_q.confirm.return_value = confirm_mock

            # text: "abc" (invalid), "111" (valid), "" (done)
            text_mock = MagicMock()
            text_mock.ask_async = AsyncMock(side_effect=["abc", "111", ""])
            mock_q.text.return_value = text_mock

            result = await configure_access_control()

        assert result["admins"] == [111]

    @pytest.mark.asyncio
    async def test_invalid_allowed_user_id_retries(self):
        """Non-numeric allowed user ID is rejected, then valid ID accepted."""
        with patch("src.setup.prompts.questionary") as mock_q:
            confirm_mock = MagicMock()
            confirm_mock.ask_async = AsyncMock(side_effect=[True, True])
            mock_q.confirm.return_value = confirm_mock

            # text: admin "111", "" (done admins),
            #        "xyz" (invalid user), "222" (valid user), "" (done)
            text_mock = MagicMock()
            text_mock.ask_async = AsyncMock(
                side_effect=["111", "", "xyz", "222", ""]
            )
            mock_q.text.return_value = text_mock

            result = await configure_access_control()

        assert result["admins"] == [111]
        assert result["allow_list"] == [222]

    @pytest.mark.asyncio
    async def test_without_allowlist(self):
        """Disabling allowlist skips allowed users prompt."""
        with patch("src.setup.prompts.questionary") as mock_q:
            # confirm: enableAdmin=True, enableAllowlist=False
            confirm_mock = MagicMock()
            confirm_mock.ask_async = AsyncMock(side_effect=[True, False])
            mock_q.confirm.return_value = confirm_mock

            # text: admin ID "111", empty (no allowed user prompts)
            text_mock = MagicMock()
            text_mock.ask_async = AsyncMock(side_effect=["111", ""])
            mock_q.text.return_value = text_mock

            result = await configure_access_control()

        assert result["security"]["enableAllowlist"] is False
        assert result["admins"] == [111]
        assert "allow_list" not in result


# ---------------------------------------------------------------------------
# configure_logging tests
# ---------------------------------------------------------------------------


class TestConfigureLogging:
    """Tests for configure_logging()."""

    @pytest.mark.asyncio
    async def test_with_admin_notify(self):
        """Returns logging config with admin notification ID."""
        with patch("src.setup.prompts.questionary") as mock_q:
            # confirm: toConsole=True, debug=False
            confirm_mock = MagicMock()
            confirm_mock.ask_async = AsyncMock(side_effect=[True, False])
            mock_q.confirm.return_value = confirm_mock

            # text: admin notify ID
            text_mock = MagicMock()
            text_mock.ask_async = AsyncMock(return_value="12345")
            mock_q.text.return_value = text_mock

            result = await configure_logging()

        assert result == {
            "toConsole": True,
            "debug": False,
            "adminNotifyId": 12345,
        }

    @pytest.mark.asyncio
    async def test_invalid_admin_notify_retries(self):
        """Non-numeric notify ID is rejected, then valid ID accepted."""
        with patch("src.setup.prompts.questionary") as mock_q:
            confirm_mock = MagicMock()
            confirm_mock.ask_async = AsyncMock(side_effect=[True, False])
            mock_q.confirm.return_value = confirm_mock

            # text: "abc" (invalid), "99999" (valid)
            text_mock = MagicMock()
            text_mock.ask_async = AsyncMock(side_effect=["abc", "99999"])
            mock_q.text.return_value = text_mock

            result = await configure_logging()

        assert result["adminNotifyId"] == 99999

    @pytest.mark.asyncio
    async def test_empty_admin_notify(self):
        """Empty admin notify ID defaults to 0."""
        with patch("src.setup.prompts.questionary") as mock_q:
            confirm_mock = MagicMock()
            confirm_mock.ask_async = AsyncMock(side_effect=[True, True])
            mock_q.confirm.return_value = confirm_mock

            text_mock = MagicMock()
            text_mock.ask_async = AsyncMock(return_value="")
            mock_q.text.return_value = text_mock

            result = await configure_logging()

        assert result["adminNotifyId"] == 0


# ---------------------------------------------------------------------------
# configure_arr_features tests
# ---------------------------------------------------------------------------


class TestConfigureArrFeatures:
    """Tests for configure_arr_features()."""

    @pytest.mark.asyncio
    async def test_radarr_has_minimum_availability(self):
        """Radarr features include minimumAvailability."""
        with patch("src.setup.prompts.questionary") as mock_q:
            # confirm: search=True
            mock_q.confirm.return_value = _mock_questionary_ask(True)
            # select: minimumAvailability
            mock_q.select.return_value = _mock_questionary_ask("announced")

            result = await configure_arr_features("radarr")

        assert result["search"] is True
        assert result["minimumAvailability"] == "announced"

    @pytest.mark.asyncio
    async def test_sonarr_has_season_folder(self):
        """Sonarr features include seasonFolder."""
        with patch("src.setup.prompts.questionary") as mock_q:
            confirm_mock = MagicMock()
            confirm_mock.ask_async = AsyncMock(side_effect=[True, True])
            mock_q.confirm.return_value = confirm_mock

            result = await configure_arr_features("sonarr")

        assert result["search"] is True
        assert result["seasonFolder"] is True

    @pytest.mark.asyncio
    async def test_lidarr_has_album_folder_and_monitor(self):
        """Lidarr features include albumFolder and monitorOption."""
        with patch("src.setup.prompts.questionary") as mock_q:
            # confirm: search=True, albumFolder=True
            confirm_mock = MagicMock()
            confirm_mock.ask_async = AsyncMock(side_effect=[True, True])
            mock_q.confirm.return_value = confirm_mock
            # select: monitorOption
            mock_q.select.return_value = _mock_questionary_ask("all")

            result = await configure_arr_features("lidarr")

        assert result["search"] is True
        assert result["albumFolder"] is True
        assert result["monitorOption"] == "all"


# ---------------------------------------------------------------------------
# configure_required_value tests
# ---------------------------------------------------------------------------


class TestConfigureRequiredValue:
    """Tests for configure_required_value()."""

    @pytest.mark.asyncio
    async def test_telegram_token(self):
        """Configures telegram token and password."""
        config = {}
        with patch("src.setup.prompts.questionary") as mock_q:
            password_mock = MagicMock()
            password_mock.ask_async = AsyncMock(
                side_effect=["bot-token", "chat-pass"]
            )
            mock_q.password.return_value = password_mock

            result = await configure_required_value(config, "telegram", "token")

        assert result["telegram"]["token"] == "bot-token"
        assert result["telegram"]["password"] == "chat-pass"

    @pytest.mark.asyncio
    async def test_telegram_token_existing_password(self):
        """Only prompts for token when password already exists."""
        config = {"telegram": {"password": "existing"}}
        with patch("src.setup.prompts.questionary") as mock_q:
            password_mock = MagicMock()
            password_mock.ask_async = AsyncMock(return_value="new-token")
            mock_q.password.return_value = password_mock

            result = await configure_required_value(config, "telegram", "token")

        assert result["telegram"]["token"] == "new-token"
        assert result["telegram"]["password"] == "existing"

    @pytest.mark.asyncio
    async def test_arr_apikey(self):
        """Configures arr service API key."""
        config = {"radarr": {"auth": {"apikey": ""}}}
        with patch("src.setup.prompts.questionary") as mock_q:
            mock_q.password.return_value = _mock_questionary_ask("new-api-key")

            result = await configure_required_value(config, "radarr", "apikey")

        assert result["radarr"]["auth"]["apikey"] == "new-api-key"

    @pytest.mark.asyncio
    async def test_arr_apikey_creates_default_config(self):
        """Creates default service config when service not in config."""
        config = {}
        default_config = {
            "enable": False,
            "auth": {"apikey": "", "username": "", "password": ""},
        }
        with patch("src.setup.prompts.questionary") as mock_q:
            mock_q.password.return_value = _mock_questionary_ask("key-123")

            result = await configure_required_value(
                config, "radarr", "apikey", default_config=default_config
            )

        assert result["radarr"]["auth"]["apikey"] == "key-123"
