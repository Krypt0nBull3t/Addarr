"""
Filename: history.py
Author: Addarr Contributors
Created Date: 2026-03-09
Description: History handler for recent Radarr/Sonarr activity.
"""

from telegram import Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from src.utils.logger import get_logger, log_user_interaction
from src.bot.handlers.auth import require_auth
from src.bot.keyboards import (
    get_history_items_keyboard,
    get_history_empty_keyboard,
    get_main_menu_keyboard,
)
from src.services.media import MediaService
from src.services.translation import TranslationService

logger = get_logger("addarr.history")


class HistoryHandler:
    """Handler for /history command showing recent activity."""

    def __init__(self):
        self.media_service = MediaService()
        self.translation = TranslationService()

    def get_handler(self):
        """Get history command handlers."""
        return [
            CommandHandler("history", self.show_history),
            CallbackQueryHandler(
                self.handle_history_action, pattern="^hist_"
            ),
        ]

    @require_auth
    async def show_history(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Show recent activity with inline keyboard."""
        if not update.effective_user:  # pragma: no cover
            return

        log_user_interaction(logger, update.effective_user, "/history")

        context.user_data["hist_filter"] = None
        context.user_data["hist_page"] = 0

        items = await self.media_service.get_history()
        context.user_data["hist_items"] = items

        text, keyboard = self._build_response(items)

        if update.callback_query:
            await update.callback_query.message.edit_text(
                text, reply_markup=keyboard
            )
        else:
            await update.message.reply_text(text, reply_markup=keyboard)

    @require_auth
    async def handle_history_action(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle history callback button presses."""
        if not update.callback_query:
            return

        query = update.callback_query
        data = query.data

        log_user_interaction(logger, query.from_user, data)

        if data.startswith("hist_filter_"):
            await self._handle_filter(query, context)
        elif data.startswith("hist_page_"):
            await self._handle_page(query, context)
        elif data == "hist_refresh":
            await self._handle_refresh(query, context)
        elif data == "hist_back":
            await self._handle_back(query)
        else:
            await query.answer()

    async def _handle_filter(self, query, context):
        """Change event type filter and re-fetch."""
        raw = query.data.replace("hist_filter_", "")
        event_filter = None if raw == "all" else raw
        context.user_data["hist_filter"] = event_filter
        context.user_data["hist_page"] = 0

        items = await self.media_service.get_history(
            event_type=event_filter
        )
        context.user_data["hist_items"] = items

        text, keyboard = self._build_response(
            items, event_filter=event_filter
        )
        await query.message.edit_text(text, reply_markup=keyboard)
        await query.answer()

    async def _handle_page(self, query, context):
        """Show a different page of cached history items."""
        page = int(query.data.split("_")[-1])
        context.user_data["hist_page"] = page
        items = context.user_data.get("hist_items", [])
        event_filter = context.user_data.get("hist_filter")

        text, keyboard = self._build_response(
            items, page=page, event_filter=event_filter
        )
        await query.message.edit_text(text, reply_markup=keyboard)
        await query.answer()

    async def _handle_refresh(self, query, context):
        """Re-fetch history data."""
        event_filter = context.user_data.get("hist_filter")
        context.user_data["hist_page"] = 0

        items = await self.media_service.get_history(
            event_type=event_filter
        )
        context.user_data["hist_items"] = items

        text, keyboard = self._build_response(
            items, event_filter=event_filter
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

    def _build_response(self, items, page=0, event_filter=None):
        """Build history text and keyboard from items."""
        if items:
            title = self.translation.get_text("HistoryTitle")
            text = f"\U0001f4dc {title}\n\n{len(items)} items"
            keyboard = get_history_items_keyboard(
                items, page, event_filter=event_filter
            )
        else:
            text = (
                f"\U0001f4dc {self.translation.get_text('HistoryTitle')}"
                f"\n\n{self.translation.get_text('HistoryEmpty')}"
            )
            keyboard = get_history_empty_keyboard()
        return text, keyboard
