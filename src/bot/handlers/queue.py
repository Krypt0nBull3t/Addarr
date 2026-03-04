"""
Filename: queue.py
Author: Addarr Contributors
Created Date: 2026-03-04
Description: Download queue handler module.
"""

from telegram import Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from src.utils.logger import get_logger, log_user_interaction
from src.bot.handlers.auth import require_auth
from src.bot.keyboards import (
    get_queue_items_keyboard,
    get_queue_empty_keyboard,
    get_main_menu_keyboard,
)
from src.services.media import MediaService
from src.services.translation import TranslationService

logger = get_logger("addarr.queue")


class QueueHandler:
    """Handler for download queue browsing."""

    def __init__(self):
        self.media_service = MediaService()
        self.translation = TranslationService()

    def get_handler(self):
        """Get queue command handlers."""
        return [
            CommandHandler("queue", self.show_queue),
            CallbackQueryHandler(
                self.handle_queue_action, pattern="^queue_"
            ),
        ]

    @require_auth
    async def show_queue(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Show download queue with inline keyboard."""
        log_user_interaction(logger, update.effective_user, "/queue")

        context.user_data.setdefault("queue_filter", "all")

        items = await self.media_service.get_queue_media()
        context.user_data["queue_items"] = items

        text, keyboard = self._build_response(items)

        if update.callback_query:
            await update.callback_query.message.edit_text(
                text, reply_markup=keyboard
            )
        else:
            await update.message.reply_text(text, reply_markup=keyboard)

    @require_auth
    async def handle_queue_action(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle queue callback button presses."""
        if not update.callback_query:
            return

        query = update.callback_query
        data = query.data

        log_user_interaction(logger, query.from_user, data)

        if data.startswith("queue_filter_"):
            await self._handle_filter(query, context)
        elif data.startswith("queue_page_"):
            await self._handle_page(query, context)
        elif data == "queue_refresh":
            await self._handle_refresh(query, context)
        elif data == "queue_back":
            await self._handle_back(query)
        else:
            await query.answer()

    async def _handle_filter(self, query, context):
        """Apply a filter tab and update the display."""
        filter_type = query.data.split("_")[-1]

        if filter_type in ("all", "movie", "episode", "album"):
            context.user_data["queue_filter"] = filter_type

        if filter_type == "all":
            items = await self.media_service.get_queue_media()
            context.user_data["queue_items"] = items

        items = context.user_data.get("queue_items", [])
        active_filter = context.user_data.get("queue_filter", "all")
        filtered = self._apply_filter(items, active_filter)

        text, keyboard = self._build_response(
            filtered, active_filter=active_filter
        )
        await query.message.edit_text(text, reply_markup=keyboard)
        await query.answer()

    async def _handle_page(self, query, context):
        """Show a different page of cached queue items."""
        page = int(query.data.split("_")[-1])
        items = context.user_data.get("queue_items", [])
        active_filter = context.user_data.get("queue_filter", "all")
        filtered = self._apply_filter(items, active_filter)

        text, keyboard = self._build_response(
            filtered, page, active_filter=active_filter
        )
        await query.message.edit_text(text, reply_markup=keyboard)
        await query.answer()

    async def _handle_refresh(self, query, context):
        """Re-fetch queue data."""
        items = await self.media_service.get_queue_media()
        context.user_data["queue_items"] = items

        active_filter = context.user_data.get("queue_filter", "all")
        filtered = self._apply_filter(items, active_filter)

        text, keyboard = self._build_response(
            filtered, active_filter=active_filter
        )
        await query.message.edit_text(text, reply_markup=keyboard)
        await query.answer()

    async def _handle_back(self, query):
        """Return to the main menu."""
        await query.message.edit_text(
            "\U0001f3e0 Main Menu",
            reply_markup=get_main_menu_keyboard(),
        )
        await query.answer()

    def _build_response(self, items, page=0, active_filter="all"):
        """Build queue text and keyboard from items."""
        if items:
            title = self.translation.get_text("QueueTitle")
            text = (
                f"\U0001f4e5 {title}\n\n"
                f"{len(items)} queue items"
            )
            keyboard = get_queue_items_keyboard(items, page, active_filter)
        else:
            text = (
                f"\U0001f4e5 {self.translation.get_text('QueueTitle')}"
                f"\n\n{self.translation.get_text('QueueEmpty')}"
            )
            keyboard = get_queue_empty_keyboard()
        return text, keyboard

    @staticmethod
    def _apply_filter(items, active_filter):
        """Filter items by type."""
        if active_filter in ("movie", "episode", "album"):
            return [i for i in items if i["type"] == active_filter]
        return items
