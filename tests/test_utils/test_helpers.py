"""Tests for src/utils/helpers.py"""

from unittest.mock import patch, MagicMock

from src.utils.helpers import format_bytes, is_admin, is_allowed, save_chat_id


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

    def test_is_allowed_allowlist_disabled(self):
        """Returns True when enableAllowlist is False in config."""
        mock_cfg = MagicMock()
        mock_cfg.get.return_value = False
        with patch("src.utils.helpers.config", mock_cfg):
            assert is_allowed(999) is True

    def test_is_allowed_in_list(self, tmp_path):
        """Returns True when user_id is in the allowlist file."""
        allow_file = tmp_path / "allowlist.txt"
        allow_file.write_text("100\n200\n300\n")

        mock_cfg = MagicMock()
        mock_cfg.get.return_value = True

        with (
            patch("src.utils.helpers.config", mock_cfg),
            patch("src.utils.helpers.ALLOWLIST_PATH", str(allow_file)),
        ):
            assert is_allowed(200) is True

    def test_is_allowed_not_in_list(self, tmp_path):
        """Returns False when user_id is NOT in the allowlist file."""
        allow_file = tmp_path / "allowlist.txt"
        allow_file.write_text("100\n200\n300\n")

        mock_cfg = MagicMock()
        mock_cfg.get.return_value = True

        with (
            patch("src.utils.helpers.config", mock_cfg),
            patch("src.utils.helpers.ALLOWLIST_PATH", str(allow_file)),
        ):
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
