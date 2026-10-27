"""
Filename: helpers.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Helper functions module.

This module contains utility functions used throughout the application,
including authentication checks, chat ID management, and data formatting.
These functions provide common functionality needed by multiple components.
"""

import os
from typing import List, Optional
from ..config.settings import config
from ..definitions import CHATID_PATH


def check_auth(func):
    """Decorator to check if user is authenticated"""
    async def wrapper(self, update, context, *args, **kwargs):
        if not await is_authenticated(update.effective_chat.id):
            await update.message.reply_text(
                "You need to authenticate first. Use /auth to begin."
            )
            return None
        return await func(self, update, context, *args, **kwargs)
    return wrapper


async def get_authorized_chats() -> List[int]:
    """Get list of authorized chat IDs"""
    if not os.path.exists(CHATID_PATH):
        return []

    with open(CHATID_PATH, 'r') as f:
        return [
            int(line.split(' - ')[0])
            for line in f.readlines()
            if line.strip()
        ]


def save_chat_id(chat_id: int, chat_name: Optional[str] = None):
    """Save a chat ID to authorized chats"""
    entry = f"{chat_id}"
    if chat_name:
        entry += f" - {chat_name}"
    entry += "\n"

    with open(CHATID_PATH, 'a') as f:
        f.write(entry)


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


async def is_authenticated(chat_id: int) -> bool:
    """Check if a chat is authenticated"""
    return chat_id in await get_authorized_chats()
