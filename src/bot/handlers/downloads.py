"""
Filename: downloads.py
Author: Addarr Contributors
Created Date: 2026-03-06
Description: Unified downloads handler supporting SABnzbd and Transmission.
"""

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, CallbackQueryHandler
from src.utils.logger import get_logger, log_user_interaction
from src.services.sabnzbd import SABnzbdService
from src.services.transmission import TransmissionService
from src.bot.handlers.auth import require_auth
from src.bot.keyboards import (
    get_downloads_queue_keyboard,
    get_downloads_history_keyboard,
)
from src.services.translation import TranslationService

logger = get_logger("addarr.handlers.downloads")


class DownloadsHandler:
    """Unified handler for /downloads supporting SABnzbd and Transmission."""

    def __init__(self):
        self.translation = TranslationService()
        self.sabnzbd_service = SABnzbdService()
        self.transmission_service = TransmissionService()
        self._sab_enabled = self.sabnzbd_service.is_enabled()
        self._tx_enabled = self.transmission_service.is_enabled()
        self._multi_client = self._sab_enabled and self._tx_enabled

    def get_handler(self):
        """Return list of handlers to register."""
        if not self._sab_enabled and not self._tx_enabled:
            return []

        return [
            CommandHandler("downloads", self.handle_downloads),
            CallbackQueryHandler(
                self.handle_client_switch, pattern=r"^dl_client_"
            ),
            CallbackQueryHandler(
                self.handle_downloads_tab, pattern=r"^dl_tab_"
            ),
            CallbackQueryHandler(
                self.handle_downloads_page, pattern=r"^dl_page_"
            ),
            CallbackQueryHandler(
                self.handle_downloads_pause_item,
                pattern=r"^dl_pause_(?!all)",
            ),
            CallbackQueryHandler(
                self.handle_downloads_resume_item,
                pattern=r"^dl_resume_(?!all)",
            ),
            CallbackQueryHandler(
                self.handle_downloads_pauseall, pattern=r"^dl_pauseall$"
            ),
            CallbackQueryHandler(
                self.handle_downloads_resumeall, pattern=r"^dl_resumeall$"
            ),
            CallbackQueryHandler(
                self.handle_downloads_refresh, pattern=r"^dl_refresh$"
            ),
            CallbackQueryHandler(
                self.handle_downloads_noop, pattern=r"^dl_noop$"
            ),
        ]

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------

    def _get_default_client(self):
        """Return the default client name."""
        if self._sab_enabled:
            return "sabnzbd"
        return "transmission"

    def _get_active_service(self, context):
        """Return the service for the current dl_client."""
        client = context.user_data.get("dl_client", self._get_default_client())
        if client == "transmission":
            return self.transmission_service
        return self.sabnzbd_service

    def _get_client_name(self, context):
        """Return the active client name string."""
        return context.user_data.get("dl_client", self._get_default_client())

    def _parse_item_id(self, raw_id, context):
        """Parse item ID: int for Transmission, string for SABnzbd."""
        if self._get_client_name(context) == "transmission":
            try:
                return int(raw_id)
            except (ValueError, TypeError):
                return raw_id
        return raw_id

    def _show_history_tab(self, context):
        """History tab only available for SABnzbd."""
        return self._get_client_name(context) == "sabnzbd"

    def _client_param(self, context):
        """Return client param for keyboards (None if single client)."""
        if self._multi_client:
            return self._get_client_name(context)
        return None

    # -----------------------------------------------------------------
    # /downloads entry point
    # -----------------------------------------------------------------

    @require_auth
    async def handle_downloads(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /downloads command."""
        if not update.effective_user:  # pragma: no cover
            return

        log_user_interaction(logger, update.effective_user, "/downloads")

        if not self._sab_enabled and not self._tx_enabled:
            await update.message.reply_text(
                self.translation.get_text("DownloadsNotEnabled")
            )
            return

        default_client = self._get_default_client()
        context.user_data["dl_client"] = default_client
        context.user_data["dl_tab"] = "queue"
        context.user_data["dl_page"] = 0

        service = self._get_active_service(context)
        queue = await service.get_queue_details()
        text = self._format_queue_text(queue)
        keyboard = get_downloads_queue_keyboard(
            queue["items"],
            page=0,
            paused=queue["paused"],
            client=self._client_param(context),
            show_history_tab=self._show_history_tab(context),
        )

        await update.message.reply_text(text, reply_markup=keyboard)

    # -----------------------------------------------------------------
    # Client switching
    # -----------------------------------------------------------------

    async def handle_client_switch(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle dl_client_sab / dl_client_tx callbacks."""
        query = update.callback_query
        await query.answer()

        new_client = query.data.replace("dl_client_", "")
        if new_client == "sab":
            context.user_data["dl_client"] = "sabnzbd"
        elif new_client == "tx":
            context.user_data["dl_client"] = "transmission"

        context.user_data["dl_tab"] = "queue"
        context.user_data["dl_page"] = 0

        await self._refresh_current_view(query, context)

    # -----------------------------------------------------------------
    # Tab / page / refresh / noop
    # -----------------------------------------------------------------

    async def handle_downloads_tab(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle tab switching between queue and history."""
        query = update.callback_query
        await query.answer()

        context.user_data["dl_tab"] = query.data.replace("dl_tab_", "")
        context.user_data["dl_page"] = 0

        await self._refresh_current_view(query, context)

    async def handle_downloads_page(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle pagination."""
        query = update.callback_query
        await query.answer()

        context.user_data["dl_page"] = int(query.data.replace("dl_page_", ""))

        await self._refresh_current_view(query, context)

    async def handle_downloads_refresh(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle refresh button."""
        query = update.callback_query
        await query.answer()

        await self._refresh_current_view(query, context)

    async def handle_downloads_noop(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle display-only button presses (dismiss loading spinner)."""
        await update.callback_query.answer()

    # -----------------------------------------------------------------
    # Pause / resume
    # -----------------------------------------------------------------

    async def handle_downloads_pause_item(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle per-item pause."""
        query = update.callback_query
        raw_id = query.data.replace("dl_pause_", "")
        item_id = self._parse_item_id(raw_id, context)
        await self._do_action(
            query, context, "pause_item", item_id,
            "DownloadsItemPaused", "DownloadsPauseError",
        )

    async def handle_downloads_resume_item(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle per-item resume."""
        query = update.callback_query
        raw_id = query.data.replace("dl_resume_", "")
        item_id = self._parse_item_id(raw_id, context)
        await self._do_action(
            query, context, "resume_item", item_id,
            "DownloadsItemResumed", "DownloadsResumeError",
        )

    async def handle_downloads_pauseall(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle pause all."""
        await self._do_action(
            update.callback_query, context, "pause_queue", None,
            "DownloadsPaused", "DownloadsPauseError",
        )

    async def handle_downloads_resumeall(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle resume all."""
        await self._do_action(
            update.callback_query, context, "resume_queue", None,
            "DownloadsResumed", "DownloadsResumeError",
        )

    # -----------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------

    async def _do_action(
        self, query, context, method_name, item_id,
        success_key, error_key,
    ):
        """Execute a service action and show result toast."""
        service = self._get_active_service(context)
        method = getattr(service, method_name)
        success = await (method(item_id) if item_id is not None else method())
        if success:
            await query.answer(
                text=self.translation.get_text(success_key)
            )
            await self._refresh_current_view(query, context)
        else:
            await query.answer(
                text=self.translation.get_text(error_key),
                show_alert=True,
            )

    async def _refresh_current_view(self, query, context):
        """Re-fetch data and edit the message for the current tab/page."""
        tab = context.user_data.get("dl_tab", "queue")
        page = context.user_data.get("dl_page", 0)
        service = self._get_active_service(context)
        client_param = self._client_param(context)

        if tab == "history" and self._show_history_tab(context):
            history = await service.get_history()
            text = self._format_history_text(history, page=page)
            keyboard = get_downloads_history_keyboard(
                history["items"], page=page, client=client_param,
            )
        else:
            queue = await service.get_queue_details()
            text = self._format_queue_text(queue)
            keyboard = get_downloads_queue_keyboard(
                queue["items"],
                page=page,
                paused=queue["paused"],
                client=client_param,
                show_history_tab=self._show_history_tab(context),
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

    def _format_history_text(self, history, page=0, page_size=5):
        """Format history data into display text for the given page."""
        t = self.translation.get_text
        title = t("DownloadsHistoryTitle")
        lines = [f"\U0001f4dc {title}\n"]

        items = history.get("items", [])
        if not items:
            lines.append(t("DownloadsHistoryEmpty"))
        else:
            start = page * page_size
            page_items = items[start:start + page_size]
            for i, item in enumerate(page_items, start + 1):
                name = item.get("name", "")
                status = item.get("status", "")
                size = item.get("size", "")
                icon = "\u2705" if status == "Completed" else "\u274c"
                dl_time = item.get("download_time", 0)
                if dl_time > 0:
                    hours = dl_time // 3600
                    minutes = (dl_time % 3600) // 60
                    time_str = (
                        f"{hours}h {minutes}m" if hours else f"{minutes}m"
                    )
                    lines.append(
                        f"{i}. {icon} {name} \u2014 {size} \u2014 {time_str}"
                    )
                else:
                    lines.append(f"{i}. {icon} {name} \u2014 {size}")

        return "\n".join(lines)
