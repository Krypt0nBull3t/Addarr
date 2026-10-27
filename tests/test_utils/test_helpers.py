"""Tests for src/utils/helpers.py"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from src.utils.helpers import (
    admin_only,
    check_auth,
    get_authorized_chats,
    format_bytes,
    is_admin,
    is_allowed,
    is_authenticated,
    save_chat_id,
)


# ---- format_bytes ----


class TestFormatBytes:
    """Tests for format_bytes -- no mocking needed."""

    def test_format_bytes_bytes(self):
        """500 bytes renders as '500.0 B'."""
        assert format_bytes(500) == "500.0 B"

    def test_format_bytes_kb(self):
        """1024 bytes renders as '1.0 KB'."""
        assert format_bytes(1024) == "1.0 KB"

    def test_format_bytes_mb(self):
        """1 048 576 bytes renders as '1.0 MB'."""
        assert format_bytes(1048576) == "1.0 MB"

    def test_format_bytes_gb(self):
        """1 073 741 824 bytes renders as '1.0 GB'."""
        assert format_bytes(1073741824) == "1.0 GB"

    def test_format_bytes_tb(self):
        """1 099 511 627 776 bytes renders as '1.0 TB'."""
        assert format_bytes(1099511627776) == "1.0 TB"

    def test_format_bytes_pb(self):
        """Very large value falls through to PB."""
        pb = 1024 ** 5
        assert format_bytes(pb) == "1.0 PB"


# ---- is_admin ----


class TestIsAdmin:
    """Tests for is_admin -- reads the admins list from config."""

    @pytest.mark.parametrize("admins, expected", [
        ([100, 200], True),
        (["200"], True),  # IDs quoted in YAML still match
        ([100], False),
        (None, False),    # `admins:` left empty in YAML
    ])
    def test_is_admin(self, admins, expected, mock_config):
        mock_config._set("admins", admins)
        with patch("src.utils.helpers.config", mock_config):
            assert is_admin(200) is expected


# ---- is_allowed ----


class TestIsAllowed:
    """Tests for is_allowed -- reads security.enableAllowlist and allow_list."""

    @pytest.mark.parametrize("enabled, allow_list, admins, expected", [
        (False, [], [], True),     # allowlist off: everyone may use the bot
        (True, [200], [], True),
        (True, ["200"], [], True),
        (True, [100], [], False),
        (True, [], [200], True),   # admins are always allowed
        (True, None, [], False),
    ])
    def test_is_allowed(self, enabled, allow_list, admins, expected, mock_config):
        mock_config._set("security", {"enableAllowlist": enabled})
        mock_config._set("allow_list", allow_list)
        mock_config._set("admins", admins)
        with patch("src.utils.helpers.config", mock_config):
            assert is_allowed(200) is expected

    def test_is_allowed_missing_security_section_defaults_false(self):
        """Returns True (allowlist disabled) when security section is absent."""
        mock_cfg = MagicMock()
        mock_cfg.get.return_value = {}  # No security section
        with patch("src.utils.helpers.config", mock_cfg):
            assert is_allowed(999) is True


# ---- admin_only ----


class TestAdminOnly:
    """Tests for admin_only -- security.enableAdmin plus per-service onlyAdmin."""

    @pytest.mark.parametrize("enable_admin, service, only_admin, expected", [
        (False, None, True, False),       # admin mode off
        (True, None, True, True),
        (True, "sabnzbd", True, True),
        (True, "sabnzbd", False, False),
        (False, "sabnzbd", True, False),  # onlyAdmin needs admin mode
    ])
    def test_admin_only(self, enable_admin, service, only_admin, expected,
                        mock_config):
        mock_config._set("security", {"enableAdmin": enable_admin})
        mock_config._set("sabnzbd", {"onlyAdmin": only_admin})
        with patch("src.utils.helpers.config", mock_config):
            assert admin_only(service) is expected


# ---- save_chat_id ----


class TestSaveChatId:
    """Tests for save_chat_id -- patches CHATID_PATH to tmp_path."""

    def test_save_chat_id_with_name(self, tmp_path):
        """Writes 'id - name\\n' when chat_name is provided."""
        chatid_file = tmp_path / "chatid.txt"
        with patch("src.utils.helpers.CHATID_PATH", str(chatid_file)):
            save_chat_id(123, "TestUser")

        assert chatid_file.read_text() == "123 - TestUser\n"

    def test_save_chat_id_without_name(self, tmp_path):
        """Writes 'id\\n' when chat_name is not provided."""
        chatid_file = tmp_path / "chatid.txt"
        with patch("src.utils.helpers.CHATID_PATH", str(chatid_file)):
            save_chat_id(123)

        assert chatid_file.read_text() == "123\n"


# ---- check_auth ----


class TestCheckAuth:
    """Tests for the check_auth decorator."""

    @pytest.mark.asyncio
    async def test_authenticated_user_proceeds(self):
        """Authenticated user proceeds to the wrapped function."""
        class FakeHandler:
            @check_auth
            async def my_method(self, update, context):
                return "success"

        handler = FakeHandler()
        update = MagicMock()
        update.effective_chat.id = 42
        context = MagicMock()

        with patch("src.utils.helpers.is_authenticated", new_callable=AsyncMock, return_value=True):
            result = await handler.my_method(update, context)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_unauthenticated_user_blocked(self):
        """Unauthenticated user gets auth prompt and returns None."""
        class FakeHandler:
            @check_auth
            async def my_method(self, update, context):
                return "success"

        handler = FakeHandler()
        update = MagicMock()
        update.effective_chat.id = 42
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        with patch("src.utils.helpers.is_authenticated", new_callable=AsyncMock, return_value=False):
            result = await handler.my_method(update, context)
        assert result is None
        update.message.reply_text.assert_awaited_once()


# ---- get_authorized_chats ----


class TestGetAuthorizedChats:
    """Tests for get_authorized_chats."""

    @pytest.mark.asyncio
    async def test_file_exists(self, tmp_path):
        """Returns list of chat IDs from file."""
        chatid_file = tmp_path / "chatid.txt"
        chatid_file.write_text("100 - Alice\n200 - Bob\n300\n")
        with patch("src.utils.helpers.CHATID_PATH", str(chatid_file)):
            result = await get_authorized_chats()
        assert result == [100, 200, 300]

    @pytest.mark.asyncio
    async def test_file_missing(self, tmp_path):
        """Returns empty list when file does not exist."""
        missing = str(tmp_path / "nonexistent_chatid.txt")
        with patch("src.utils.helpers.CHATID_PATH", missing):
            result = await get_authorized_chats()
        assert result == []

    @pytest.mark.asyncio
    async def test_file_with_empty_lines(self, tmp_path):
        """Skips empty lines in the file."""
        chatid_file = tmp_path / "chatid.txt"
        chatid_file.write_text("100 - Alice\n\n200 - Bob\n\n")
        with patch("src.utils.helpers.CHATID_PATH", str(chatid_file)):
            result = await get_authorized_chats()
        assert result == [100, 200]


# ---- is_authenticated ----


class TestIsAuthenticated:
    """Tests for is_authenticated."""

    @pytest.mark.asyncio
    async def test_authenticated(self, tmp_path):
        """Returns True when chat_id is in authorized chats."""
        chatid_file = tmp_path / "chatid.txt"
        chatid_file.write_text("42 - Alice\n")
        with patch("src.utils.helpers.CHATID_PATH", str(chatid_file)):
            result = await is_authenticated(42)
        assert result is True

    @pytest.mark.asyncio
    async def test_not_authenticated(self, tmp_path):
        """Returns False when chat_id is not in authorized chats."""
        chatid_file = tmp_path / "chatid.txt"
        chatid_file.write_text("100 - Bob\n")
        with patch("src.utils.helpers.CHATID_PATH", str(chatid_file)):
            result = await is_authenticated(42)
        assert result is False
