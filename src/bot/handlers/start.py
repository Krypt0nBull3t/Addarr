"""
Filename: start.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Start handler module.

This module handles the main entry point and menu for the bot.
"""

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
)
from src.utils.logger import get_logger, log_user_interaction
from src.bot.handlers.auth import require_auth
from src.bot.handlers.calendar import CalendarHandler
from src.bot.handlers.help import HelpHandler
from src.bot.handlers.system import SystemHandler
from src.bot.handlers.delete import DeleteHandler
from src.bot.keyboards import get_main_menu_keyboard, get_library_menu_keyboard
from src.services.translation import TranslationService

logger = get_logger("addarr.start")
logger.info("Start handler module initialized")


class StartHandler:
    """Handler for start command and main menu"""

    def __init__(self):
        self.calendar_handler = CalendarHandler()
        self.help_handler = HelpHandler()
        self.system_handler = SystemHandler()
        self.delete_handler = DeleteHandler()
        self.translation = TranslationService()

    def get_handler(self):
        """Get the command handlers.

        Plain handlers, no conversation: menu_movie/series/music start
        MediaHandler's conversation, menu_settings SettingsHandler's and
        menu_back is HelpHandler's. Register these after those conversations,
        so a Cancel tap inside one of them ends that conversation.
        """
        return [
            CommandHandler("start", self.show_menu),
            CallbackQueryHandler(
                self.handle_menu_selection,
                pattern="^menu_(cancel|status|upcoming|library|help|delete)$",
            ),
        ]

    @require_auth
    async def show_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show the main menu"""
        log_user_interaction(logger, update.effective_user, "/start")

        welcome_text = self.translation.get_text("mainMenu")

        if update.effective_message:
            await update.effective_message.reply_text(
                welcome_text,
                reply_markup=get_main_menu_keyboard()
            )

    @require_auth
    async def handle_menu_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle menu button selections"""
        logger.info("handle_menu_selection called")

        if not update.callback_query:
            logger.warning("Received menu selection without callback query")
            return

        query = update.callback_query
        logger.info(f"Received callback query with data: {query.data}")

        await query.answer()

        action = query.data.replace("menu_", "")
        user = query.from_user

        logger.info(f"Menu button pressed - Action: {action}, User: {user.first_name} (ID: {user.id})")
        log_user_interaction(logger, user, f"menu_{action}")

        if action == "cancel":
            logger.info(f"Cancel action triggered by user {user.first_name} (ID: {user.id})")
            if context.user_data:
                context.user_data.clear()
            await query.message.edit_text(
                self.translation.get_text("Canceled")
            )
            return

        if action == "upcoming":
            await self.calendar_handler.show_upcoming(update, context)
            return

        if action == "library":
            await query.message.edit_text(
                self.translation.get_text("LibraryPrompt"),
                reply_markup=get_library_menu_keyboard()
            )
            return

        if action == "status":
            await self.system_handler.show_status(update, context)
        elif action == "help":
            await self.help_handler.show_help(update, context)
        elif action == "delete":
            keyboard = self.delete_handler.get_delete_keyboard()
            await query.message.edit_text(
                self.translation.get_text(
                    "DeletePrompt",
                    default="Select what you want to delete"
                ),
                reply_markup=keyboard,
            )
        else:
            logger.warning(f"Unknown menu action '{action}' from user {user.first_name} (ID: {user.id})")
