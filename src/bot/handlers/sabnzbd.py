"""
Filename: sabnzbd.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: SABnzbd handler module.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes, CallbackQueryHandler
from src.utils.logger import get_logger, log_user_interaction
from src.services.sabnzbd import SABnzbdService
from src.bot.handlers.auth import require_auth
from src.bot.keyboards import (
    get_downloads_queue_keyboard,
    get_downloads_history_keyboard,
)
from src.services.translation import TranslationService

logger = get_logger("addarr.handlers.sabnzbd")


class SabnzbdHandler:
    """Handler for SABnzbd-related commands"""

    def __init__(self):
        self.sabnzbd_service = SABnzbdService()
        self.translation = TranslationService()

    def get_handler(self):
        """Get the conversation handler for SABnzbd"""
        if not self.sabnzbd_service.is_enabled():
            logger.warning("SABnzbd service not available, skipping handler registration")
            return []

        return [
            CommandHandler("sabnzbd", self.handle_sabnzbd),
            CallbackQueryHandler(self.handle_speed_selection, pattern="^sabnzbd_speed_"),
            CommandHandler("downloads", self.handle_downloads),
            CallbackQueryHandler(self.handle_downloads_tab, pattern=r"^dl_tab_"),
            CallbackQueryHandler(self.handle_downloads_page, pattern=r"^dl_page_"),
            CallbackQueryHandler(self.handle_downloads_pause_item, pattern=r"^dl_pause_(?!all)"),
            CallbackQueryHandler(self.handle_downloads_resume_item, pattern=r"^dl_resume_(?!all)"),
            CallbackQueryHandler(self.handle_downloads_pauseall, pattern=r"^dl_pauseall$"),
            CallbackQueryHandler(self.handle_downloads_resumeall, pattern=r"^dl_resumeall$"),
            CallbackQueryHandler(self.handle_downloads_refresh, pattern=r"^dl_refresh$"),
            CallbackQueryHandler(self.handle_downloads_noop, pattern=r"^dl_noop$"),
        ]

    @require_auth
    async def handle_sabnzbd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle SABnzbd command"""
        if not update.effective_user:  # pragma: no cover
            return

        log_user_interaction(logger, update.effective_user, "/sabnzbd")

        if not self.sabnzbd_service.is_enabled():
            await update.message.reply_text(
                self.translation.get_text("Sabnzbd.NotEnabled")
            )
            return

        # Create speed selection keyboard
        keyboard = [
            [
                InlineKeyboardButton(
                    self.translation.get_text("Sabnzbd.Limit25"),
                    callback_data="sabnzbd_speed_25"
                ),
                InlineKeyboardButton(
                    self.translation.get_text("Sabnzbd.Limit50"),
                    callback_data="sabnzbd_speed_50"
                )
            ],
            [
                InlineKeyboardButton(
                    self.translation.get_text("Sabnzbd.Limit100"),
                    callback_data="sabnzbd_speed_100"
                )
            ]
        ]

        await update.message.reply_text(
            self.translation.get_text("Sabnzbd.Speed"),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def handle_speed_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle speed selection"""
        if not update.callback_query:
            return

        query = update.callback_query
        await query.answer()

        speed = int(query.data.replace("sabnzbd_speed_", ""))

        try:
            await self.sabnzbd_service.set_speed_limit(speed)

            # Get appropriate message for speed setting
            message_key = f"Sabnzbd.ChangedTo{speed}"
            await query.message.edit_text(
                self.translation.get_text(message_key)
            )

        except Exception as e:
            logger.error(f"Error setting SABnzbd speed: {e}")
            await query.message.edit_text(
                self.translation.get_text("Sabnzbd.Error")
            )

    # -----------------------------------------------------------------
    # /downloads dashboard
    # -----------------------------------------------------------------

    @require_auth
    async def handle_downloads(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /downloads command — show SABnzbd queue dashboard."""
        if not update.effective_user:  # pragma: no cover
            return

        log_user_interaction(logger, update.effective_user, "/downloads")

        if not self.sabnzbd_service.is_enabled():
            await update.message.reply_text(
                self.translation.get_text("DownloadsNotEnabled")
            )
            return

        context.user_data["dl_tab"] = "queue"
        context.user_data["dl_page"] = 0

        queue = await self.sabnzbd_service.get_queue_details()
        text = self._format_queue_text(queue)
        keyboard = get_downloads_queue_keyboard(
            queue["items"], page=0, paused=queue["paused"]
        )

        await update.message.reply_text(
            text, reply_markup=keyboard
        )

    async def handle_downloads_tab(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle tab switching between queue and history."""
        query = update.callback_query
        await query.answer()

        context.user_data["dl_tab"] = query.data.replace("dl_tab_", "")
        context.user_data["dl_page"] = 0

        await self._refresh_current_view(query, context)

    async def handle_downloads_page(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle pagination."""
        query = update.callback_query
        await query.answer()

        context.user_data["dl_page"] = int(query.data.replace("dl_page_", ""))

        await self._refresh_current_view(query, context)

    async def handle_downloads_pause_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle per-item pause."""
        query = update.callback_query
        nzo_id = query.data.replace("dl_pause_", "")

        success = await self.sabnzbd_service.pause_item(nzo_id)
        if success:
            await query.answer(
                text=self.translation.get_text("DownloadsItemPaused")
            )
            await self._refresh_current_view(query, context)
        else:
            await query.answer(
                text=self.translation.get_text("DownloadsPauseError"),
                show_alert=True,
            )

    async def handle_downloads_resume_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle per-item resume."""
        query = update.callback_query
        nzo_id = query.data.replace("dl_resume_", "")

        success = await self.sabnzbd_service.resume_item(nzo_id)
        if success:
            await query.answer(
                text=self.translation.get_text("DownloadsItemResumed")
            )
            await self._refresh_current_view(query, context)
        else:
            await query.answer(
                text=self.translation.get_text("DownloadsResumeError"),
                show_alert=True,
            )

    async def handle_downloads_pauseall(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle pause all."""
        query = update.callback_query
        await self.sabnzbd_service.pause_queue()
        await query.answer(
            text=self.translation.get_text("DownloadsPaused")
        )
        await self._refresh_current_view(query, context)

    async def handle_downloads_resumeall(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle resume all."""
        query = update.callback_query
        await self.sabnzbd_service.resume_queue()
        await query.answer(
            text=self.translation.get_text("DownloadsItemResumed")
        )
        await self._refresh_current_view(query, context)

    async def handle_downloads_refresh(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle refresh button."""
        query = update.callback_query
        await query.answer()

        await self._refresh_current_view(query, context)

    async def handle_downloads_noop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle display-only button presses (dismiss loading spinner)."""
        await update.callback_query.answer()

    # -----------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------

    async def _refresh_current_view(self, query, context):
        """Re-fetch data and edit the message for the current tab/page."""
        tab = context.user_data.get("dl_tab", "queue")
        page = context.user_data.get("dl_page", 0)

        if tab == "history":
            history = await self.sabnzbd_service.get_history()
            text = self._format_history_text(history)
            keyboard = get_downloads_history_keyboard(
                history["items"], page=page
            )
        else:
            queue = await self.sabnzbd_service.get_queue_details()
            text = self._format_queue_text(queue)
            keyboard = get_downloads_queue_keyboard(
                queue["items"], page=page, paused=queue["paused"]
            )

        await query.message.edit_text(text, reply_markup=keyboard)

    def _format_queue_text(self, queue):
        """Format queue data into display text."""
        t = self.translation.get_text
        title = t("DownloadsTitle")
        speed = queue.get("speed", "0 KB/s")
        size = queue.get("size_remaining", "0 MB")
        count = queue.get("items_count", 0)

        lines = [f"\U0001f4e5 {title}\n"]

        if count == 0:
            lines.append(t("DownloadsEmpty"))
        else:
            lines.append(
                f"\u26a1 {t('DownloadsSpeed')}: {speed} | "
                f"\U0001f4e6 {t('DownloadsItems')}: {count} | "
                f"\U0001f4be {t('DownloadsRemaining')}: {size}"
            )
            if queue.get("paused"):
                lines.append(f"\u23f8 {t('DownloadsPaused')}")

        return "\n".join(lines)

    def _format_history_text(self, history):
        """Format history data into display text."""
        t = self.translation.get_text
        title = t("DownloadsHistoryTitle")
        lines = [f"\U0001f4dc {title}\n"]

        items = history.get("items", [])
        if not items:
            lines.append(t("DownloadsHistoryEmpty"))
        else:
            for i, item in enumerate(items[:10], 1):
                name = item.get("name", "")
                status = item.get("status", "")
                size = item.get("size", "")
                icon = "\u2705" if status == "Completed" else "\u274c"
                dl_time = item.get("download_time", 0)
                if dl_time > 0:
                    hours = dl_time // 3600
                    minutes = (dl_time % 3600) // 60
                    time_str = f"{hours}h {minutes}m" if hours else f"{minutes}m"
                    lines.append(f"{i}. {icon} {name} \u2014 {size} \u2014 {time_str}")
                else:
                    lines.append(f"{i}. {icon} {name} \u2014 {size}")

        return "\n".join(lines)
