"""Tests for src/utils/__init__.py"""

from unittest.mock import patch


class TestInitUtils:
    """Tests for init_utils function."""

    def test_init_utils_returns_dict(self):
        """init_utils returns a dict with all expected error classes and handlers."""
        from src.utils import init_utils

        with patch("src.utils.init_colorama") as mock_colorama:
            result = init_utils()

        mock_colorama.assert_called_once_with(autoreset=True)
        assert isinstance(result, dict)
        assert "AddarrError" in result
        assert "ConfigError" in result
        assert "ValidationError" in result
        assert "handle_token_error" in result
        assert "handle_missing_token_error" in result
        assert "handle_network_error" in result
        assert "handle_initialization_error" in result
        assert "handle_telegram_error" in result
        assert "send_error_message" in result
