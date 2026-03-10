"""
Tests for src/bot/handlers/help.py - HelpHandler with show_help and handle_back.

HelpHandler.__init__ creates TranslationService().
show_help builds dynamic help text from translations, filtered by enabled services.
handle_back returns to the main menu (decorated with @require_auth).
"""

import pytest
from contextlib import contextmanager
from unittest.mock import patch, MagicMock


def _make_config(radarr=False, sonarr=False, lidarr=False,
                 transmission=False, sabnzbd=False, bazarr=False):
    """Build a mock config dict with service enable flags."""
    data = {
        "radarr": {"enable": True} if radarr else {},
        "sonarr": {"enable": True} if sonarr else {},
        "lidarr": {"enable": True} if lidarr else {},
        "transmission": {"enable": True} if transmission else {},
        "sabnzbd": {"enable": True} if sabnzbd else {},
        "bazarr": {"enable": True} if bazarr else {},
    }
    mock = MagicMock()
    mock.get = lambda key, default=None: data.get(
        key, default if default is not None else {}
    )
    return mock


@contextmanager
def _help_patches(**config_kwargs):
    """Patch TranslationService, config, and keyboard for help handler tests."""
    mock_ts_class = MagicMock()
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    with patch("src.bot.handlers.help.TranslationService", mock_ts_class), \
         patch("src.bot.handlers.help.config", _make_config(**config_kwargs)), \
         patch("src.bot.handlers.help.get_main_menu_keyboard"):

        from src.bot.handlers.auth import AuthHandler
        AuthHandler._authenticated_users = {12345}
        yield


def _make_handler():
    from src.bot.handlers.help import HelpHandler
    return HelpHandler()


# ---------------------------------------------------------------------------
# show_help - direct command
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_show_help_command(make_update, make_context):
    """show_help replies with help text containing enabled service commands."""
    with _help_patches(radarr=True, sonarr=True, lidarr=True):
        handler = _make_handler()
        update = make_update(text="/help")
        await handler.show_help(update, make_context())

        help_text = update.message.reply_text.call_args[0][0]
        assert "HelpHeader" in help_text
        assert "HelpBasicCommands" in help_text
        assert "HelpMediaMovies" in help_text
        assert "HelpMediaSeries" in help_text
        assert "HelpMediaMusic" in help_text


@pytest.mark.asyncio
async def test_show_help_hides_disabled_services(make_update, make_context):
    """show_help omits media commands when services are disabled."""
    with _help_patches():
        handler = _make_handler()
        update = make_update(text="/help")
        await handler.show_help(update, make_context())

        help_text = update.message.reply_text.call_args[0][0]
        assert "HelpMediaMovies" not in help_text
        assert "HelpMediaSeries" not in help_text
        assert "HelpMediaMusic" not in help_text


@pytest.mark.asyncio
async def test_show_help_shows_version(make_update, make_context):
    """show_help includes the bot version from src.__version__."""
    with _help_patches():
        handler = _make_handler()
        update = make_update(text="/help")
        await handler.show_help(update, make_context())

        help_text = update.message.reply_text.call_args[0][0]
        assert "HelpVersion" in help_text


@pytest.mark.asyncio
async def test_show_help_shows_download_clients(make_update, make_context):
    """show_help includes download client commands when enabled."""
    with _help_patches(transmission=True, sabnzbd=True):
        handler = _make_handler()
        update = make_update(text="/help")
        await handler.show_help(update, make_context())

        help_text = update.message.reply_text.call_args[0][0]
        assert "HelpDownloadTransmission" in help_text
        assert "HelpDownloadSabnzbd" in help_text


@pytest.mark.asyncio
async def test_show_help_shows_bazarr(make_update, make_context):
    """show_help includes subtitles section when bazarr is enabled."""
    with _help_patches(bazarr=True):
        handler = _make_handler()
        update = make_update(text="/help")
        await handler.show_help(update, make_context())

        help_text = update.message.reply_text.call_args[0][0]
        assert "HelpSubtitlesBazarr" in help_text


@pytest.mark.asyncio
async def test_show_help_hides_download_clients(make_update, make_context):
    """show_help omits download client commands when disabled."""
    with _help_patches():
        handler = _make_handler()
        update = make_update(text="/help")
        await handler.show_help(update, make_context())

        help_text = update.message.reply_text.call_args[0][0]
        assert "HelpDownloadTransmission" not in help_text
        assert "HelpDownloadSabnzbd" not in help_text


@pytest.mark.asyncio
async def test_show_help_callback(make_update, make_context):
    """show_help via callback query edits message text."""
    with _help_patches():
        handler = _make_handler()
        update = make_update(callback_data="menu_help")
        await handler.show_help(update, make_context())

        update.callback_query.message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_show_help_no_user(make_update, make_context):
    """show_help returns when no effective_user."""
    with _help_patches():
        handler = _make_handler()
        update = make_update(text="/help")
        update.effective_user = None

        result = await handler.show_help(update, make_context())

        assert result is None


# ---------------------------------------------------------------------------
# handle_back
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_back(make_update, make_context):
    """handle_back edits message with welcome text and main menu keyboard."""
    with _help_patches():
        handler = _make_handler()
        update = make_update(callback_data="menu_back")
        await handler.handle_back(update, make_context())

        update.callback_query.answer.assert_called_once()
        update.callback_query.message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_back_no_callback(make_update, make_context):
    """handle_back returns early if no callback query."""
    with _help_patches():
        handler = _make_handler()
        update = make_update(text="/back")

        result = await handler.handle_back(update, make_context())
        assert result is None


# ---------------------------------------------------------------------------
# get_handler
# ---------------------------------------------------------------------------


def test_get_handler_returns_list():
    """get_handler returns a list of handlers."""
    with _help_patches():
        handler = _make_handler()
        handlers = handler.get_handler()

        assert isinstance(handlers, list)
        assert len(handlers) > 0
