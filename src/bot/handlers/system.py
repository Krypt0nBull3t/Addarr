"""
Filename: system.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: System command handler module.
"""

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, CallbackQueryHandler
from src.utils.logger import get_logger, log_user_interaction
from src.utils.helpers import format_bytes
from src.bot.handlers.auth import require_auth
from src.bot.keyboards import get_system_keyboard, get_main_menu_keyboard
from src.services.health import health_service
from src.services.translation import TranslationService

logger = get_logger("addarr.system")

LOW_SPACE_THRESHOLD = 10  # percent free


def _format_usage_bar(percent_used, width=10):
    """Build a text progress bar for disk usage."""
    filled = round(width * percent_used / 100)
    empty = width - filled
    return "█" * filled + "░" * empty


def _build_disk_space_text(drives, translation):
    """Build formatted disk space text from a list of drive dicts."""
    if not drives:
        return translation.get_text("DiskSpaceNone", default="No disk space data available.")

    text = "💾 *Disk Space*\n\n"
    for drive in drives:
        path = drive.get("path", "Unknown")
        free = drive.get("freeSpace", 0)
        total = drive.get("totalSpace", 0)

        if total > 0:
            used = total - free
            percent_used = round(used / total * 100, 1)
            percent_free = round(free / total * 100, 1)
        else:
            percent_used = 0
            percent_free = 100

        bar = _format_usage_bar(percent_used)
        warning = " ⚠️" if percent_free < LOW_SPACE_THRESHOLD else ""

        text += f"📁 `{path}`{warning}\n"
        text += f"  {bar} {percent_used}%\n"
        text += f"  {format_bytes(free)} free / {format_bytes(total)} total\n\n"

    return text


class SystemHandler:
    """Handler for system-related commands"""

    def __init__(self):
        self.translation = TranslationService()

    def get_handler(self):
        """Get system command handlers"""
        return [
            CommandHandler("status", self.show_status),
            CallbackQueryHandler(self.handle_system_action, pattern="^system_")
        ]

    @require_auth
    async def show_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show system status with action buttons"""
        if not update.effective_user:  # pragma: no cover
            return

        log_user_interaction(logger, update.effective_user, "/status")

        status_text = self._build_status_text()
        keyboard = get_system_keyboard()

        if update.callback_query:
            await update.callback_query.message.edit_text(
                status_text,
                reply_markup=keyboard,
            )
        else:
            await update.message.reply_text(
                status_text,
                reply_markup=keyboard,
            )

    @require_auth
    async def handle_system_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle system action button presses"""
        if not update.callback_query:
            return

        query = update.callback_query
        action = query.data.replace("system_", "")

        log_user_interaction(logger, query.from_user, f"system_{action}")

        if action == "refresh":
            await self._handle_refresh(query)
        elif action == "details":
            await self._handle_details(query)
        elif action == "diskspace":
            await self._handle_diskspace(query)
        elif action == "back":
            await self._handle_back(query)
        else:
            logger.warning(f"Unknown system action received: {action}")
            await query.answer(self.translation.get_text("UnknownAction"))
            status_text = self._build_status_text()
            await query.message.edit_text(
                status_text,
                reply_markup=get_system_keyboard(),
            )

    async def _handle_refresh(self, query):
        """Re-run health checks and update the status display."""
        try:
            await health_service.run_health_checks()
            status_text = self._build_status_text()
            await query.message.edit_text(
                status_text,
                reply_markup=get_system_keyboard(),
            )
            await query.answer(
                self.translation.get_text("StatusRefreshed")
            )
        except Exception as e:
            logger.error(f"Error refreshing status: {e}")
            await query.message.edit_text(
                self.translation.get_text("StatusRefreshError"),
                reply_markup=get_system_keyboard(),
            )
            await query.answer(
                self.translation.get_text("StatusRefreshFailed")
            )

    async def _handle_details(self, query):
        """Show detailed per-service health information."""
        try:
            results = await health_service.run_health_checks()
            details_text = self._build_details_text(results)
            await query.message.edit_text(
                details_text,
                reply_markup=get_system_keyboard(),
            )
            await query.answer()
        except Exception as e:
            logger.error(f"Error getting service details: {e}")
            await query.message.edit_text(
                self.translation.get_text("StatusDetailsError"),
                reply_markup=get_system_keyboard(),
            )
            await query.answer(
                self.translation.get_text("StatusDetailsFailed")
            )

    async def _handle_diskspace(self, query):
        """Show disk space information from the first available *arr service."""
        try:
            drives = await health_service.get_disk_space()
            text = _build_disk_space_text(drives, self.translation)
            await query.message.edit_text(
                text,
                reply_markup=get_system_keyboard(),
                parse_mode="Markdown",
            )
            await query.answer()
        except Exception as e:
            logger.error(f"Error getting disk space: {e}")
            await query.message.edit_text(
                self.translation.get_text("DiskSpaceError", default="Error retrieving disk space."),
                reply_markup=get_system_keyboard(),
            )
            await query.answer(
                self.translation.get_text("DiskSpaceFailed", default="Failed to get disk space.")
            )

    async def _handle_back(self, query):
        """Return to the main menu."""
        await query.message.edit_text(
            "🏠 Main Menu",
            reply_markup=get_main_menu_keyboard(),
        )
        await query.answer()

    def _build_status_text(self):
        """Build the status summary text from health service state."""
        status = health_service.get_status()

        running = status.get("running", False)
        last_check = status.get("last_check")
        unhealthy = status.get("unhealthy_services", [])

        text = "📊 *System Status*\n\n"
        text += "🏥 *Health Monitor*\n"
        text += f"• Status: {'✅ Running' if running else '❌ Stopped'}\n"

        if last_check:
            text += f"• Last Check: {last_check.strftime('%Y-%m-%d %H:%M:%S')}\n"

        text += "\n🔧 *Services*\n"
        if unhealthy:
            text += "❌ Unhealthy:\n"
            for service in unhealthy:
                text += f"  • {service}\n"
        else:
            text += "✅ All services healthy\n"

        return text

    def _build_details_text(self, results):
        """Build detailed per-service text from health check results."""
        media = results.get("media_services", [])
        clients = results.get("download_clients", [])

        if not media and not clients:
            return "📋 *Service Details*\n\nNo services enabled."

        text = "📋 *Service Details*\n\n"

        if media:
            text += "🎬 *Media Services*\n"
            for svc in media:
                icon = "✅" if svc["healthy"] else "❌"
                text += f"  {icon} {svc['name']}: {svc['status']}\n"
            text += "\n"

        if clients:
            text += "📥 *Download Clients*\n"
            for cl in clients:
                icon = "✅" if cl["healthy"] else "❌"
                text += f"  {icon} {cl['name']}: {cl['status']}\n"

        return text
