"""Tests for src/utils/__init__.py"""

from unittest.mock import patch


class TestInitUtils:
    """Tests for init_utils function."""

    def test_init_utils_initializes_colorama(self):
        """init_utils turns on colorama with autoreset."""
        from src.utils import init_utils

        with patch("src.utils.init_colorama") as mock_colorama:
            init_utils()

        mock_colorama.assert_called_once_with(autoreset=True)
