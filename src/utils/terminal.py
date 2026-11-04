"""
Description: Terminal detection.

A module of its own, so error_handler can ask without importing
src.config.settings (that import loads and validates config.yaml).
"""

import sys


def is_interactive() -> bool:
    """Check if we're running in an interactive terminal."""
    return sys.stdin.isatty() and sys.stdout.isatty()
