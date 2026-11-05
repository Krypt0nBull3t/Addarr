"""Tests for src/utils/chat.py"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram.error import BadRequest

from src.utils.chat import edit_text_ignoring_unmodified, get_chat_name


class TestGetChatName:
    """Tests for get_chat_name utility function."""

    def test_get_chat_name_with_title(self):
        """Returns 'title (id)' when chat_title is provided."""
        result = get_chat_name(123, "My Group")
        assert result == "My Group (123)"

    def test_get_chat_name_without_title(self):
        """Returns 'chat id' when no chat_title is provided."""
        result = get_chat_name(123)
        assert result == "chat 123"

    def test_get_chat_name_none_title(self):
        """Returns 'chat id' when chat_title is explicitly None."""
        result = get_chat_name(123, None)
        assert result == "chat 123"


class TestEditTextIgnoringUnmodified:
    """Tests for edit_text_ignoring_unmodified."""

    @pytest.mark.asyncio
    async def test_edits_message(self):
        """Passes the text and keyword arguments to edit_text."""
        message = MagicMock()
        message.edit_text = AsyncMock()

        await edit_text_ignoring_unmodified(message, "Hi", reply_markup="kb")

        message.edit_text.assert_awaited_once_with("Hi", reply_markup="kb")

    @pytest.mark.asyncio
    async def test_ignores_message_not_modified(self):
        """Telegram's error for an identical edit is not raised."""
        message = MagicMock()
        message.edit_text = AsyncMock(side_effect=BadRequest(
            "Message is not modified: specified new message content and "
            "reply markup are exactly the same"
        ))

        await edit_text_ignoring_unmodified(message, "Hi")

    @pytest.mark.asyncio
    async def test_raises_other_bad_request(self):
        """Any other BadRequest still raises."""
        message = MagicMock()
        message.edit_text = AsyncMock(side_effect=BadRequest("Message to edit not found"))

        with pytest.raises(BadRequest, match="not found"):
            await edit_text_ignoring_unmodified(message, "Hi")
