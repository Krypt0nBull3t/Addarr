"""
Filename: chat.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Chat utility functions.

This module provides utility functions for handling chat-related operations.
"""

from typing import Optional

from telegram.error import BadRequest


def get_chat_name(chat_id: int, chat_title: Optional[str] = None) -> str:
    """
    Get a formatted chat name for logging purposes.

    Args:
        chat_id: The Telegram chat ID
        chat_title: The chat title (for group chats)

    Returns:
        A formatted string containing the chat name/ID
    """
    if chat_title:
        return f"{chat_title} ({chat_id})"
    return f"chat {chat_id}"


async def edit_text_ignoring_unmodified(message, text: str, **kwargs) -> None:
    """Edit a message's text, ignoring Telegram's error for identical text.

    A refresh button often produces the same text again, and Telegram then
    raises BadRequest "Message is not modified". Any other error still raises.
    """
    try:
        await message.edit_text(text, **kwargs)
    except BadRequest as e:
        if "message is not modified" not in str(e).lower():
            raise
