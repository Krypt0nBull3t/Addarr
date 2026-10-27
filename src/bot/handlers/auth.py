"""
Filename: auth.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Authentication handler module.

This module handles user authentication through the bot.
"""

import hmac
from typing import Optional

from telegram import Update
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)
from colorama import Fore
from functools import wraps

from src.utils.chat import get_chat_name
from src.utils.logger import get_logger, log_user_interaction
from src.config.settings import config
from src.utils.helpers import admin_only, is_admin, is_allowed
from src.bot.commands import register_commands_for_chat
from src.services.translation import TranslationService
from src.services.rate_limit import rate_limit

# Get logger instance
logger = get_logger("addarr.auth")

# States
PASSWORD = 0


async def _enforce_private_chat(update: Update) -> bool:
    """Return True if the update should be blocked due to chat mode policy."""
    chat_mode = config.get("security", {}).get("chatMode", "private_only")
    if chat_mode != "private_only" or not update.effective_chat:
        return False
    if update.effective_chat.type == "private":
        return False
    translation = TranslationService()
    msg = translation.get_text(
        "PrivateChatOnly",
        default="🔒 This bot only works in private chats."
    )
    if update.effective_message:
        await update.effective_message.reply_text(msg)
    return True


async def _refuse(update: Update, text: str) -> None:
    """Tell the user why a command or button press is refused."""
    if update.callback_query:
        # update.message is None for button presses; answer the press instead
        await update.callback_query.answer(text, show_alert=True)
    elif update.effective_message:
        await update.effective_message.reply_text(text)


async def _enforce_allowlist(update: Update) -> bool:
    """Return True if the update should be blocked by the allowlist."""
    if is_allowed(update.effective_user.id):
        return False
    await _refuse(update, TranslationService().get_text("NotAllowed"))
    return True


def require_auth(func):
    """Decorator to require authentication for handlers"""
    @wraps(func)
    async def wrapped(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if not update.effective_user:
            return

        if await _enforce_private_chat(update):
            return

        if await _enforce_allowlist(update):
            return

        if not AuthHandler.is_authenticated(update.effective_user.id):
            translation = TranslationService()
            await _refuse(
                update,
                translation.get_text("NotAuthorized", default="🔒 You need to authenticate first.\nUse /auth to begin authentication.")
            )
            return
        return await func(self, update, context, *args, **kwargs)
    return wrapped


def require_admin(service: Optional[str] = None):
    """Decorator to refuse non-admins when admin mode applies.

    Use below @require_auth. With a service name, only refuse when that
    service also sets onlyAdmin.
    """
    def decorator(func):
        @wraps(func)
        async def wrapped(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            if admin_only(service) and not is_admin(update.effective_user.id):
                await _refuse(update, TranslationService().get_text("NotAdmin"))
                return
            return await func(self, update, context, *args, **kwargs)
        return wrapped
    return decorator


class AuthHandler:
    """Handler for user authentication"""

    # Class-level storage for authenticated users
    _authenticated_users = set()

    def __init__(self):
        password = config.get("telegram", {}).get("password")
        # YAML loads `password: 123456` as an int
        self.password = "" if password is None else str(password)
        self.translation = TranslationService()
        # Load authenticated users from config
        AuthHandler._authenticated_users = set(config.get("authenticated_users", []))

    @classmethod
    def is_authenticated(cls, user_id: int) -> bool:
        """Check if a user is authenticated"""
        return user_id in cls._authenticated_users

    def _save_authenticated_users(self):
        """Save authenticated users to config file"""
        try:
            # Update the in-memory config too, so a later config.save() keeps them
            config.update_nested(
                "authenticated_users", sorted(AuthHandler._authenticated_users)
            )
            config.save()
        except Exception as e:
            logger.error(f"Error saving authenticated users to config: {e}")

    def get_handler(self):
        """Get the conversation handler for authentication"""
        return [
            ConversationHandler(
                entry_points=[CommandHandler("auth", self.start_auth)],
                states={
                    PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.check_password)]
                },
                fallbacks=[CommandHandler("cancel", self.cancel_auth)],
                name="auth_conversation",
                per_message=False,
            )
        ]

    @rate_limit("auth")
    async def start_auth(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the authentication process"""
        if not update.effective_message or not update.effective_user:
            return ConversationHandler.END

        if await _enforce_private_chat(update):
            return ConversationHandler.END

        if await _enforce_allowlist(update):
            return ConversationHandler.END

        user = update.effective_user
        chat = update.effective_message.chat

        log_user_interaction(logger, user, "/auth", "authentication attempt")

        # Check if user is already authenticated
        if self.is_authenticated(user.id):
            logger.info(Fore.GREEN + f"👤 User {user.username} ({user.id}) is already authenticated")
            await update.message.reply_text(
                self.translation.get_text("Chatid already allowed")
            )
            return ConversationHandler.END

        # Log authentication attempt
        logger.info(Fore.CYAN + f"👤 User {user.username} ({user.id}) started authentication in {get_chat_name(chat.id, chat.title)}")

        await update.message.reply_text(
            self.translation.get_text("Authorize")
        )

        return PASSWORD

    async def check_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check the provided password"""
        if not update.effective_message or not update.effective_user:
            return ConversationHandler.END

        user = update.effective_user
        chat = update.effective_message.chat
        message = update.effective_message

        # Delete password message for security
        await message.delete()

        if self.password and hmac.compare_digest(
            (message.text or "").encode(), self.password.encode()
        ):
            # Add user to authenticated users and save
            AuthHandler._authenticated_users.add(user.id)
            self._save_authenticated_users()
            await register_commands_for_chat(context.bot, chat.id)

            log_user_interaction(logger, user, "auth_success")

            # Log successful authentication
            logger.info(Fore.GREEN + f"✅ User {user.username} ({user.id}) authenticated successfully")

            # Show success message
            await chat.send_message(
                self.translation.get_text("Chatid added")
            )

            # Trigger the start command to show the menu
            await context.bot.send_message(
                chat.id,
                "/start"
            )

            return ConversationHandler.END
        else:
            log_user_interaction(logger, user, "auth_failed")

            # Log failed authentication
            logger.warning(Fore.RED + f"❌ User {user.username} ({user.id}) failed authentication")

            await chat.send_message(
                self.translation.get_text("Wrong password")
            )
            return ConversationHandler.END

    async def cancel_auth(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel the authentication process"""
        if update.effective_message:
            log_user_interaction(logger, update.effective_user, "auth_cancelled")
            await update.message.reply_text(
                self.translation.get_text("End")
            )
        return ConversationHandler.END
