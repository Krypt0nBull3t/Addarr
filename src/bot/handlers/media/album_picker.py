"""
Filename: album_picker.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Album picker mixin for music album selection flow.

Provides handle_album_monitor_mode, handle_album_selection, and
handle_album_confirm methods that MediaHandler inherits via mixin.
"""

from telegram import Update
from telegram.ext import ConversationHandler, ContextTypes

from src.utils.logger import get_logger
from src.bot.keyboards import get_album_selection_keyboard
from .dispatch import ALBUM_SELECT
from .formatters import send_response

logger = get_logger("addarr.media.album_picker")


class AlbumPickerMixin:
    """Mixin providing album selection flow for music.

    Expects self.media_service to be available (provided by MediaHandler.__init__).
    """

    async def handle_album_monitor_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle album monitor mode selection (all vs pick specific)"""
        if not update.callback_query:
            return ConversationHandler.END

        query = update.callback_query
        await query.answer()

        action = query.data.replace("album_monitor_mode_", "")

        if action == "all":
            # Add artist monitoring all albums
            selected = context.user_data.get("selected_media")
            profile_id = context.user_data.get("selected_profile_id")
            root_folder = context.user_data.get("selected_root_folder")

            try:
                success, message = await self.media_service.add_music_with_profile(
                    selected["id"], profile_id, root_folder
                )
                await send_response(
                    query.message,
                    f"{'✅' if success else '❌'} {message}"
                )
            except Exception as e:
                logger.error(f"Error adding artist: {e}")
                await send_response(
                    query.message,
                    self.translation.get_text("ArtistAddError")
                )
            return ConversationHandler.END

        elif action == "pick":
            # Fetch artist albums and show picker
            selected = context.user_data.get("selected_media")
            try:
                albums = await self.media_service.get_artist_albums(selected["id"])
                context.user_data["artist_albums"] = albums
                context.user_data["selected_albums"] = set()
                context.user_data["future_albums"] = False

                keyboard = get_album_selection_keyboard(albums, set(), False)
                await send_response(
                    query.message,
                    f"Adding: {selected['title']}\n\n"
                    "Select albums to monitor:",
                    reply_markup=keyboard
                )
                return ALBUM_SELECT
            except Exception as e:
                logger.error(f"Error fetching albums: {e}")
                await send_response(
                    query.message,
                    self.translation.get_text("AlbumFetchError")
                )
                return ConversationHandler.END

        return ConversationHandler.END

    async def handle_album_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle album selection toggles"""
        if not update.callback_query:
            return ConversationHandler.END

        query = update.callback_query
        await query.answer()

        action = query.data.replace("albumsel_", "")
        albums = context.user_data.get("artist_albums", [])
        selected_albums = context.user_data.get("selected_albums", set())
        future_albums = context.user_data.get("future_albums", False)

        if action == "cancel":
            await send_response(
                query.message,
                "🚫 Search cancelled.\nUse /start to see the main menu."
            )
            return ConversationHandler.END

        if action == "confirm":
            return await self.handle_album_confirm(update, context)

        if action == "monitor_all":
            # Auto-confirm with all albums
            selected = context.user_data.get("selected_media")
            profile_id = context.user_data.get("selected_profile_id")
            root_folder = context.user_data.get("selected_root_folder")

            try:
                success, message = await self.media_service.add_music_with_profile(
                    selected["id"], profile_id, root_folder
                )
                await send_response(
                    query.message,
                    f"{'✅' if success else '❌'} {message}"
                )
            except Exception as e:
                logger.error(f"Error adding artist: {e}")
                await send_response(
                    query.message,
                    self.translation.get_text("ArtistAddError")
                )
            return ConversationHandler.END

        if action == "all":
            # Toggle all albums
            all_ids = {a["album_id"] for a in albums}
            if selected_albums == all_ids:
                selected_albums.clear()
            else:
                selected_albums.clear()
                selected_albums.update(all_ids)
        elif action == "future":
            future_albums = not future_albums
        else:
            # Toggle individual album
            if action in selected_albums:
                selected_albums.remove(action)
            else:
                selected_albums.add(action)

        context.user_data["selected_albums"] = selected_albums
        context.user_data["future_albums"] = future_albums

        # Rebuild keyboard
        new_markup = get_album_selection_keyboard(
            albums, selected_albums, future_albums
        )
        if query.message.reply_markup.to_dict() != new_markup.to_dict():
            await query.message.edit_reply_markup(reply_markup=new_markup)

        return ALBUM_SELECT

    async def handle_album_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle album selection confirmation"""
        if not update.callback_query:
            return ConversationHandler.END

        query = update.callback_query
        await query.answer()

        try:
            selected = context.user_data.get("selected_media")
            profile_id = context.user_data.get("selected_profile_id")
            root_folder = context.user_data.get("selected_root_folder")
            selected_albums = list(context.user_data.get("selected_albums", set()))
            future_albums = context.user_data.get("future_albums", False)

            kwargs = {}
            if selected_albums:
                kwargs["albums_to_monitor"] = selected_albums
            if future_albums:
                kwargs["future_albums"] = True

            success, message = await self.media_service.add_music_with_profile(
                selected["id"], profile_id, root_folder,
                **kwargs,
            )

            await send_response(
                query.message,
                f"{'✅' if success else '❌'} {message}"
            )
            return ConversationHandler.END

        except Exception as e:
            logger.error(f"Error confirming album selection: {e}")
            await send_response(
                query.message,
                self.translation.get_text("SelectionProcessError")
            )
            return ConversationHandler.END
