"""
Filename: preferences.py
Author: Addarr Contributors
Created Date: 2026-03-02
Description: Preferences handler module.

This module provides user preference management via Telegram commands.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from src.utils.logger import get_logger, log_user_interaction
from src.bot.handlers.auth import require_auth
from src.services.preferences import PreferencesService
from src.services.translation import TranslationService

logger = get_logger("addarr.preferences")


class PreferencesHandler:
    """Handler for user preferences commands."""

    def __init__(self):
        self.prefs = PreferencesService()
        self.translation = TranslationService()

    def get_handler(self):
        """Get command handlers for preferences."""
        return [
            CommandHandler("preferences", self.show_preferences),
            CallbackQueryHandler(
                self.handle_toggle,
                pattern="^pref_toggle_view$"
            ),
        ]

    @require_auth
    async def show_preferences(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Show current preferences with toggle buttons."""
        user_id = update.effective_user.id
        log_user_interaction(logger, update.effective_user, "/preferences")

        view_mode = self.prefs.get_view_mode(user_id)
        mode_label = (
            "\U0001f4cb List View"
            if view_mode == "list"
            else "\U0001f0cf Card View"
        )

        text = (
            "\u2699\ufe0f *Your Preferences*\n\n"
            f"Search results: {mode_label}"
        )

        toggle_label = "Card" if view_mode == "list" else "List"
        keyboard = [
            [InlineKeyboardButton(
                f"\U0001f504 Switch to {toggle_label} View",
                callback_data="pref_toggle_view"
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    @require_auth
    async def handle_toggle(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle view mode toggle from preferences menu."""
        if not update.callback_query:
            return

        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        new_mode = self.prefs.toggle_view_mode(user_id)
        mode_label = (
            "\U0001f4cb List View"
            if new_mode == "list"
            else "\U0001f0cf Card View"
        )

        text = (
            "\u2699\ufe0f *Your Preferences*\n\n"
            f"Search results: {mode_label}"
        )

        toggle_label = "Card" if new_mode == "list" else "List"
        keyboard = [
            [InlineKeyboardButton(
                f"\U0001f504 Switch to {toggle_label} View",
                callback_data="pref_toggle_view"
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.edit_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
