"""
Filename: __init__.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Media handler package.

Re-exports MediaHandler and state constants for backward-compatible imports.
"""

from .handler import MediaHandler
from .dispatch import (
    SEARCHING,
    SELECTING,
    QUALITY_SELECT,
    SEASON_SELECT,
    ALBUM_SELECT,
)

__all__ = [
    "MediaHandler",
    "SEARCHING",
    "SELECTING",
    "QUALITY_SELECT",
    "SEASON_SELECT",
    "ALBUM_SELECT",
]
