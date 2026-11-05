"""
Tests for src/services/notification.py -- NotificationService singleton.
"""

import pytest
from unittest.mock import AsyncMock

from src.services.notification import NotificationService


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


class TestNotificationServiceSingleton:
    def test_singleton(self):
        a = NotificationService()
        b = NotificationService()
        assert a is b


# ---------------------------------------------------------------------------
# set_bot
# ---------------------------------------------------------------------------


class TestSetBot:
    def test_set_bot(self):
        service = NotificationService()
        mock_bot = AsyncMock()

        service.set_bot(mock_bot)

        assert service._bot is mock_bot


# ---------------------------------------------------------------------------
# notify_admin
# ---------------------------------------------------------------------------


class TestNotifyAdmin:
    @pytest.mark.asyncio
    async def test_notify_admin_success(self):
        service = NotificationService()
        mock_bot = AsyncMock()
        service._bot = mock_bot
        service.admin_notify_id = 99999

        await service.notify_admin("Test alert")

        mock_bot.send_message.assert_awaited_once_with(
            chat_id=99999, text="Test alert"
        )

    @pytest.mark.asyncio
    async def test_notify_admin_no_bot(self):
        service = NotificationService()
        service._bot = None
        service.admin_notify_id = 99999

        # Should not crash
        await service.notify_admin("Test alert")

    @pytest.mark.asyncio
    async def test_notify_admin_no_admin_id(self):
        service = NotificationService()
        mock_bot = AsyncMock()
        service._bot = mock_bot
        service.admin_notify_id = None

        # Should not crash and should not call send_message
        await service.notify_admin("Test alert")
        mock_bot.send_message.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_notify_admin_exception(self):
        service = NotificationService()
        mock_bot = AsyncMock()
        mock_bot.send_message.side_effect = Exception("Network error")
        service._bot = mock_bot
        service.admin_notify_id = 99999

        # Should catch exception and log, not raise
        await service.notify_admin("Test alert")
