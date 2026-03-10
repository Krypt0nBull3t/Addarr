"""
Filename: webhooks.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Webhook setup wizard handler for configuring *arr webhook secrets,
             ports, and event toggles through inline keyboards.
"""

import secrets

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from src.bot.handlers.auth import require_auth
from src.bot.keyboards import (
    get_webhook_events_keyboard,
    get_webhook_menu_keyboard,
    get_webhook_service_keyboard,
)
from src.bot.states import States
from src.config.settings import config
from src.definitions import is_admin
from src.services.translation import TranslationService
from src.utils.logger import get_logger, log_user_interaction

logger = get_logger("addarr.webhooks")


class WebhooksHandler:
    """Handler for webhook configuration wizard."""

    def __init__(self):
        self.translation = TranslationService()

    def get_handler(self):
        """Return list of handlers to register."""
        return [
            ConversationHandler(
                entry_points=[
                    CommandHandler("webhooks", self.show_menu),
                ],
                states={
                    States.WEBHOOK_MENU: [
                        CallbackQueryHandler(
                            self.setup_service, pattern="^wh_setup_"
                        ),
                        CallbackQueryHandler(
                            self.regenerate_secret, pattern="^wh_regen_"
                        ),
                        CallbackQueryHandler(
                            self.show_events, pattern="^wh_events$"
                        ),
                        CallbackQueryHandler(
                            self.prompt_port, pattern="^wh_port$"
                        ),
                        CallbackQueryHandler(
                            self.handle_close, pattern="^wh_close$"
                        ),
                    ],
                    States.WEBHOOK_EVENTS: [
                        CallbackQueryHandler(
                            self.toggle_event, pattern="^wh_toggle_"
                        ),
                        CallbackQueryHandler(
                            self._back_to_menu, pattern="^wh_back$"
                        ),
                    ],
                    States.WEBHOOK_CHANGE_PORT: [
                        MessageHandler(
                            filters.TEXT & ~filters.COMMAND,
                            self.save_port,
                        ),
                    ],
                },
                fallbacks=[
                    CommandHandler("cancel", self.handle_close),
                    CallbackQueryHandler(
                        self.handle_close, pattern="^wh_close$"
                    ),
                ],
                name="webhooks_conversation",
                persistent=False,
                per_message=False,
            ),
        ]

    @require_auth
    async def show_menu(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Show the webhook settings menu."""
        # @require_auth already guards against missing user/message
        log_user_interaction(logger, update.effective_user, "/webhooks")

        # Admin gate
        if not is_admin(update.effective_user.id):
            await update.effective_message.reply_text(
                self.translation.get_text("WebhookNotAdmin")
            )
            return ConversationHandler.END

        # Check if webhooks are enabled
        webhook_config = config.get("webhooks", {})
        if not webhook_config.get("enable", False):
            await update.effective_message.reply_text(
                self.translation.get_text("WebhookNotEnabled")
            )
            return ConversationHandler.END

        # Build status text
        port = webhook_config.get("port", 8080)
        status_text = self.translation.get_text(
            "WebhookMenuTitle"
        )
        status_text += "\n\n"
        status_text += self.translation.get_text(
            "WebhookServerRunning", port=port
        )

        keyboard = get_webhook_menu_keyboard(
            radarr_configured=bool(webhook_config.get("radarr_secret")),
            sonarr_configured=bool(webhook_config.get("sonarr_secret")),
            lidarr_configured=bool(webhook_config.get("lidarr_secret")),
        )

        await update.effective_message.reply_text(
            text=status_text,
            reply_markup=keyboard,
        )
        return States.WEBHOOK_MENU

    async def setup_service(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Generate a secret for a service and show instructions."""
        if not update.callback_query:
            return ConversationHandler.END

        query = update.callback_query
        await query.answer()

        service = query.data.replace("wh_setup_", "")
        secret = secrets.token_hex(32)

        # Save secret to config
        webhook_config = config.get("webhooks", {})
        webhook_config[f"{service}_secret"] = secret
        config._set("webhooks", webhook_config)
        config.save()

        port = webhook_config.get("port", 8080)
        url = f"http://<your-host>:{port}/webhooks/{service}"

        text = self.translation.get_text(
            "WebhookSecretGenerated",
            service=service.capitalize(),
            url=url,
            secret=secret,
        )

        keyboard = get_webhook_service_keyboard(service)
        await query.message.edit_text(text=text, reply_markup=keyboard)
        return States.WEBHOOK_MENU

    async def regenerate_secret(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Regenerate secret for a service."""
        if not update.callback_query:
            return ConversationHandler.END

        query = update.callback_query
        await query.answer()

        service = query.data.replace("wh_regen_", "")
        secret = secrets.token_hex(32)

        # Save new secret
        webhook_config = config.get("webhooks", {})
        webhook_config[f"{service}_secret"] = secret
        config._set("webhooks", webhook_config)
        config.save()

        port = webhook_config.get("port", 8080)
        url = f"http://<your-host>:{port}/webhooks/{service}"

        text = self.translation.get_text(
            "WebhookSecretRegenerated",
            service=service.capitalize(),
            url=url,
            secret=secret,
        )

        keyboard = get_webhook_service_keyboard(service)
        await query.message.edit_text(text=text, reply_markup=keyboard)
        return States.WEBHOOK_MENU

    async def show_events(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Show event type toggle keyboard."""
        if not update.callback_query:
            return ConversationHandler.END

        query = update.callback_query
        await query.answer()

        webhook_config = config.get("webhooks", {})
        events = webhook_config.get("events", {})

        text = self.translation.get_text("WebhookEvents")
        keyboard = get_webhook_events_keyboard(events)
        await query.message.edit_text(text=text, reply_markup=keyboard)
        return States.WEBHOOK_EVENTS

    async def toggle_event(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Toggle an event type on/off."""
        if not update.callback_query:
            return ConversationHandler.END

        query = update.callback_query
        await query.answer()

        event_key = query.data.replace("wh_toggle_", "")

        webhook_config = config.get("webhooks", {})
        events = webhook_config.get("events", {})
        events[event_key] = not events.get(event_key, True)
        webhook_config["events"] = events
        config._set("webhooks", webhook_config)
        config.save()

        # Refresh the events keyboard
        text = self.translation.get_text("WebhookEvents")
        keyboard = get_webhook_events_keyboard(events)
        await query.message.edit_text(text=text, reply_markup=keyboard)
        return States.WEBHOOK_EVENTS

    async def prompt_port(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Prompt user to enter a new port number."""
        if not update.callback_query:
            return ConversationHandler.END

        query = update.callback_query
        await query.answer()

        text = self.translation.get_text("WebhookPortPrompt")
        await query.message.edit_text(text=text)
        return States.WEBHOOK_CHANGE_PORT

    async def save_port(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Validate and save a new port number."""
        if not update.effective_message:
            return ConversationHandler.END

        text = update.message.text.strip()

        try:
            port = int(text)
        except ValueError:
            await update.effective_message.reply_text(
                self.translation.get_text("WebhookPortInvalid")
            )
            return States.WEBHOOK_CHANGE_PORT

        if port < 1024 or port > 65535:
            await update.effective_message.reply_text(
                self.translation.get_text("WebhookPortInvalid")
            )
            return States.WEBHOOK_CHANGE_PORT

        webhook_config = config.get("webhooks", {})
        webhook_config["port"] = port
        config._set("webhooks", webhook_config)
        config.save()

        msg = self.translation.get_text("WebhookPortSaved", port=port)

        # Show menu again
        keyboard = get_webhook_menu_keyboard(
            radarr_configured=bool(webhook_config.get("radarr_secret")),
            sonarr_configured=bool(webhook_config.get("sonarr_secret")),
            lidarr_configured=bool(webhook_config.get("lidarr_secret")),
        )
        await update.effective_message.reply_text(
            text=msg, reply_markup=keyboard
        )
        return States.WEBHOOK_MENU

    async def _back_to_menu(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Go back to the main webhook menu."""
        if not update.callback_query:
            return ConversationHandler.END

        query = update.callback_query
        await query.answer()

        webhook_config = config.get("webhooks", {})
        port = webhook_config.get("port", 8080)
        status_text = self.translation.get_text("WebhookMenuTitle")
        status_text += "\n\n"
        status_text += self.translation.get_text(
            "WebhookServerRunning", port=port
        )

        keyboard = get_webhook_menu_keyboard(
            radarr_configured=bool(webhook_config.get("radarr_secret")),
            sonarr_configured=bool(webhook_config.get("sonarr_secret")),
            lidarr_configured=bool(webhook_config.get("lidarr_secret")),
        )
        await query.message.edit_text(
            text=status_text, reply_markup=keyboard
        )
        return States.WEBHOOK_MENU

    async def handle_close(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Close the webhook settings wizard."""
        context.user_data.clear()

        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.edit_text(
                self.translation.get_text("WebhookClose")
            )
        elif update.effective_message:
            await update.effective_message.reply_text(
                self.translation.get_text("WebhookClose")
            )
        return ConversationHandler.END
