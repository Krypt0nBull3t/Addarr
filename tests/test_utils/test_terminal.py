"""Tests for src/utils/terminal.py"""

from unittest.mock import MagicMock, patch

import pytest

from src.utils.terminal import is_interactive


@pytest.mark.parametrize(
    "stdin_tty, stdout_tty, expected",
    [(True, True, True), (True, False, False), (False, True, False), (False, False, False)],
)
def test_is_interactive_checks_both_streams(stdin_tty, stdout_tty, expected):
    """Only a terminal on both stdin and stdout counts as interactive."""
    stdin, stdout = MagicMock(), MagicMock()
    stdin.isatty.return_value = stdin_tty
    stdout.isatty.return_value = stdout_tty
    with patch("sys.stdin", stdin), patch("sys.stdout", stdout):
        assert is_interactive() is expected
