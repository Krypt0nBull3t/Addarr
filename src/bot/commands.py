"""
Filename: commands.py
Author: Addarr Contributors
Created Date: 2026-03-03
Description: Bot command registration for Telegram's setMyCommands API.

Builds command lists for two tiers: default (unauthenticated) and
authenticated (filtered by enabled services). Used by AddarrBot at startup
and by AuthHandler after successful authentication.
"""

from telegram import BotCommand, BotCommandScopeChat

from src.config.settings import config
from src.services.translation import TranslationService
from src.utils.logger import get_logger

logger = get_logger("addarr.commands")


def build_default_commands() -> list:
    """Build command list for unauthenticated users."""
    translation = TranslationService()
    return [
        BotCommand("start", translation.get_text("CommandStart")),
        BotCommand("auth", translation.get_text("CommandAuth")),
        BotCommand("help", translation.get_text("CommandHelp")),
    ]


def build_authenticated_commands() -> list:
    """Build full command list for authenticated users, filtered by enabled services."""
    translation = TranslationService()

    commands = [
        BotCommand("start", translation.get_text("CommandStart")),
        BotCommand("auth", translation.get_text("CommandAuth")),
        BotCommand("help", translation.get_text("CommandHelp")),
        BotCommand("status", translation.get_text("CommandStatus")),
        BotCommand("settings", translation.get_text("CommandSettings")),
        BotCommand("preferences", translation.get_text("CommandPreferences")),
        BotCommand("delete", translation.get_text("CommandDelete")),
    ]

    if config.get("radarr", {}).get("enable"):
        commands.append(BotCommand("movie", translation.get_text("CommandMovie")))
        commands.append(BotCommand("allmovies", translation.get_text("CommandAllMovies")))

    if config.get("sonarr", {}).get("enable"):
        commands.append(BotCommand("series", translation.get_text("CommandSeries")))
        commands.append(BotCommand("allseries", translation.get_text("CommandAllSeries")))

    if config.get("lidarr", {}).get("enable"):
        commands.append(BotCommand("music", translation.get_text("CommandMusic")))
        commands.append(BotCommand("allmusic", translation.get_text("CommandAllMusic")))

    if config.get("radarr", {}).get("enable") or config.get("sonarr", {}).get("enable"):
        commands.append(BotCommand("upcoming", translation.get_text("CommandUpcoming")))
        commands.append(BotCommand("missing", translation.get_text("CommandMissing")))

    if (config.get("radarr", {}).get("enable")
            or config.get("sonarr", {}).get("enable")
            or config.get("lidarr", {}).get("enable")):
        commands.append(BotCommand("queue", translation.get_text("CommandQueue")))

    if config.get("transmission", {}).get("enable", False):
        commands.append(BotCommand("transmission", translation.get_text("CommandTransmission")))

    if config.get("sabnzbd", {}).get("enable", False):
        commands.append(BotCommand("sabnzbd", translation.get_text("CommandSabnzbd")))
        commands.append(BotCommand("downloads", translation.get_text("CommandDownloads")))

    return commands


async def register_commands_for_chat(bot, chat_id: int) -> None:
    """Register authenticated commands for a specific chat."""
    commands = build_authenticated_commands()
    try:
        await bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id=chat_id))
    except Exception as e:
        logger.warning(f"Could not set commands for chat {chat_id}: {e}")
