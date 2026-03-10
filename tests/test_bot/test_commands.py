"""Tests for src/bot/commands.py

Command builder functions that produce BotCommand lists for Telegram's
setMyCommands API. Two tiers: default (unauthenticated) and authenticated
(filtered by enabled services).
"""

import pytest
from unittest.mock import AsyncMock, patch

from telegram import BotCommand, BotCommandScopeChat


# ---------------------------------------------------------------------------
# build_default_commands
# ---------------------------------------------------------------------------


class TestBuildDefaultCommands:
    """Tests for build_default_commands()."""

    def test_returns_three_commands(self):
        """Default commands are exactly: start, auth, help."""
        from src.bot.commands import build_default_commands

        commands = build_default_commands()

        assert len(commands) == 3
        names = [c.command for c in commands]
        assert names == ["start", "auth", "help"]

    def test_returns_bot_command_objects(self):
        """Each item is a telegram.BotCommand."""
        from src.bot.commands import build_default_commands

        commands = build_default_commands()

        for cmd in commands:
            assert isinstance(cmd, BotCommand)

    def test_descriptions_use_translation_keys(self):
        """Descriptions come from get_text (which returns the key in tests)."""
        from src.bot.commands import build_default_commands

        commands = build_default_commands()

        descriptions = [c.description for c in commands]
        assert "CommandStart" in descriptions
        assert "CommandAuth" in descriptions
        assert "CommandHelp" in descriptions


# ---------------------------------------------------------------------------
# build_authenticated_commands
# ---------------------------------------------------------------------------


class TestBuildAuthenticatedCommands:
    """Tests for build_authenticated_commands()."""

    def _make_config(self, mock_config, **overrides):
        """Set all services to disabled, then apply overrides."""
        mock_config._set("radarr", {"enable": False})
        mock_config._set("sonarr", {"enable": False})
        mock_config._set("lidarr", {"enable": False})
        mock_config._set("transmission", {"enable": False})
        mock_config._set("sabnzbd", {"enable": False})
        for key, value in overrides.items():
            mock_config._set(key, value)
        return mock_config

    def test_minimal_config_returns_base_commands(self, mock_config):
        """With no optional services enabled, returns 8 base commands."""
        cfg = self._make_config(mock_config)

        with patch("src.bot.commands.config", cfg):
            from src.bot.commands import build_authenticated_commands
            commands = build_authenticated_commands()

        names = [c.command for c in commands]
        assert len(commands) == 8
        assert names == [
            "start", "auth", "help", "status",
            "settings", "preferences", "delete", "webhooks",
        ]

    def test_radarr_adds_movie_and_allmovies(self, mock_config):
        """Radarr enabled adds movie + allmovies + upcoming + missing."""
        cfg = self._make_config(mock_config, radarr={"enable": True})

        with patch("src.bot.commands.config", cfg):
            from src.bot.commands import build_authenticated_commands
            commands = build_authenticated_commands()

        names = [c.command for c in commands]
        assert "movie" in names
        assert "allmovies" in names
        assert len(commands) == 14  # 8 base + 2 + upcoming + missing + queue + history

    def test_sonarr_adds_series_and_allseries(self, mock_config):
        """Sonarr enabled adds series + allseries + upcoming + missing."""
        cfg = self._make_config(mock_config, sonarr={"enable": True})

        with patch("src.bot.commands.config", cfg):
            from src.bot.commands import build_authenticated_commands
            commands = build_authenticated_commands()

        names = [c.command for c in commands]
        assert "series" in names
        assert "allseries" in names
        assert len(commands) == 14  # 8 base + 2 + upcoming + missing + queue + history

    def test_lidarr_adds_music_and_allmusic(self, mock_config):
        """Lidarr enabled adds music + allmusic commands."""
        cfg = self._make_config(mock_config, lidarr={"enable": True})

        with patch("src.bot.commands.config", cfg):
            from src.bot.commands import build_authenticated_commands
            commands = build_authenticated_commands()

        names = [c.command for c in commands]
        assert "music" in names
        assert "allmusic" in names
        assert len(commands) == 11  # 8 base + 2 + queue

    def test_transmission_adds_transmission(self, mock_config):
        """Transmission enabled adds transmission command."""
        cfg = self._make_config(mock_config, transmission={"enable": True})

        with patch("src.bot.commands.config", cfg):
            from src.bot.commands import build_authenticated_commands
            commands = build_authenticated_commands()

        names = [c.command for c in commands]
        assert "transmission" in names
        assert "downloads" in names
        assert len(commands) == 10  # 8 base + transmission + downloads

    def test_sabnzbd_adds_sabnzbd(self, mock_config):
        """SABnzbd enabled adds sabnzbd command."""
        cfg = self._make_config(mock_config, sabnzbd={"enable": True})

        with patch("src.bot.commands.config", cfg):
            from src.bot.commands import build_authenticated_commands
            commands = build_authenticated_commands()

        names = [c.command for c in commands]
        assert "sabnzbd" in names
        assert "downloads" in names
        assert len(commands) == 10  # 8 base + sabnzbd + downloads

    def test_radarr_adds_upcoming_and_missing(self, mock_config):
        """Radarr enabled adds upcoming and missing commands."""
        cfg = self._make_config(mock_config, radarr={"enable": True})

        with patch("src.bot.commands.config", cfg):
            from src.bot.commands import build_authenticated_commands
            commands = build_authenticated_commands()

        names = [c.command for c in commands]
        assert "upcoming" in names
        assert "missing" in names

    def test_sonarr_adds_upcoming_and_missing(self, mock_config):
        """Sonarr enabled adds upcoming and missing commands."""
        cfg = self._make_config(mock_config, sonarr={"enable": True})

        with patch("src.bot.commands.config", cfg):
            from src.bot.commands import build_authenticated_commands
            commands = build_authenticated_commands()

        names = [c.command for c in commands]
        assert "upcoming" in names
        assert "missing" in names

    def test_no_upcoming_missing_when_neither_radarr_nor_sonarr(self, mock_config):
        """Upcoming and missing commands absent when neither Radarr nor Sonarr enabled."""
        cfg = self._make_config(mock_config)

        with patch("src.bot.commands.config", cfg):
            from src.bot.commands import build_authenticated_commands
            commands = build_authenticated_commands()

        names = [c.command for c in commands]
        assert "upcoming" not in names
        assert "missing" not in names

    def test_webhooks_command_always_present(self, mock_config):
        """webhooks command is always included in authenticated commands."""
        cfg = self._make_config(mock_config)

        with patch("src.bot.commands.config", cfg):
            from src.bot.commands import build_authenticated_commands
            commands = build_authenticated_commands()

        names = [c.command for c in commands]
        assert "webhooks" in names

    def test_all_services_enabled(self, mock_config):
        """All services enabled returns all commands."""
        cfg = self._make_config(
            mock_config,
            radarr={"enable": True},
            sonarr={"enable": True},
            lidarr={"enable": True},
            transmission={"enable": True},
            sabnzbd={"enable": True},
        )

        with patch("src.bot.commands.config", cfg):
            from src.bot.commands import build_authenticated_commands
            commands = build_authenticated_commands()

        assert len(commands) == 21
        names = [c.command for c in commands]
        expected = [
            "start", "auth", "help", "status", "settings",
            "preferences", "delete", "webhooks", "movie", "allmovies",
            "series", "allseries", "music", "allmusic",
            "upcoming", "missing", "queue", "history",
            "transmission", "sabnzbd", "downloads",
        ]
        assert names == expected


# ---------------------------------------------------------------------------
# register_commands_for_chat
# ---------------------------------------------------------------------------


class TestRegisterCommandsForChat:
    """Tests for register_commands_for_chat()."""

    @pytest.mark.asyncio
    async def test_calls_set_my_commands_with_chat_scope(self):
        """Calls bot.set_my_commands with BotCommandScopeChat for given chat_id."""
        from src.bot.commands import register_commands_for_chat

        bot = AsyncMock()
        await register_commands_for_chat(bot, chat_id=99999)

        bot.set_my_commands.assert_called_once()
        call_args = bot.set_my_commands.call_args
        scope = call_args.kwargs.get("scope") or call_args[1].get("scope")
        assert isinstance(scope, BotCommandScopeChat)

    @pytest.mark.asyncio
    async def test_error_does_not_propagate(self):
        """If bot.set_my_commands raises, the error is caught (not propagated)."""
        from src.bot.commands import register_commands_for_chat

        bot = AsyncMock()
        bot.set_my_commands.side_effect = Exception("Chat not found")

        # Should not raise
        await register_commands_for_chat(bot, chat_id=99999)
