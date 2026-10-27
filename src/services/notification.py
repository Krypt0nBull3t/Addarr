"""
Filename: notification.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Notification service module.

This module handles sending notifications to users and admins.
"""

from typing import Optional
from telegram import Bot

from src.utils.logger import get_logger
from src.config.settings import config

logger = get_logger("addarr.notification")


class NotificationService:
    """Service for handling notifications"""

    _instance: Optional["NotificationService"] = None
    _bot: Optional[Bot] = None
    admin_notify_id: Optional[str] = None

    def __new__(cls):
        """Ensure only one instance exists"""
        if cls._instance is None:
            cls._instance = super(NotificationService, cls).__new__(cls)
            cls._initialize()
        return cls._instance

    @classmethod
    def _initialize(cls):
        """Initialize the notification service"""
        cls.admin_notify_id = config.get("logging", {}).get("adminNotifyId")

    def set_bot(self, bot: Bot):
        """Set the bot instance for sending notifications"""
        self._bot = bot

    async def notify_admin(self, message: str):
        """Send notification to admin"""
        if not self._bot or not self.admin_notify_id:
            return

        try:
            await self._bot.send_message(
                chat_id=self.admin_notify_id,
                text=message
            )
        except Exception as e:
            logger.error(f"Failed to send admin notification: {e}")
