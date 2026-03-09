"""
Filename: season_picker.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Season picker mixin for TV series season selection flow.

Provides handle_season_selection and handle_season_confirm methods
that MediaHandler inherits via mixin.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, ContextTypes

from src.utils.logger import get_logger
from .dispatch import SEASON_SELECT
from .formatters import send_response

logger = get_logger("addarr.media.season_picker")


class SeasonPickerMixin:
    """Mixin providing season selection flow for TV series.

    Expects self.media_service to be available (provided by MediaHandler.__init__).
    """

    async def handle_season_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle season selection"""
        if not update.callback_query:
            return ConversationHandler.END

        query = update.callback_query
        await query.answer()

        if query.data == "select_cancel":
            await send_response(
                query.message,
                "🚫 Search cancelled.\nUse /start to see the main menu."
            )
            return ConversationHandler.END

        if query.data == "season_confirm":
            return await self.handle_season_confirm(update, context)

        quality_data = context.user_data.get("quality_data", {})
        seasons = quality_data.get("seasons", [])
        selected_seasons = context.user_data.get("selected_seasons", set())
        future_mode = context.user_data.get("future_mode", None)

        action = query.data.replace("season_", "")

        # Handle special actions
        if action == "monitor_all":
            # Toggle monitor all mode
            context.user_data["monitor_all"] = not context.user_data.get("monitor_all", False)
            if context.user_data["monitor_all"]:
                # When enabling monitor all, select all seasons and enable future monitoring
                all_season_numbers = {s.get("seasonNumber") for s in seasons if s.get("seasonNumber") is not None}
                selected_seasons.update(all_season_numbers)
                future_mode = "future_seasons"
                context.user_data["selected_seasons"] = selected_seasons
                context.user_data["future_mode"] = future_mode
                # Automatically submit
                return await self.handle_season_confirm(update, context)
            else:
                selected_seasons.clear()
                future_mode = None
        elif action == "all":
            # Toggle between all seasons and no seasons
            all_season_numbers = {s.get("seasonNumber") for s in seasons if s.get("seasonNumber") is not None}
            if selected_seasons == all_season_numbers:
                # If all seasons are selected, clear selection
                selected_seasons.clear()
                future_mode = None
            else:
                # Otherwise, select all seasons
                selected_seasons.clear()
                selected_seasons.update(all_season_numbers)
                future_mode = "all"
        elif action == "future_seasons":
            # Toggle future seasons mode
            future_mode = "future_seasons" if future_mode != "future_seasons" else None
        elif action == "future_episodes":
            # Toggle future episodes mode
            future_mode = "future_episodes" if future_mode != "future_episodes" else None
        else:
            try:
                # Toggle individual season
                season_num = int(action)
                if season_num in selected_seasons:
                    selected_seasons.remove(season_num)
                else:
                    selected_seasons.add(season_num)
            except ValueError:
                pass

        # Create new keyboard with updated button states
        keyboard = [
            [InlineKeyboardButton(
                f"{'✅ ' if context.user_data.get('monitor_all') else ''}👁️ Monitor All",
                callback_data="season_monitor_all"
            )],
            [InlineKeyboardButton(
                f"{'✅ ' if future_mode == 'all' else ''}📺 All Seasons",
                callback_data="season_all"
            )],
            [InlineKeyboardButton(
                f"{'✅ ' if future_mode == 'future_seasons' else ''}🔄 Future Seasons",
                callback_data="season_future_seasons"
            )],
            [InlineKeyboardButton(
                f"{'✅ ' if future_mode == 'future_episodes' else ''}⏩ Future Episodes",
                callback_data="season_future_episodes"
            )]
        ]

        # Add season buttons with selection status
        for season in seasons:
            season_number = season.get("seasonNumber")
            if season_number is not None:
                # Show checkmark if season is selected or if in "all" mode
                is_selected = (season_number in selected_seasons
                               or future_mode == "all")
                keyboard.append([
                    InlineKeyboardButton(
                        f"{'✅ ' if is_selected else ''}Season {season_number}",
                        callback_data=f"season_{season_number}"
                    )
                ])

        # Add confirm and cancel buttons
        keyboard.extend([
            [InlineKeyboardButton("✅ Confirm Selection", callback_data="season_confirm")],
            [InlineKeyboardButton("❌ Cancel", callback_data="select_cancel")]
        ])

        # Store updated selection and mode
        context.user_data["selected_seasons"] = selected_seasons
        context.user_data["future_mode"] = future_mode

        # Only update if keyboard has changed
        new_markup = InlineKeyboardMarkup(keyboard)
        if query.message.reply_markup.to_dict() != new_markup.to_dict():
            await query.message.edit_reply_markup(reply_markup=new_markup)

        return SEASON_SELECT

    async def handle_season_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle season selection confirmation"""
        if not update.callback_query:
            return ConversationHandler.END

        query = update.callback_query
        await query.answer()

        try:
            selected = context.user_data.get("selected_media")
            profile_id = context.user_data.get("selected_profile_id")
            root_folder = context.user_data.get("selected_root_folder")
            selected_seasons = list(context.user_data.get("selected_seasons", set()))
            future_mode = context.user_data.get("future_mode")
            monitor_all = context.user_data.get("monitor_all", False)

            # Format seasons data based on selection mode
            if monitor_all:
                # Monitor everything (current and future)
                seasons_data = [{"seasonNumber": season.get("seasonNumber"), "monitored": True}
                                for season in context.user_data.get("quality_data", {}).get("seasons", [])]
                future_mode = "future_seasons"
            elif future_mode == "all":
                # Monitor all current seasons
                seasons_data = [{"seasonNumber": season.get("seasonNumber"), "monitored": True}
                                for season in context.user_data.get("quality_data", {}).get("seasons", [])]
            elif future_mode == "future_episodes":
                # Only monitor future episodes
                seasons_data = [{"seasonNumber": season.get("seasonNumber"), "monitored": False}
                                for season in context.user_data.get("quality_data", {}).get("seasons", [])]
                seasons_data.append({"seasonNumber": -1, "monitored": True})  # Special flag for future episodes
            else:
                # Monitor selected seasons and optionally future seasons
                seasons_data = [{"seasonNumber": season.get("seasonNumber"),
                                 "monitored": season.get("seasonNumber") in selected_seasons}
                                for season in context.user_data.get("quality_data", {}).get("seasons", [])]
                if future_mode == "future_seasons":
                    seasons_data.append({"seasonNumber": -1, "monitored": True})  # Special flag for future seasons

            success, message = await self.media_service.add_series_with_profile(
                selected["id"],
                profile_id,
                root_folder,
                seasons_data
            )

            await send_response(
                query.message,
                f"{'✅' if success else '❌'} {message}"
            )
            return ConversationHandler.END

        except Exception as e:
            logger.error(f"Error confirming season selection: {e}")
            await send_response(
                query.message,
                self.translation.get_text("SelectionProcessError")
            )
            return ConversationHandler.END
