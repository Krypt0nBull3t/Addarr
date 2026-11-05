"""Tests for src/utils/helpers.py"""

import pytest
from unittest.mock import patch, MagicMock

from src.utils.helpers import (
    admin_only,
    format_bytes,
    is_admin,
    is_allowed,
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
