"""
Filename: missing.py
Author: Addarr Contributors
Created Date: 2026-03-03
Description: Missing/wanted media handler module.
"""

from telegram import Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from src.utils.logger import get_logger, log_user_interaction
from src.bot.handlers.auth import require_auth
from src.bot.keyboards import (
    get_missing_items_keyboard,
    get_missing_empty_keyboard,
    get_main_menu_keyboard,
)
from src.services.media import MediaService
from src.services.translation import TranslationService

logger = get_logger("addarr.missing")


class MissingHandler:
    """Handler for missing/wanted media browsing and search triggers."""

    def __init__(self):
        self.media_service = MediaService()
        self.translation = TranslationService()

    def get_handler(self):
        """Get missing command handlers."""
        return [
            CommandHandler("missing", self.show_missing),
            CallbackQueryHandler(
                self.handle_missing_action, pattern="^missing_"
            ),
        ]

    @require_auth
    async def show_missing(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Show missing/wanted media with inline keyboard."""
        if not update.effective_user:  # pragma: no cover
            return

        log_user_interaction(logger, update.effective_user, "/missing")

        context.user_data.setdefault("missing_filter", "all")

        items = await self.media_service.get_missing_media()
        context.user_data["missing_items"] = items

        text, keyboard = self._build_response(items)

        if update.callback_query:
            await update.callback_query.message.edit_text(
                text, reply_markup=keyboard
            )
        else:
            await update.message.reply_text(text, reply_markup=keyboard)

    @require_auth
    async def handle_missing_action(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle missing callback button presses."""
        if not update.callback_query:
            return

        query = update.callback_query
        data = query.data

        log_user_interaction(logger, query.from_user, data)

        if data.startswith("missing_filter_"):
            await self._handle_filter(query, context)
        elif data.startswith("missing_page_"):
            await self._handle_page(query, context)
        elif data == "missing_refresh":
            await self._handle_refresh(query, context)
        elif data == "missing_back":
            await self._handle_back(query)
        elif data.startswith("missing_search_"):
            await self._handle_search(query, context)
        else:
            await query.answer()

    async def _handle_filter(self, query, context):
        """Apply a filter tab and update the display."""
        filter_type = query.data.split("_")[-1]

        if filter_type == "cutoff":
            items = await self.media_service.get_cutoff_unmet_media()
            context.user_data["missing_items"] = items
            context.user_data["missing_filter"] = "cutoff"
        elif filter_type == "all":
            items = await self.media_service.get_missing_media()
            context.user_data["missing_items"] = items
            context.user_data["missing_filter"] = "all"
        elif filter_type == "movie":
            context.user_data["missing_filter"] = "movie"
        elif filter_type == "series":
            context.user_data["missing_filter"] = "episode"

        items = context.user_data.get("missing_items", [])
        active_filter = context.user_data.get("missing_filter", "all")
        filtered = self._apply_filter(items, active_filter)

        text, keyboard = self._build_response(filtered, active_filter=active_filter)
        await query.message.edit_text(text, reply_markup=keyboard)
        await query.answer()

    async def _handle_page(self, query, context):
        """Show a different page of cached missing items."""
        page = int(query.data.split("_")[-1])
        items = context.user_data.get("missing_items", [])
        active_filter = context.user_data.get("missing_filter", "all")
        filtered = self._apply_filter(items, active_filter)

        text, keyboard = self._build_response(
            filtered, page, active_filter=active_filter
        )
        await query.message.edit_text(text, reply_markup=keyboard)
        await query.answer()

    async def _handle_refresh(self, query, context):
        """Re-fetch data based on current filter mode."""
        active_filter = context.user_data.get("missing_filter", "all")

        if active_filter == "cutoff":
            items = await self.media_service.get_cutoff_unmet_media()
        else:
            items = await self.media_service.get_missing_media()

        context.user_data["missing_items"] = items
        filtered = self._apply_filter(items, active_filter)

        text, keyboard = self._build_response(filtered, active_filter=active_filter)
        await query.message.edit_text(text, reply_markup=keyboard)
        await query.answer()

    async def _handle_back(self, query):
        """Return to the main menu."""
        await query.message.edit_text(
            "\U0001f3e0 Main Menu",
            reply_markup=get_main_menu_keyboard(),
        )
        await query.answer()

    async def _handle_search(self, query, context):
        """Trigger a manual search for a specific item."""
        # Parse: missing_search_radarr_1  or  missing_search_sonarr_101
        parts = query.data.split("_")
        service = parts[2]
        item_id = int(parts[3])

        await query.answer(
            self.translation.get_text("MissingSearching")
        )

        success = await self.media_service.trigger_missing_search(
            service, item_id
        )

        if success:
            await query.answer(
                self.translation.get_text("MissingSearchSuccess"),
                show_alert=True,
            )
        else:
            await query.answer(
                self.translation.get_text("MissingSearchFailed"),
                show_alert=True,
            )

    def _build_response(self, items, page=0, active_filter="all"):
        """Build missing text and keyboard from items."""
        if items:
            title = self.translation.get_text("MissingTitle")
            text = (
                f"\U0001f4ed {title}\n\n"
                f"{len(items)} wanted items"
            )
            keyboard = get_missing_items_keyboard(items, page, active_filter)
        else:
            text = (
                f"\U0001f4ed {self.translation.get_text('MissingTitle')}"
                f"\n\n{self.translation.get_text('MissingEmpty')}"
            )
            keyboard = get_missing_empty_keyboard()
        return text, keyboard

    @staticmethod
    def _apply_filter(items, active_filter):
        """Filter items by type."""
        if active_filter in ("movie", "episode"):
            return [i for i in items if i["type"] == active_filter]
        return items
