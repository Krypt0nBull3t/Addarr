"""
Filename: bazarr.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Telegram command handler for Bazarr subtitle operations.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from typing import Dict, List

from src.services.bazarr import BazarrService
from src.services.translation import TranslationService
from src.bot.handlers.auth import require_auth
from src.bot.states import States
from src.utils.logger import get_logger

logger = get_logger("addarr.handlers.bazarr")

MAX_DISPLAY_ITEMS = 10


def _format_missing_subs(item: Dict) -> str:
    """Format the missing subtitles portion of a display line."""
    missing = item.get("missing_subtitles", [])
    if not missing:
        return "None"
    return ", ".join(s.get("name", "?") for s in missing)


class BazarrHandler:
    """Handler for Bazarr subtitle commands."""

    def __init__(self):
        self.service = BazarrService()
        self.translation = TranslationService()

    def get_handler(self) -> List:
        """Get the command and callback handlers."""
        conv_handler = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(
                    self.prompt_search, pattern=r"^bazarr_search$"
                ),
            ],
            states={
                States.BAZARR_SEARCH: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.handle_search,
                    ),
                ],
            },
            fallbacks=[
                CallbackQueryHandler(
                    self.cancel, pattern=r"^bazarr_cancel$"
                ),
                CommandHandler("cancel", self.cancel),
            ],
        )

        return [
            CommandHandler("subtitles", self.subtitles_menu),
            conv_handler,
            CallbackQueryHandler(
                self.subtitles_menu, pattern=r"^bazarr_menu$"
            ),
            CallbackQueryHandler(
                self.wanted_movies, pattern=r"^bazarr_wanted_movies$"
            ),
            CallbackQueryHandler(
                self.wanted_episodes, pattern=r"^bazarr_wanted_episodes$"
            ),
            CallbackQueryHandler(
                self.search_subtitles_trigger,
                pattern=r"^bazarr_sub_(movie|episode)_",
            ),
            CallbackQueryHandler(
                self.cancel, pattern=r"^bazarr_cancel$"
            ),
        ]

    def _get_menu_keyboard(self) -> InlineKeyboardMarkup:
        """Build the subtitles menu keyboard."""
        t = self.translation
        keyboard = [
            [InlineKeyboardButton(
                t.get_text("BazarrSearchButton"),
                callback_data="bazarr_search",
            )],
            [InlineKeyboardButton(
                t.get_text("BazarrWantedMoviesButton"),
                callback_data="bazarr_wanted_movies",
            )],
            [InlineKeyboardButton(
                t.get_text("BazarrWantedEpisodesButton"),
                callback_data="bazarr_wanted_episodes",
            )],
            [InlineKeyboardButton(
                t.get_text("BazarrCancelButton"),
                callback_data="bazarr_cancel",
            )],
        ]
        return InlineKeyboardMarkup(keyboard)

    @require_auth
    async def subtitles_menu(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /subtitles command or bazarr_menu callback."""
        t = self.translation

        if not self.service.is_enabled():
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.edit_message_text(
                    t.get_text("BazarrNotEnabled")
                )
            else:
                await update.message.reply_text(
                    t.get_text("BazarrNotEnabled")
                )
            return

        keyboard = self._get_menu_keyboard()
        menu_text = t.get_text("BazarrMenu")

        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                menu_text, reply_markup=keyboard
            )
        else:
            await update.message.reply_text(
                menu_text, reply_markup=keyboard
            )

    async def prompt_search(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Prompt user to enter a search term."""
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            self.translation.get_text("BazarrSearchPrompt")
        )
        return States.BAZARR_SEARCH

    async def handle_search(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle search text from user."""
        text = update.message.text
        if not text:
            return ConversationHandler.END

        results = await self.service.search(text.strip())

        if not results:
            await update.message.reply_text(
                self.translation.get_text("BazarrNoResults")
            )
            return ConversationHandler.END

        lines = []
        for movie in results[:MAX_DISPLAY_ITEMS]:
            title = movie.get("title", "Unknown")
            missing_names = _format_missing_subs(movie)
            lines.append(f"- *{title}*\n  Missing: {missing_names}")

        await update.message.reply_text("\n".join(lines))
        return ConversationHandler.END

    async def wanted_movies(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Show movies missing subtitles."""
        await update.callback_query.answer()

        movies = await self.service.get_wanted_movies()

        if not movies:
            await update.callback_query.edit_message_text(
                self.translation.get_text("BazarrWantedEmpty")
            )
            return

        lines = []
        for movie in movies[:MAX_DISPLAY_ITEMS]:
            title = movie.get("title", "Unknown")
            missing_names = _format_missing_subs(movie)
            lines.append(f"- *{title}*\n  Missing: {missing_names}")

        await update.callback_query.edit_message_text("\n".join(lines))

    async def wanted_episodes(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Show episodes missing subtitles."""
        await update.callback_query.answer()

        episodes = await self.service.get_wanted_episodes()

        if not episodes:
            await update.callback_query.edit_message_text(
                self.translation.get_text("BazarrWantedEmpty")
            )
            return

        lines = []
        for ep in episodes[:MAX_DISPLAY_ITEMS]:
            series = ep.get("seriesTitle", "Unknown")
            ep_num = ep.get("episode_number", "?")
            ep_title = ep.get("episodeTitle", "")
            missing_names = _format_missing_subs(ep)
            lines.append(
                f"- *{series}* {ep_num} - {ep_title}\n"
                f"  Missing: {missing_names}"
            )

        await update.callback_query.edit_message_text("\n".join(lines))

    async def search_subtitles_trigger(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Trigger subtitle search for a movie or episode."""
        await update.callback_query.answer()
        data = update.callback_query.data
        t = self.translation

        # Parse callback: bazarr_sub_movie_{id}_{lang}
        parts = data.split("_")
        media_type = parts[2]  # "movie" or "episode"
        media_id = int(parts[3])
        language = parts[4]

        if media_type == "movie":
            success = await self.service.search_movie_subtitles(
                media_id, language
            )
        else:
            # For episodes, id encodes series_id and episode_id
            success = await self.service.search_episode_subtitles(
                media_id, media_id, language
            )

        if success:
            await update.callback_query.edit_message_text(
                t.get_text("BazarrSearchTriggered")
            )
        else:
            await update.callback_query.edit_message_text(
                t.get_text("BazarrSearchFailed")
            )

    async def cancel(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Cancel the current operation."""
        t = self.translation
        msg = t.get_text("BazarrCancelled")

        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(msg)
        else:
            await update.message.reply_text(msg)

        return ConversationHandler.END
