"""
Filename: handler.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Media handler module.

This module handles media-related commands (movies, TV shows, music).
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes
)

from src.config.settings import config
from src.utils.logger import get_logger, log_user_interaction
from src.bot.handlers.auth import require_auth
from src.services.rate_limit import rate_limit
from src.bot.keyboards import get_album_monitor_mode_keyboard
from src.services.media import MediaService
from src.services.translation import TranslationService
from src.services.preferences import PreferencesService

from .dispatch import (
    SEARCHING,
    SELECTING,
    QUALITY_SELECT,
    SEASON_SELECT,
    ALBUM_SELECT,
)
from .formatters import (
    show_result,
    show_list,
    show_list_detail,
    send_response,
)
from .season_picker import SeasonPickerMixin
from .album_picker import AlbumPickerMixin

logger = get_logger("addarr.media")


class MediaHandler(SeasonPickerMixin, AlbumPickerMixin):
    """Handler for media-related commands"""

    def __init__(self):
        self.media_service = MediaService()
        self.translation = TranslationService()

    def get_handler(self):
        """Get command handlers for media operations"""
        return [
            ConversationHandler(
                entry_points=[
                    CommandHandler("movie", self.handle_movie),
                    CommandHandler("series", self.handle_series),
                    CommandHandler("music", self.handle_music),
                    CallbackQueryHandler(self.handle_menu_callback, pattern="^menu_(movie|series|music)$")
                ],
                states={
                    SEARCHING: [
                        MessageHandler(
                            filters.TEXT & ~filters.COMMAND,
                            self.handle_search
                        ),
                        CallbackQueryHandler(
                            self.handle_menu_callback,
                            pattern="^menu_cancel$"
                        )
                    ],
                    SELECTING: [
                        CallbackQueryHandler(
                            self.handle_selection,
                            pattern="^select_"
                        ),
                        CallbackQueryHandler(
                            self.handle_navigation,
                            pattern="^nav_"
                        ),
                        CallbackQueryHandler(
                            self.handle_list_select,
                            pattern="^listsel_"
                        ),
                        CallbackQueryHandler(
                            self.handle_list_back,
                            pattern="^listback$"
                        ),
                        CallbackQueryHandler(
                            self.handle_list_page,
                            pattern="^listpage_"
                        ),
                        CallbackQueryHandler(
                            self.handle_view_toggle,
                            pattern="^viewtoggle$"
                        ),
                        CallbackQueryHandler(
                            self.handle_menu_callback,
                            pattern="^menu_cancel$"
                        )
                    ],
                    QUALITY_SELECT: [
                        CallbackQueryHandler(
                            self.handle_quality_selection,
                            pattern="^quality_"
                        ),
                        CallbackQueryHandler(
                            self.handle_menu_callback,
                            pattern="^menu_cancel$"
                        )
                    ],
                    SEASON_SELECT: [
                        CallbackQueryHandler(
                            self.handle_season_selection,
                            pattern="^season_"
                        ),
                        CallbackQueryHandler(
                            self.handle_season_confirm,
                            pattern="^season_confirm$"
                        ),
                        CallbackQueryHandler(
                            self.handle_menu_callback,
                            pattern="^menu_cancel$"
                        )
                    ],
                    ALBUM_SELECT: [
                        CallbackQueryHandler(
                            self.handle_album_monitor_mode,
                            pattern="^album_monitor_mode_"
                        ),
                        CallbackQueryHandler(
                            self.handle_album_selection,
                            pattern="^albumsel_"
                        ),
                        CallbackQueryHandler(
                            self.handle_menu_callback,
                            pattern="^menu_cancel$"
                        )
                    ]
                },
                fallbacks=[
                    CommandHandler("cancel", self.cancel_search),
                    CallbackQueryHandler(self.handle_menu_callback, pattern="^menu_cancel$")
                ],
                name="media_conversation",
                persistent=False,
                per_message=False,
            ),
        ]

    async def handle_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle menu callbacks from StartHandler"""
        if not update.callback_query:
            return ConversationHandler.END

        query = update.callback_query
        action = query.data.replace("menu_", "")

        # Handle cancel action
        if action == "cancel":
            await query.message.edit_text(
                self.translation.get_text("Canceled")
            )
            return ConversationHandler.END

        # Set search type in context
        context.user_data["search_type"] = action

        # Get translated prompt
        prompt = self.translation.get_text("Title")

        # Create keyboard with cancel button
        keyboard = [
            [InlineKeyboardButton(
                f"❌ {self.translation.get_text('Cancel')}",
                callback_data="menu_cancel"
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.edit_text(
            prompt,
            reply_markup=reply_markup
        )

        return SEARCHING

    @require_auth
    @rate_limit("search")
    async def handle_movie(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start movie search conversation"""
        if not update.effective_message or not update.effective_user:
            return ConversationHandler.END

        if config.get("radarr", {}).get("adminRestrictions", False):
            if update.effective_user.id not in config.get("admins", []):
                await update.message.reply_text("Access restricted to admins only.")
                return ConversationHandler.END

        log_user_interaction(logger, update.effective_user, "/movie")

        context.user_data["search_type"] = "movie"
        prompt = self.translation.get_text("Title")

        # Create keyboard with cancel button
        keyboard = [
            [InlineKeyboardButton(
                f"❌ {self.translation.get_text('Cancel')}",
                callback_data="menu_cancel"
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            prompt,
            reply_markup=reply_markup
        )
        return SEARCHING

    @require_auth
    @rate_limit("search")
    async def handle_series(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start series search conversation"""
        if not update.effective_message or not update.effective_user:
            return ConversationHandler.END

        if config.get("sonarr", {}).get("adminRestrictions", False):
            if update.effective_user.id not in config.get("admins", []):
                await update.message.reply_text("Access restricted to admins only.")
                return ConversationHandler.END

        log_user_interaction(logger, update.effective_user, "/series")

        context.user_data["search_type"] = "series"
        prompt = self.translation.get_text("Title")

        # Create keyboard with cancel button
        keyboard = [
            [InlineKeyboardButton(
                f"❌ {self.translation.get_text('Cancel')}",
                callback_data="menu_cancel"
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            prompt,
            reply_markup=reply_markup
        )
        return SEARCHING

    @require_auth
    @rate_limit("search")
    async def handle_music(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start music search conversation"""
        if not update.effective_message or not update.effective_user:
            return ConversationHandler.END

        if config.get("lidarr", {}).get("adminRestrictions", False):
            if update.effective_user.id not in config.get("admins", []):
                await update.message.reply_text("Access restricted to admins only.")
                return ConversationHandler.END

        log_user_interaction(logger, update.effective_user, "/music")

        context.user_data["search_type"] = "music"
        prompt = self.translation.get_text("Title")

        # Create keyboard with cancel button
        keyboard = [
            [InlineKeyboardButton(
                f"❌ {self.translation.get_text('Cancel')}",
                callback_data="menu_cancel"
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            prompt,
            reply_markup=reply_markup
        )
        return SEARCHING

    async def handle_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle search query"""
        if not update.effective_message:
            return ConversationHandler.END

        search_type = context.user_data.get("search_type")
        query = update.message.text

        log_user_interaction(
            logger,
            update.effective_user,
            f"search_{search_type}",
            query
        )

        try:
            # Use the appropriate service based on search type
            if search_type == "movie":
                results = await self.media_service.search_movies(query)
            elif search_type == "series":
                results = await self.media_service.search_series(query)
            elif search_type == "music":
                results = await self.media_service.search_music(query)
            else:
                await update.message.reply_text("❌ Invalid search type")
                return ConversationHandler.END

            if not results:
                await update.message.reply_text(
                    f"❌ No {search_type} found matching '{query}'"
                )
                return ConversationHandler.END

            # Store results and current index in context
            context.user_data["search_results"] = results
            context.user_data["current_index"] = 0

            # Branch on user's view preference
            user_id = update.effective_user.id
            view_mode = PreferencesService().get_view_mode(user_id)
            if view_mode == "list":
                context.user_data["list_page"] = 0
                await show_list(
                    update.message, results, 0, search_type
                )
            else:
                await show_result(
                    update.message, results[0], 0, len(results)
                )

            return SELECTING

        except Exception as e:
            logger.error(f"Error during search: {e}")
            await update.message.reply_text(
                "❌ An error occurred while searching.\n"
                "Please try again later."
            )
            return ConversationHandler.END

    async def handle_list_select(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle list item selection — show detail view."""
        if not update.callback_query:
            return ConversationHandler.END

        query = update.callback_query
        await query.answer()

        idx = int(query.data.replace("listsel_", ""))
        results = context.user_data.get("search_results", [])

        if 0 <= idx < len(results):
            context.user_data["current_index"] = idx
            await show_list_detail(query.message, results[idx])

        return SELECTING

    async def handle_list_back(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle back to list from detail view."""
        if not update.callback_query:
            return ConversationHandler.END

        query = update.callback_query
        await query.answer()

        results = context.user_data.get("search_results", [])
        page = context.user_data.get("list_page", 0)
        search_type = context.user_data.get("search_type", "movie")

        await show_list(query.message, results, page, search_type)
        return SELECTING

    async def handle_list_page(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle list page navigation."""
        if not update.callback_query:
            return ConversationHandler.END

        query = update.callback_query
        await query.answer()

        page_data = query.data.replace("listpage_", "")
        if page_data == "noop":
            return SELECTING

        page = int(page_data)
        context.user_data["list_page"] = page
        results = context.user_data.get("search_results", [])
        search_type = context.user_data.get("search_type", "movie")

        await show_list(query.message, results, page, search_type)
        return SELECTING

    async def handle_view_toggle(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle view toggle between card and list."""
        if not update.callback_query:
            return ConversationHandler.END

        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        new_mode = PreferencesService().toggle_view_mode(user_id)

        results = context.user_data.get("search_results", [])
        search_type = context.user_data.get("search_type", "movie")

        if new_mode == "list":
            current_index = context.user_data.get("current_index", 0)
            page = current_index // 5
            context.user_data["list_page"] = page
            await show_list(
                query.message, results, page, search_type
            )
        else:
            index = context.user_data.get("current_index", 0)
            await show_result(
                query.message, results[index], index, len(results)
            )

        return SELECTING

    async def handle_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle result selection"""
        if not update.callback_query:
            return ConversationHandler.END

        query = update.callback_query
        await query.answer()

        if query.data.startswith("select_"):
            selection = query.data.replace("select_", "")

            if selection == "cancel":
                if query.message.photo:
                    await query.message.edit_caption(
                        "🚫 Search cancelled.\nUse /start to see the main menu."
                    )
                else:
                    await query.message.edit_text(
                        "🚫 Search cancelled.\nUse /start to see the main menu."
                    )
                return ConversationHandler.END

            try:
                # Get selected result
                results = context.user_data.get("search_results", [])
                selected = next(
                    (r for r in results if r["id"] == selection),
                    None
                )

                if not selected:
                    await send_response(
                        query.message,
                        "❌ Error: Selection not found.\nPlease try your search again."
                    )
                    return ConversationHandler.END

                # Store selection for later use
                context.user_data["selected_media"] = selected

                # Store music routing data if present
                if selected.get("music_type"):
                    context.user_data["music_type"] = selected["music_type"]
                if selected.get("artist_id"):
                    context.user_data["artist_id"] = selected["artist_id"]
                if selected.get("album_id"):
                    context.user_data["album_id"] = selected["album_id"]

                # Get quality profiles based on media type
                search_type = context.user_data.get("search_type")

                # For music with album: prefix, strip it for the API call
                media_id = selected["id"]
                if search_type == "music" and media_id.startswith("album:"):
                    # Album/song selections use the artist_id for add_music
                    media_id = selected.get("artist_id", media_id[6:])

                if search_type == "movie":
                    result = await self.media_service.add_movie(media_id)
                elif search_type == "series":
                    result = await self.media_service.add_series(media_id)
                elif search_type == "music":
                    result = await self.media_service.add_music(media_id)

                # Handle quality profile selection
                if isinstance(result, dict) and result.get("type") == "quality_selection":
                    context.user_data["quality_data"] = result

                    # Create keyboard with quality profile buttons
                    keyboard = []
                    for profile in result["profiles"]:
                        keyboard.append([
                            InlineKeyboardButton(
                                profile["name"],
                                callback_data=f"quality_{profile['id']}"
                            )
                        ])
                    keyboard.append([
                        InlineKeyboardButton("❌ Cancel", callback_data="quality_cancel")
                    ])

                    message_text = (
                        f"Adding: {selected['title']}\n\n"
                        f"Please select a quality profile:"
                    )

                    if query.message.photo:
                        await query.message.edit_caption(
                            caption=message_text,
                            reply_markup=InlineKeyboardMarkup(keyboard)
                        )
                    else:
                        await query.message.edit_text(
                            text=message_text,
                            reply_markup=InlineKeyboardMarkup(keyboard)
                        )
                    return QUALITY_SELECT
                else:
                    success, message = result
                    await send_response(
                        query.message,
                        f"{'✅' if success else '❌'} {message}"
                    )
                    return ConversationHandler.END

            except Exception as e:
                logger.error(f"Error adding media: {e}")
                await send_response(
                    query.message,
                    f"❌ An error occurred: {str(e)}"
                )
                return ConversationHandler.END

    async def handle_quality_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle quality profile selection"""
        if not update.callback_query:
            return ConversationHandler.END

        query = update.callback_query
        await query.answer()

        if query.data == "quality_cancel":
            await send_response(
                query.message,
                "🚫 Operation cancelled.\nUse /start to see the main menu."
            )
            return ConversationHandler.END

        try:
            # Get quality selection data
            quality_data = context.user_data.get("quality_data")
            selected = context.user_data.get("selected_media")
            search_type = context.user_data.get("search_type")

            if not quality_data or not selected:
                await send_response(
                    query.message,
                    "❌ Error: Selection data not found.\nPlease try your search again."
                )
                return ConversationHandler.END

            # Get selected profile ID
            profile_id = int(query.data.replace("quality_", ""))
            context.user_data["selected_profile_id"] = profile_id
            context.user_data["selected_root_folder"] = quality_data["root_folder"]

            # For series, show season selection
            if search_type == "series" and "seasons" in quality_data:
                seasons = quality_data["seasons"]
                keyboard = [
                    # Add season selection mode buttons
                    [InlineKeyboardButton("👁️ Monitor All", callback_data="season_monitor_all")],
                    [InlineKeyboardButton("📺 All Seasons", callback_data="season_all")],
                    [InlineKeyboardButton("🔄 Future Seasons", callback_data="season_future_seasons")],
                    [InlineKeyboardButton("⏩ Future Episodes", callback_data="season_future_episodes")]
                ]

                # Add individual season buttons
                for season in seasons:
                    season_num = season.get("seasonNumber")
                    if season_num is not None:
                        keyboard.append([
                            InlineKeyboardButton(
                                f"Season {season_num}",
                                callback_data=f"season_{season_num}"
                            )
                        ])

                # Add confirm and cancel buttons
                keyboard.extend([
                    [InlineKeyboardButton("✅ Confirm Selection", callback_data="season_confirm")],
                    [InlineKeyboardButton("❌ Cancel", callback_data="select_cancel")]
                ])

                context.user_data["selected_seasons"] = set()  # Store selected seasons
                context.user_data["future_mode"] = None  # Track future mode
                context.user_data["monitor_all"] = False  # Track monitor all mode

                await send_response(
                    query.message,
                    f"Adding: {selected['title']}\n\n"
                    "Select seasons to download:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return SEASON_SELECT

            # For music, branch based on music_type
            if search_type == "music":
                music_type = context.user_data.get("music_type", "artist")

                if music_type == "artist":
                    # Artist: show album monitor mode prompt
                    await send_response(
                        query.message,
                        f"Adding: {selected['title']}\n\n"
                        "How would you like to monitor albums?",
                        reply_markup=get_album_monitor_mode_keyboard()
                    )
                    return ALBUM_SELECT

                # Album or song: add with pre-selected album
                album_id = context.user_data.get("album_id")
                artist_id = context.user_data.get("artist_id", selected["id"])
                albums_to_monitor = [album_id] if album_id else None

                success, message = await self.media_service.add_music_with_profile(
                    artist_id, profile_id, quality_data["root_folder"],
                    albums_to_monitor=albums_to_monitor,
                )

                await send_response(
                    query.message,
                    f"{'✅' if success else '❌'} {message}"
                )
                return ConversationHandler.END

            # For other media types, proceed with adding
            success, message = await self._add_media_with_profile(
                search_type, selected, profile_id, quality_data["root_folder"]
            )

            await send_response(
                query.message,
                f"{'✅' if success else '❌'} {message}"
            )
            return ConversationHandler.END

        except Exception as e:
            logger.error(f"Error handling quality selection: {e}")
            await send_response(
                query.message,
                "❌ An error occurred while processing your selection.\n"
                "Please try again."
            )
            return ConversationHandler.END

    async def _add_media_with_profile(self, media_type: str, selected: dict, profile_id: int, root_folder: str) -> tuple[bool, str]:
        """Add media with selected profile"""
        if media_type == "movie":
            return await self.media_service.add_movie_with_profile(
                selected["id"], profile_id, root_folder
            )
        elif media_type == "series":
            return await self.media_service.add_series_with_profile(
                selected["id"], profile_id, root_folder
            )
        elif media_type == "music":
            return await self.media_service.add_music_with_profile(
                selected["id"], profile_id, root_folder
            )
        return False, "Invalid media type"

    async def cancel_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel the search process"""
        log_user_interaction(logger, update.effective_user, "cancel_search")

        # Handle both direct commands and callback queries
        if update.callback_query:
            await send_response(
                update.callback_query.message,
                "🚫 Search cancelled.\nUse /start to see the main menu."
            )
        elif update.message:
            await update.message.reply_text(
                "🚫 Search cancelled.\nUse /start to see the main menu."
            )
        return ConversationHandler.END

    async def handle_navigation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle navigation between search results"""
        if not update.callback_query:
            return ConversationHandler.END

        query = update.callback_query
        await query.answer()

        # Extract direction and current index from callback data
        _, direction, current = query.data.split("_")
        current = int(current)

        # Get stored results
        results = context.user_data.get("search_results", [])

        # Calculate new index
        if direction == "next":
            new_index = current + 1
        else:  # prev
            new_index = current - 1

        # Validate index
        if 0 <= new_index < len(results):
            context.user_data["current_index"] = new_index
            # Show the new result
            await show_result(query.message, results[new_index], new_index, len(results))
            return SELECTING
        else:
            logger.error(f"Invalid navigation index: {new_index}")
            return SELECTING
