"""
Filename: library.py
Author: Addarr Contributors
Created Date: 2026-02-18
Description: Library listing handler module.

This module handles /allMovies, /allSeries, and /allMusic commands,
displaying paginated lists of media items from the user's library.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler
from src.utils.logger import get_logger, log_user_interaction
from src.services.media import MediaService
from src.services.translation import TranslationService
from src.bot.handlers.auth import require_auth

logger = get_logger("addarr.library")

ITEMS_PER_PAGE = 10

# Media type short codes for callback data (stay under 64-byte limit)
MEDIA_TYPES = {
    "m": {"label": "movies", "service_method": "get_movies"},
    "s": {"label": "series", "service_method": "get_series"},
    "a": {"label": "music", "service_method": "get_music"},
}


class LibraryHandler:
    """Handler for library listing operations."""

    def __init__(self):
        self.media_service = MediaService()
        self.translation = TranslationService()

    def get_handler(self):
        """Get library command handlers."""
        return [
            CommandHandler("allMovies", self.handle_all_movies),
            CommandHandler("allSeries", self.handle_all_series),
            CommandHandler("allMusic", self.handle_all_music),
            CallbackQueryHandler(
                self.handle_page_navigation, pattern="^lib_"
            ),
        ]

    @require_auth
    async def handle_all_movies(self, update, context):
        """Handle /allMovies command."""
        await self._fetch_and_show(update, context, "m")

    @require_auth
    async def handle_all_series(self, update, context):
        """Handle /allSeries command."""
        await self._fetch_and_show(update, context, "s")

    @require_auth
    async def handle_all_music(self, update, context):
        """Handle /allMusic command."""
        await self._fetch_and_show(update, context, "a")

    async def _fetch_and_show(self, update, context, media_type):
        """Fetch library items and show paginated list."""
        if not update.effective_message or not update.effective_user:
            return

        type_info = MEDIA_TYPES[media_type]
        log_user_interaction(
            logger, update.effective_user,
            f"/all{type_info['label'].capitalize()}"
        )

        try:
            method = getattr(self.media_service, type_info["service_method"])
            items = await method()
        except ValueError:
            await update.message.reply_text(
                self.translation.get_text(
                    "LibraryNotEnabled", subject=type_info["label"]
                )
            )
            return
        except Exception:
            logger.error(
                f"Error fetching {type_info['label']} library",
                exc_info=True,
            )
            await update.message.reply_text(
                self.translation.get_text("LibraryError")
            )
            return

        if not items:
            await update.message.reply_text(
                self.translation.get_text(
                    "LibraryEmpty", subject=type_info["label"]
                )
            )
            return

        # Sort alphabetically by title
        items = sorted(items, key=lambda x: x.get("title", "").lower())

        # Cache items for pagination
        context.user_data[f"library_{media_type}"] = items

        text, reply_markup = self._build_page_message(
            items, 0, media_type
        )
        await update.message.reply_text(text, reply_markup=reply_markup)

    @staticmethod
    def _build_page_message(items, page, media_type):
        """Build a paginated text message with navigation buttons."""
        total = len(items)
        total_pages = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
        start = page * ITEMS_PER_PAGE
        end = min(start + ITEMS_PER_PAGE, total)
        page_items = items[start:end]

        type_label = MEDIA_TYPES[media_type]["label"].capitalize()

        lines = [f"📚 {type_label} ({total} total)\n"]
        for i, item in enumerate(page_items, start=start + 1):
            lines.append(f"{i}. {item.get('title', 'Unknown')}")

        if total_pages > 1:
            lines.append(f"\nPage {page + 1}/{total_pages}")

        text = "\n".join(lines)

        # Build navigation buttons
        buttons = []
        if page > 0:
            buttons.append(
                InlineKeyboardButton(
                    "⬅️ Previous",
                    callback_data=f"lib_{media_type}_{page - 1}",
                )
            )
        if page < total_pages - 1:
            buttons.append(
                InlineKeyboardButton(
                    "Next ➡️",
                    callback_data=f"lib_{media_type}_{page + 1}",
                )
            )

        reply_markup = InlineKeyboardMarkup([buttons]) if buttons else None
        return text, reply_markup

    async def handle_page_navigation(self, update, context):
        """Handle pagination callback queries (lib_{type}_{page})."""
        if not update.callback_query:
            return

        query = update.callback_query
        await query.answer()

        # Parse callback data: lib_{type}_{page}
        parts = query.data.split("_")
        if len(parts) != 3:
            return

        _, media_type, page_str = parts

        try:
            page = int(page_str)
        except ValueError:
            return

        # Retrieve cached items
        cache_key = f"library_{media_type}"
        items = context.user_data.get(cache_key)

        if not items:
            await query.message.edit_text(
                self.translation.get_text("LibraryExpired")
            )
            return

        text, reply_markup = self._build_page_message(
            items, page, media_type
        )
        await query.message.edit_text(text, reply_markup=reply_markup)
