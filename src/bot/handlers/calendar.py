"""
Filename: calendar.py
Author: Addarr Contributors
Created Date: 2026-03-03
Description: Calendar/upcoming releases handler module.
"""

from telegram import Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from src.utils.logger import get_logger, log_user_interaction
from src.bot.handlers.auth import require_auth
from src.bot.keyboards import (
    get_calendar_keyboard,
    get_calendar_items_keyboard,
    get_main_menu_keyboard,
)
from src.services.media import MediaService
from src.services.translation import TranslationService

logger = get_logger("addarr.calendar")


class CalendarHandler:
    """Handler for upcoming releases calendar"""

    def __init__(self):
        self.media_service = MediaService()
        self.translation = TranslationService()

    def get_handler(self):
        """Get calendar command handlers"""
        return [
            CommandHandler("upcoming", self.show_upcoming),
            CallbackQueryHandler(
                self.handle_calendar_action, pattern="^cal_"
            ),
        ]

    @require_auth
    async def show_upcoming(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Show upcoming releases with inline keyboard."""
        if not update.effective_user:  # pragma: no cover
            return

        log_user_interaction(logger, update.effective_user, "/upcoming")

        days = context.user_data.get("cal_days", 7)
        context.user_data["cal_days"] = days

        items = await self.media_service.get_upcoming(days)
        context.user_data["cal_items"] = items

        text, keyboard = self._build_response(items, days)

        if update.callback_query:
            await update.callback_query.message.edit_text(
                text, reply_markup=keyboard
            )
        else:
            await update.message.reply_text(text, reply_markup=keyboard)

    @require_auth
    async def handle_calendar_action(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle calendar callback button presses."""
        if not update.callback_query:
            return

        query = update.callback_query
        data = query.data

        log_user_interaction(logger, query.from_user, data)

        if data.startswith("cal_period_"):
            await self._handle_period(query, context)
        elif data.startswith("cal_page_"):
            await self._handle_page(query, context)
        elif data == "cal_refresh":
            await self._handle_refresh(query, context)
        elif data == "cal_back":
            await self._handle_back(query)
        elif data.startswith("cal_add_"):
            await self._handle_add(query, context)
        else:
            await query.answer()

    async def _handle_period(self, query, context):
        """Change the calendar period and re-fetch."""
        days = int(query.data.split("_")[-1])
        context.user_data["cal_days"] = days

        items = await self.media_service.get_upcoming(days)
        context.user_data["cal_items"] = items

        text, keyboard = self._build_response(items, days)
        await query.message.edit_text(text, reply_markup=keyboard)
        await query.answer()

    async def _handle_page(self, query, context):
        """Show a different page of cached calendar items."""
        page = int(query.data.split("_")[-1])
        items = context.user_data.get("cal_items", [])
        days = context.user_data.get("cal_days", 7)

        text, keyboard = self._build_response(items, days, page)
        await query.message.edit_text(text, reply_markup=keyboard)
        await query.answer()

    async def _handle_refresh(self, query, context):
        """Clear cache and re-fetch calendar data."""
        days = context.user_data.get("cal_days", 7)

        items = await self.media_service.get_upcoming(days)
        context.user_data["cal_items"] = items

        text, keyboard = self._build_response(items, days)
        await query.message.edit_text(text, reply_markup=keyboard)
        await query.answer()

    async def _handle_back(self, query):
        """Return to the main menu."""
        await query.message.edit_text(
            "\U0001f3e0 Main Menu",
            reply_markup=get_main_menu_keyboard(),
        )
        await query.answer()

    async def _handle_add(self, query, context):
        """Quick-add media from calendar using first root folder and profile."""
        # Parse: cal_add_movie_12345 or cal_add_episode_67890
        parts = query.data.split("_")
        media_type = parts[2]
        media_id = parts[3]

        try:
            if media_type == "movie":
                root_folders = await self.media_service.radarr.get_root_folders()
                profiles = await self.media_service.radarr.get_quality_profiles()
                success, msg = await self.media_service.add_movie_with_profile(
                    media_id, profiles[0]["id"], root_folders[0]
                )
            elif media_type == "episode":
                root_folders = await self.media_service.sonarr.get_root_folders()
                profiles = await self.media_service.sonarr.get_quality_profiles()
                success, msg = await self.media_service.add_series_with_profile(
                    media_id, profiles[0]["id"], root_folders[0]
                )
            else:
                await query.answer("Unknown media type")
                return

            if success:
                await query.answer(
                    self.translation.get_text("CalendarAddSuccess")
                )
            else:
                await query.answer(
                    self.translation.get_text("CalendarAddFailed")
                )
        except Exception as e:
            logger.error(f"Error adding media from calendar: {e}")
            await query.answer(
                self.translation.get_text("CalendarAddFailed")
            )

    def _build_response(self, items, days, page=0):
        """Build calendar text and keyboard from items."""
        if items:
            title = self.translation.get_text("CalendarTitle")
            text = (
                f"\U0001f4c5 {title}\n\n"
                f"{len(items)} releases \u2014 {days} days"
            )
            keyboard = get_calendar_items_keyboard(items, page, days)
        else:
            text = (
                f"\U0001f4c5 {self.translation.get_text('CalendarTitle')}"
                f"\n\n{self.translation.get_text('CalendarEmpty')}"
            )
            keyboard = get_calendar_keyboard(days)
        return text, keyboard
