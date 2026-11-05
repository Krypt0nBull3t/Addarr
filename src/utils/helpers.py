"""
Filename: helpers.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Helper functions module.

This module contains utility functions used throughout the application,
including admin and allowlist checks and data formatting.
These functions provide common functionality needed by multiple components.
"""

from typing import Optional
from ..config.settings import config


def format_bytes(size: float) -> str:
    """Format bytes to human readable string"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def is_admin(user_id: int) -> bool:
    """Check if user is in the config admins list"""
    # str(): IDs may be quoted in YAML, and `admins:` may be left empty (None)
    return str(user_id) in map(str, config.get("admins") or [])


def is_allowed(user_id: int) -> bool:
    """Check if user passes the allowlist (admins always do)"""
    if not config.get("security", {}).get("enableAllowlist", False):
        return True
    return str(user_id) in map(str, config.get("allow_list") or []) or is_admin(user_id)


def admin_only(service: Optional[str] = None) -> bool:
    """Check if admin mode restricts this action to admins.

    With a service name (transmission, sabnzbd), that service's onlyAdmin
    flag must also be set.
    """
    if not config.get("security", {}).get("enableAdmin", False):
        return False
    return service is None or config.get(service, {}).get("onlyAdmin", True)
