"""
Filename: logger.py
Author: Christian Blank
Created Date: 2024-11-08
Description: Logging configuration module for Addarr. This module sets up logging for the application, configuring both file
and console logging with proper formatting and log rotation. It provides
a consistent logging interface across the application.
"""

import logging
import os
from pathlib import Path
from typing import Optional
from colorama import Fore, Style, init
from logging.handlers import RotatingFileHandler

from ..definitions import LOG_PATH, ERROR_LOG_PATH

# Initialize colorama
init(autoreset=True)

# Add custom logging level for success messages
SUCCESS_LEVEL = 25  # Between INFO and WARNING
logging.addLevelName(SUCCESS_LEVEL, 'SUCCESS')


class ColoredFormatter(logging.Formatter):
    """Custom formatter adding colors to log levels"""

    def format(self, record):
        # Save the original message
        original_msg = record.msg

        # Add color based on level without modifying anything else
        if record.levelno >= logging.ERROR:
            record.msg = f"{Fore.RED}{original_msg}{Style.RESET_ALL}"
        elif record.levelno >= logging.WARNING:
            record.msg = f"{Fore.YELLOW}{original_msg}{Style.RESET_ALL}"
        elif record.levelno >= logging.INFO:
            record.msg = f"{Fore.BLUE}{original_msg}{Style.RESET_ALL}"
        elif record.levelno >= logging.DEBUG:
            record.msg = f"{Fore.CYAN}{original_msg}{Style.RESET_ALL}"

        # Format the message
        result = super().format(record)

        # Restore the original message for file logging
        record.msg = original_msg
        return result


class ColoredLogger(logging.Logger):
    """Logger class with success method"""
    def success(self, msg, *args, **kwargs):
        """Log success messages"""
        if self.isEnabledFor(SUCCESS_LEVEL):
            self._log(SUCCESS_LEVEL, msg, args, **kwargs)


LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Set once the shared handlers exist (a handlers check would also see foreign ones)
_shared_handlers_ready = False


def _rotating_file_handler(path: str, level: int, fmt: str = LOG_FORMAT) -> RotatingFileHandler:
    """Create a file handler (no colors) that rotates at 1MB and keeps 5 backups"""
    handler = RotatingFileHandler(
        path,
        maxBytes=1024 * 1024,  # 1MB
        backupCount=5,
        encoding='utf-8'
    )
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(fmt))
    return handler


def _setup_shared_handlers():
    """Attach the console and file handlers once, to the shared "addarr" logger.

    All "addarr.*" loggers propagate to it, so each log file has exactly one
    handler and rotation works. If the log folder is not writable (for example
    a Docker bind mount owned by another user), log to the console only.
    """
    global _shared_handlers_ready
    if _shared_handlers_ready:
        return
    _shared_handlers_ready = True

    parent = logging.getLogger("addarr")
    parent.setLevel(logging.DEBUG)
    # Don't propagate to root logger
    parent.propagate = False

    # Console handler with colors and a minimal format
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(ColoredFormatter('%(message)s'))
    parent.addHandler(console_handler)

    # Separate logger so interactions do not repeat in addarr.log and the console
    interactions = logging.getLogger("interactions")
    interactions.setLevel(logging.INFO)
    interactions.propagate = False

    log_dir = os.path.dirname(LOG_PATH)
    try:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        parent.addHandler(_rotating_file_handler(LOG_PATH, logging.INFO))
        parent.addHandler(_rotating_file_handler(ERROR_LOG_PATH, logging.ERROR))
        interactions.addHandler(_rotating_file_handler(
            os.path.join(log_dir, "interactions.log"), logging.INFO, '%(message)s'
        ))
    except OSError as e:
        parent.warning(f"⚠️ Cannot write log files to {log_dir} ({e}). Logging to the console only.")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger that writes through the shared console and file handlers

    Args:
        name: The name of the logger. Use an "addarr." prefix, or the
            records do not reach the shared handlers.

    Returns:
        logging.Logger: Configured logger instance
    """
    # Register the custom logger class
    logging.setLoggerClass(ColoredLogger)
    _setup_shared_handlers()
    return logging.getLogger(name)


def log_exception(logger: logging.Logger, e: Exception, context: Optional[str] = None):
    """
    Helper function to log exceptions with full context

    Args:
        logger: Logger instance
        e: Exception to log
        context: Additional context information
    """
    error_msg = f"{Fore.RED}❌ Error"
    if context:
        error_msg += f" in {context}"
    error_msg += f": {str(e)}"

    logger.error(
        error_msg,
        exc_info=True,
        stack_info=True
    )


def log_user_interaction(logger, user, action: str, input_data: Optional[str] = None):
    """Log user interaction with the bot with emojis

    Args:
        logger: Logger instance
        user: Telegram user object
        action: Action/command being performed
        input_data: Optional input data from user
    """
    username = user.username or "Unknown"
    user_id = user.id

    # Define emojis for different actions
    action_emojis = {
        # Authentication
        "/auth": "🔐",
        "auth_success": "✅",
        "auth_failed": "❌",
        "auth_cancelled": "🚫",

        # Main menu
        "/start": "🚀",
        "menu_movie": "🎬",
        "menu_series": "📺",
        "menu_music": "🎵",
        "menu_delete": "❌",
        "menu_status": "📊",
        "menu_settings": "⚙️",
        "menu_help": "❓",

        # Media actions
        "/movie": "🎬",
        "/series": "📺",
        "/music": "🎵",
        "search_movie": "🔍",
        "search_series": "🔍",
        "search_music": "🔍",
        "add_movie": "➕",
        "add_series": "➕",
        "add_music": "➕",
        "cancel_search": "🚫",

        # System commands
        "/status": "📊",
        "/settings": "⚙️",
        "/help": "❓",
        "/delete": "❌",

        # Download clients
        "/transmission": "📥",
        "/sabnzbd": "📥",

        # System actions
        "system_refresh": "🔄",
        "system_back": "⬅️",
    }

    # Get emoji for action, default to 🔹 if not found
    emoji = action_emojis.get(action, "🔹")

    # Format the log message with emoji
    log_message = f"{emoji} User: {username} ({user_id}) - Action: {action}"
    if input_data:
        log_message += f" - Input: {input_data}"

    # Log to console with color
    logger.info(Fore.CYAN + log_message)

    # Log to interaction log file
    logging.getLogger("interactions").info(log_message)
