"""Tests for src/utils/error_handler.py"""

from unittest.mock import patch, mock_open

from src.utils.error_handler import (
    handle_token_error,
    handle_missing_token_error,
    handle_network_error,
    handle_initialization_error,
)


# ---- handle_token_error ----


class TestHandleTokenError:
    """Tests for handle_token_error."""

    def test_user_says_yes_valid_token(self):
        """Returns True when user enters y and provides valid token."""
        yaml_data = {"telegram": {"token": "old-token"}}
        with (
            patch("builtins.input", side_effect=["y", "new-valid-token"]),
            patch("builtins.open", mock_open(read_data="telegram:\n  token: old\n")),
            patch("yaml.safe_load", return_value=yaml_data),
            patch("yaml.dump"),
        ):
            result = handle_token_error()
        assert result is True
        # Verify token was updated in the config dict
        assert yaml_data["telegram"]["token"] == "new-valid-token"

    def test_user_says_yes_empty_token_then_yes_valid(self):
        """Retries when user enters empty token, then succeeds."""
        yaml_data = {"telegram": {"token": "old"}}
        with (
            patch("builtins.input", side_effect=["y", "  ", "y", "good-token"]),
            patch("builtins.open", mock_open(read_data="telegram:\n  token: old\n")),
            patch("yaml.safe_load", return_value=yaml_data),
            patch("yaml.dump"),
        ):
            result = handle_token_error()
        assert result is True

    def test_user_says_yes_no_telegram_section(self):
        """Creates telegram section if missing in config."""
        yaml_data = {}
        with (
            patch("builtins.input", side_effect=["y", "new-token"]),
            patch("builtins.open", mock_open(read_data="{}")),
            patch("yaml.safe_load", return_value=yaml_data),
            patch("yaml.dump"),
        ):
            result = handle_token_error()
        assert result is True
        assert yaml_data["telegram"]["token"] == "new-token"

    def test_user_says_yes_file_error(self):
        """Returns False when file operation fails."""
        with (
            patch("builtins.input", side_effect=["y", "new-token"]),
            patch("builtins.open", side_effect=IOError("disk full")),
        ):
            result = handle_token_error()
        assert result is False

    def test_user_says_no(self):
        """Returns False when user declines."""
        with patch("builtins.input", return_value="n"):
            result = handle_token_error()
        assert result is False

    def test_invalid_then_no(self):
        """Prompts again after invalid input, then user says n."""
        with patch("builtins.input", side_effect=["maybe", "n"]):
            result = handle_token_error()
        assert result is False


# ---- handle_missing_token_error ----


class TestHandleMissingTokenError:
    """Tests for handle_missing_token_error."""

    def test_prints_instructions(self):
        """Prints setup instructions without raising."""
        handle_missing_token_error()  # should not raise


# ---- handle_network_error ----


class TestHandleNetworkError:
    """Tests for handle_network_error."""

    def test_prints_instructions(self):
        """Prints troubleshooting instructions without raising."""
        handle_network_error()  # should not raise


# ---- handle_initialization_error ----


class TestHandleInitializationError:
    """Tests for handle_initialization_error."""

    def test_prints_error_details(self):
        """Prints error details and troubleshooting steps."""
        error = RuntimeError("failed to start")
        handle_initialization_error(error)  # should not raise
