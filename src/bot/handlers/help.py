"""
Filename: help.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Help handler module.

This module provides help and command information to users.
"""

from telegram import Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from src.utils.logger import get_logger, log_user_interaction
from src.bot.handlers.auth import require_auth
from src.bot.keyboards import get_main_menu_keyboard
from src.config.settings import config
from src.services.translation import TranslationService
from src import __version__

logger = get_logger("addarr.help")


class HelpHandler:
    """Handler for help commands"""

    def __init__(self):
        self.translation = TranslationService()

    def get_handler(self):
        """Get the command handler for help"""
        return [
            CommandHandler("help", self.show_help),
            CallbackQueryHandler(self.handle_back, pattern="^menu_back$")
        ]

    def _build_help_text(self):
        """Build help text from translations, filtered by enabled services."""
        t = self.translation
        sections = [t.get_text("HelpHeader"), "", t.get_text("HelpBasicCommands")]

        if config.get("radarr", {}).get("enable"):
            sections.append(t.get_text("HelpMediaMovies"))
        if config.get("sonarr", {}).get("enable"):
            sections.append(t.get_text("HelpMediaSeries"))
        if config.get("lidarr", {}).get("enable"):
            sections.append(t.get_text("HelpMediaMusic"))

        if config.get("transmission", {}).get("enable", False):
            sections.append(t.get_text("HelpDownloadTransmission"))
        if config.get("sabnzbd", {}).get("enable", False):
            sections.append(t.get_text("HelpDownloadSabnzbd"))

        if config.get("bazarr", {}).get("enable", False):
            sections.append(t.get_text("HelpSubtitlesBazarr"))

        sections.append("")
        sections.append(t.get_text("HelpVersion", version=__version__))
        sections.append(t.get_text("HelpFooter"))

        return "\n".join(sections)

    @require_auth
    async def show_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help message with available commands"""
        if not update.effective_user:  # pragma: no cover
            return

        user = update.effective_user
        log_user_interaction(logger, user, "/help")

        help_text = self._build_help_text()

        if update.callback_query:
            await update.callback_query.message.edit_text(
                help_text,
                parse_mode='Markdown',
                disable_web_page_preview=True,
            )
        else:
            await update.message.reply_text(
                help_text,
                parse_mode='Markdown',
                disable_web_page_preview=True,
            )

    @require_auth
    async def handle_back(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle back button press"""
        if not update.callback_query:
            return

        query = update.callback_query
        await query.answer()

        log_user_interaction(logger, query.from_user, "menu_back")

        # Get translated welcome message
        welcome_text = self.translation.get_text("Start chatting")

        await query.message.edit_text(
            welcome_text,
            reply_markup=get_main_menu_keyboard()
        )
