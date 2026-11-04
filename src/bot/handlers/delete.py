"""
Filename: delete.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Delete handler module.

This module handles media deletion operations.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes, CallbackQueryHandler
from src.utils.logger import get_logger, log_user_interaction
from src.services.media import MediaService
from src.bot.handlers.auth import require_admin, require_auth
from src.services.rate_limit import rate_limit
from src.services.translation import TranslationService
from src.bot.keyboards import get_delete_items_keyboard
from src.utils.chat import edit_text_ignoring_unmodified

logger = get_logger("addarr.delete")

# media type -> MediaService methods: list all, get one, delete one
MEDIA_METHODS = {
    "movie": ("get_movies", "get_movie", "delete_movie"),
    "series": ("get_series", "get_series", "delete_series"),
    "music": ("get_music", "get_music", "delete_music"),
}


def _is_id(value: str) -> bool:
    """True for a non-empty run of ASCII digits (an id or a page number)."""
    return value.isascii() and value.isdigit()


class DeleteHandler:
    """Handler for delete operations"""

    def __init__(self):
        self.media_service = MediaService()
        self.translation = TranslationService()

    def get_handler(self):
        """Get delete command handlers"""
        return [
            CommandHandler("delete", self.handle_delete),
            CallbackQueryHandler(self.handle_delete_selection, pattern="^delete_")
        ]

    def get_delete_keyboard(self) -> InlineKeyboardMarkup:
        """Get the delete media type selection keyboard"""
        keyboard = [
            [
                InlineKeyboardButton(
                    f"🎬 {self.translation.get_text('Movie')}",
                    callback_data="delete_type_movie"
                ),
                InlineKeyboardButton(
                    f"📺 {self.translation.get_text('Series')}",
                    callback_data="delete_type_series"
                )
            ],
            [
                InlineKeyboardButton(
                    f"🎵 {self.translation.get_text('Music')}",
                    callback_data="delete_type_music"
                )
            ],
            [
                InlineKeyboardButton(
                    f"❌ {self.translation.get_text('Stop')}",
                    callback_data="delete_cancel"
                )
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    @require_auth
    @require_admin()
    @rate_limit("modify")
    async def handle_delete(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle delete command"""
        if not update.effective_message or not update.effective_user:
            return

        log_user_interaction(logger, update.effective_user, "/delete")

        await update.message.reply_text(
            self.translation.get_text(
                "DeletePrompt",
                default="Select what you want to delete"
            ),
            reply_markup=self.get_delete_keyboard()
        )

    @require_auth
    @require_admin()
    async def handle_delete_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle delete selection.

        Callbacks: delete_cancel, delete_type_<type>, delete_page_<type>_<n>,
        delete_item_<type>_<id>, delete_confirm_<type>_<id>. The type and id
        come from the callback, never from user_data: an older /delete list
        must act on the item it was drawn for.
        """
        if not update.callback_query:
            return

        query = update.callback_query
        await query.answer()

        parts = query.data[len("delete_"):].split("_")
        action = parts[0]

        if action == "cancel":
            await query.message.edit_text(
                self.translation.get_text("End")
            )
        elif action == "type":
            await self._show_list(query, "_".join(parts[1:]), 0)
        elif action == "page":
            if len(parts) != 3 or not _is_id(parts[2]):
                await self._show_bad_callback(query)
                return
            await self._show_list(query, parts[1], int(parts[2]))
        elif action in ("item", "confirm"):
            if len(parts) != 3 or not _is_id(parts[2]):
                await self._show_bad_callback(query)
                return
            if action == "item":
                await self._show_confirm(query, parts[1], parts[2])
            else:
                await self._delete(query, parts[1], parts[2])

    async def _show_bad_callback(self, query):
        await query.message.edit_text(
            self.translation.get_text("ItemDataNotFound")
        )

    async def _show_list(self, query, media_type: str, page: int):
        """Show one page of the item list for the given media type."""
        methods = MEDIA_METHODS.get(media_type)
        if not methods:
            await query.message.edit_text(
                self.translation.get_text("InvalidMediaType")
            )
            return

        try:
            items = await getattr(self.media_service, methods[0])()

            if not items:
                await query.message.edit_text(
                    self.translation.get_message("NoExist", subject=media_type)
                )
                return

            await edit_text_ignoring_unmodified(
                query.message,
                self.translation.get_text("Select"),
                reply_markup=get_delete_items_keyboard(
                    items, media_type, page, self.translation
                )
            )

        except Exception as e:
            logger.error(f"Error getting media list: {e}")
            await query.message.edit_text(
                self.translation.get_text("MediaListError")
            )

    async def _load_item(self, query, media_type: str, item_id: str):
        """Fetch one item, or tell the user why not and return None."""
        methods = MEDIA_METHODS.get(media_type)
        if not methods:
            await query.message.edit_text(
                self.translation.get_text("InvalidMediaType")
            )
            return None

        try:
            item = await getattr(self.media_service, methods[1])(item_id)
        except Exception as e:
            logger.error(f"Error getting item details: {e}")
            await query.message.edit_text(
                self.translation.get_text("ItemDetailsError")
            )
            return None

        if not item:
            await query.message.edit_text(
                self.translation.get_message("NoExist", subject=media_type)
            )
        return item

    async def _show_confirm(self, query, media_type: str, item_id: str):
        """Ask the user to confirm deleting one item."""
        item = await self._load_item(query, media_type, item_id)
        if not item:
            return

        keyboard = [
            [
                InlineKeyboardButton(
                    f"✅ {self.translation.get_text('Delete')}",
                    callback_data=f"delete_confirm_{media_type}_{item_id}"
                ),
                InlineKeyboardButton(
                    f"❌ {self.translation.get_text('StopDelete')}",
                    callback_data="delete_cancel"
                )
            ]
        ]

        await query.message.edit_text(
            self.translation.get_message("ThisDelete",
                                         subject=media_type,
                                         title=item["title"]
                                         ),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _delete(self, query, media_type: str, item_id: str):
        """Delete one item. The item is fetched again for its title."""
        item = await self._load_item(query, media_type, item_id)
        if not item:
            return

        try:
            success = await getattr(
                self.media_service, MEDIA_METHODS[media_type][2]
            )(item_id)
        except Exception as e:
            logger.error(f"Error deleting item: {e}")
            success = False

        key = "DeleteSuccess" if success else "DeleteFailed"
        await query.message.edit_text(
            self.translation.get_message(key,
                                         subject=media_type,
                                         title=item["title"]
                                         )
        )
