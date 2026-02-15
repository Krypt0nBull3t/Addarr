"""Tests for src/utils/helpers.py"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from src.utils.helpers import (
    check_auth,
    get_authorized_chats,
    get_chat_name,
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
    """Tests for is_admin -- patches ADMIN_PATH to use tmp_path files."""

    @patch("src.utils.helpers.ADMIN_PATH")
    def test_is_admin_true(self, mock_path, tmp_path):
        """Returns True when user_id is present in the admin file."""
        admin_file = tmp_path / "admin.txt"
        admin_file.write_text("100\n200\n300\n")
        mock_path.__str__ = lambda self: str(admin_file)
        # os.path.exists and open use the string value, so patch the name
        with patch("src.utils.helpers.ADMIN_PATH", str(admin_file)):
            assert is_admin(200) is True

    @patch("src.utils.helpers.ADMIN_PATH")
    def test_is_admin_false(self, mock_path, tmp_path):
        """Returns False when user_id is NOT in the admin file."""
        admin_file = tmp_path / "admin.txt"
        admin_file.write_text("100\n200\n300\n")
        with patch("src.utils.helpers.ADMIN_PATH", str(admin_file)):
            assert is_admin(999) is False

    def test_is_admin_no_file(self, tmp_path):
        """Returns False when the admin file does not exist."""
        missing = str(tmp_path / "nonexistent_admin.txt")
        with patch("src.utils.helpers.ADMIN_PATH", missing):
            assert is_admin(100) is False


# ---- is_allowed ----


class TestIsAllowed:
    """Tests for is_allowed -- patches ALLOWLIST_PATH and config."""

    def _make_config(self, allowlist_enabled):
        """Build a mock config with enableAllowlist under security section."""
        mock_cfg = MagicMock()

        def get_side_effect(key, default=None):
            config_data = {
                "security": {"enableAllowlist": allowlist_enabled},
            }
            return config_data.get(key, default)

        mock_cfg.get.side_effect = get_side_effect
        return mock_cfg

    def test_is_allowed_allowlist_disabled(self):
        """Returns True when enableAllowlist is False in config."""
        mock_cfg = self._make_config(allowlist_enabled=False)
        with patch("src.utils.helpers.config", mock_cfg):
            assert is_allowed(999) is True

    def test_is_allowed_in_list(self, tmp_path):
        """Returns True when user_id is in the allowlist file."""
        allow_file = tmp_path / "allowlist.txt"
        allow_file.write_text("100\n200\n300\n")

        mock_cfg = self._make_config(allowlist_enabled=True)

        with (
            patch("src.utils.helpers.config", mock_cfg),
            patch("src.utils.helpers.ALLOWLIST_PATH", str(allow_file)),
        ):
            assert is_allowed(200) is True

    def test_is_allowed_not_in_list(self, tmp_path):
        """Returns False when user_id is NOT in the allowlist file."""
        allow_file = tmp_path / "allowlist.txt"
        allow_file.write_text("100\n200\n300\n")

        mock_cfg = self._make_config(allowlist_enabled=True)

        with (
            patch("src.utils.helpers.config", mock_cfg),
            patch("src.utils.helpers.ALLOWLIST_PATH", str(allow_file)),
        ):
            assert is_allowed(999) is False

    def test_is_allowed_no_file(self, tmp_path):
        """Returns False when allowlist is enabled but file is missing."""
        mock_cfg = self._make_config(allowlist_enabled=True)
        missing = str(tmp_path / "nonexistent_allowlist.txt")

        with (
            patch("src.utils.helpers.config", mock_cfg),
            patch("src.utils.helpers.ALLOWLIST_PATH", missing),
        ):
            assert is_allowed(100) is False

    def test_is_allowed_reads_nested_security_config(self, tmp_path):
        """is_allowed reads enableAllowlist from security section, not root."""
        allow_file = tmp_path / "allowlist.txt"
        allow_file.write_text("100\n200\n")

        mock_cfg = MagicMock()

        def get_side_effect(key, default=None):
            config_data = {
                "security": {"enableAllowlist": True},
            }
            return config_data.get(key, default)

        mock_cfg.get.side_effect = get_side_effect

        with (
            patch("src.utils.helpers.config", mock_cfg),
            patch("src.utils.helpers.ALLOWLIST_PATH", str(allow_file)),
        ):
            # User 999 NOT in allowlist — should be denied
            assert is_allowed(999) is False


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


# ---- get_chat_name ----


class TestGetChatName:
    """Tests for get_chat_name."""

    @pytest.mark.asyncio
    async def test_username(self):
        """Returns chat_id - username when username is set."""
        bot = AsyncMock()
        chat = MagicMock()
        chat.username = "alice"
        chat.title = None
        chat.first_name = None
        chat.last_name = None
        bot.get_chat.return_value = chat
        result = await get_chat_name(bot, 42)
        assert result == "42 - alice"

    @pytest.mark.asyncio
    async def test_title(self):
        """Returns chat_id - title when title is set."""
        bot = AsyncMock()
        chat = MagicMock()
        chat.username = None
        chat.title = "My Group"
        chat.first_name = None
        chat.last_name = None
        bot.get_chat.return_value = chat
        result = await get_chat_name(bot, 42)
        assert result == "42 - My Group"

    @pytest.mark.asyncio
    async def test_first_and_last_name(self):
        """Returns chat_id - first last when both names are set."""
        bot = AsyncMock()
        chat = MagicMock()
        chat.username = None
        chat.title = None
        chat.first_name = "Alice"
        chat.last_name = "Smith"
        bot.get_chat.return_value = chat
        result = await get_chat_name(bot, 42)
        assert result == "42 - Alice Smith"

    @pytest.mark.asyncio
    async def test_first_name_only(self):
        """Returns chat_id - first when only first_name is set."""
        bot = AsyncMock()
        chat = MagicMock()
        chat.username = None
        chat.title = None
        chat.first_name = "Alice"
        chat.last_name = None
        bot.get_chat.return_value = chat
        result = await get_chat_name(bot, 42)
        assert result == "42 - Alice"

    @pytest.mark.asyncio
    async def test_last_name_only(self):
        """Returns chat_id - last when only last_name is set."""
        bot = AsyncMock()
        chat = MagicMock()
        chat.username = None
        chat.title = None
        chat.first_name = None
        chat.last_name = "Smith"
        bot.get_chat.return_value = chat
        result = await get_chat_name(bot, 42)
        assert result == "42 - Smith"

    @pytest.mark.asyncio
    async def test_no_name(self):
        """Returns str(chat_id) when no name attributes are set."""
        bot = AsyncMock()
        chat = MagicMock()
        chat.username = None
        chat.title = None
        chat.first_name = None
        chat.last_name = None
        bot.get_chat.return_value = chat
        result = await get_chat_name(bot, 42)
        assert result == "42"


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
