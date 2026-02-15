"""Tests for src/utils/chat.py"""

from src.utils.chat import get_chat_name


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
