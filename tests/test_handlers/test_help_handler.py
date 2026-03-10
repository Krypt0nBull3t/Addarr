"""
Tests for src/bot/handlers/help.py - HelpHandler with show_help and handle_back.

HelpHandler.__init__ creates TranslationService().
show_help builds dynamic help text from translations, filtered by enabled services.
handle_back returns to the main menu (decorated with @require_auth).
"""

import pytest
from unittest.mock import patch, MagicMock


def _make_config(radarr=False, sonarr=False, lidarr=False,
                 transmission=False, sabnzbd=False):
    """Build a mock config dict with service enable flags."""
    data = {
        "radarr": {"enable": True} if radarr else {},
        "sonarr": {"enable": True} if sonarr else {},
        "lidarr": {"enable": True} if lidarr else {},
        "transmission": {"enable": True} if transmission else {},
        "sabnzbd": {"enable": True} if sabnzbd else {},
    }
    mock = MagicMock()
    mock.get = lambda key, default=None: data.get(
        key, default if default is not None else {}
    )
    return mock


def _make_translation_mock():
    mock_ts_class = MagicMock()
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts
    return mock_ts_class


# ---------------------------------------------------------------------------
# show_help - direct command
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_show_help_command(make_update, make_context):
    """show_help replies with help text containing enabled service commands."""
    mock_config = _make_config(radarr=True, sonarr=True, lidarr=True)

    with patch("src.bot.handlers.help.TranslationService", _make_translation_mock()), \
         patch("src.bot.handlers.help.config", mock_config), \
         patch("src.bot.handlers.help.get_main_menu_keyboard"):

        from src.bot.handlers.help import HelpHandler
        from src.bot.handlers.auth import AuthHandler
        AuthHandler._authenticated_users = {12345}

        handler = HelpHandler()
        update = make_update(text="/help")
        context = make_context()

        await handler.show_help(update, context)

        update.message.reply_text.assert_called_once()
        help_text = update.message.reply_text.call_args[0][0]
        assert "HelpHeader" in help_text
        assert "HelpBasicCommands" in help_text
        assert "HelpMediaMovies" in help_text
        assert "HelpMediaSeries" in help_text
        assert "HelpMediaMusic" in help_text


@pytest.mark.asyncio
async def test_show_help_hides_disabled_services(make_update, make_context):
    """show_help omits media commands when services are disabled."""
    mock_config = _make_config()

    with patch("src.bot.handlers.help.TranslationService", _make_translation_mock()), \
         patch("src.bot.handlers.help.config", mock_config), \
         patch("src.bot.handlers.help.get_main_menu_keyboard"):

        from src.bot.handlers.help import HelpHandler
        from src.bot.handlers.auth import AuthHandler
        AuthHandler._authenticated_users = {12345}

        handler = HelpHandler()
        update = make_update(text="/help")
        context = make_context()

        await handler.show_help(update, context)

        help_text = update.message.reply_text.call_args[0][0]
        assert "HelpMediaMovies" not in help_text
        assert "HelpMediaSeries" not in help_text
        assert "HelpMediaMusic" not in help_text


@pytest.mark.asyncio
async def test_show_help_shows_version(make_update, make_context):
    """show_help includes the bot version from src.__version__."""
    mock_config = _make_config()

    with patch("src.bot.handlers.help.TranslationService", _make_translation_mock()), \
         patch("src.bot.handlers.help.config", mock_config), \
         patch("src.bot.handlers.help.get_main_menu_keyboard"):

        from src.bot.handlers.help import HelpHandler
        from src.bot.handlers.auth import AuthHandler
        AuthHandler._authenticated_users = {12345}

        handler = HelpHandler()
        update = make_update(text="/help")
        context = make_context()

        await handler.show_help(update, context)

        help_text = update.message.reply_text.call_args[0][0]
        assert "HelpVersion" in help_text


@pytest.mark.asyncio
async def test_show_help_shows_download_clients(make_update, make_context):
    """show_help includes download client commands when enabled."""
    mock_config = _make_config(transmission=True, sabnzbd=True)

    with patch("src.bot.handlers.help.TranslationService", _make_translation_mock()), \
         patch("src.bot.handlers.help.config", mock_config), \
         patch("src.bot.handlers.help.get_main_menu_keyboard"):

        from src.bot.handlers.help import HelpHandler
        from src.bot.handlers.auth import AuthHandler
        AuthHandler._authenticated_users = {12345}

        handler = HelpHandler()
        update = make_update(text="/help")
        context = make_context()

        await handler.show_help(update, context)

        help_text = update.message.reply_text.call_args[0][0]
        assert "HelpDownloadTransmission" in help_text
        assert "HelpDownloadSabnzbd" in help_text


@pytest.mark.asyncio
async def test_show_help_hides_download_clients(make_update, make_context):
    """show_help omits download client commands when disabled."""
    mock_config = _make_config()

    with patch("src.bot.handlers.help.TranslationService", _make_translation_mock()), \
         patch("src.bot.handlers.help.config", mock_config), \
         patch("src.bot.handlers.help.get_main_menu_keyboard"):

        from src.bot.handlers.help import HelpHandler
        from src.bot.handlers.auth import AuthHandler
        AuthHandler._authenticated_users = {12345}

        handler = HelpHandler()
        update = make_update(text="/help")
        context = make_context()

        await handler.show_help(update, context)

        help_text = update.message.reply_text.call_args[0][0]
        assert "HelpDownloadTransmission" not in help_text
        assert "HelpDownloadSabnzbd" not in help_text


@pytest.mark.asyncio
async def test_show_help_callback(make_update, make_context):
    """show_help via callback query edits message text."""
    mock_config = _make_config()

    with patch("src.bot.handlers.help.TranslationService", _make_translation_mock()), \
         patch("src.bot.handlers.help.config", mock_config), \
         patch("src.bot.handlers.help.get_main_menu_keyboard"):

        from src.bot.handlers.help import HelpHandler
        from src.bot.handlers.auth import AuthHandler
        AuthHandler._authenticated_users = {12345}

        handler = HelpHandler()
        update = make_update(callback_data="menu_help")
        context = make_context()

        await handler.show_help(update, context)

        update.callback_query.message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_show_help_no_user(make_update, make_context):
    """show_help returns when no effective_user."""
    mock_config = _make_config()

    with patch("src.bot.handlers.help.TranslationService", _make_translation_mock()), \
         patch("src.bot.handlers.help.config", mock_config), \
         patch("src.bot.handlers.help.get_main_menu_keyboard"):

        from src.bot.handlers.help import HelpHandler
        from src.bot.handlers.auth import AuthHandler
        AuthHandler._authenticated_users = {12345}

        handler = HelpHandler()
        update = make_update(text="/help")
        update.effective_user = None
        context = make_context()

        result = await handler.show_help(update, context)

        assert result is None


# ---------------------------------------------------------------------------
# handle_back
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.help.get_main_menu_keyboard")
@patch("src.bot.handlers.help.TranslationService")
async def test_handle_back(
    mock_ts_class, mock_keyboard, make_update, make_context
):
    """handle_back edits message with welcome text and main menu keyboard."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts
    mock_keyboard.return_value = MagicMock()

    from src.bot.handlers.help import HelpHandler
    from src.bot.handlers.auth import AuthHandler

    AuthHandler._authenticated_users = {12345}

    handler = HelpHandler()
    update = make_update(callback_data="menu_back")
    context = make_context()

    await handler.handle_back(update, context)

    update.callback_query.answer.assert_called_once()
    update.callback_query.message.edit_text.assert_called_once()


@pytest.mark.asyncio
@patch("src.bot.handlers.help.get_main_menu_keyboard")
@patch("src.bot.handlers.help.TranslationService")
async def test_handle_back_no_callback(
    mock_ts_class, mock_keyboard, make_update, make_context
):
    """handle_back returns early if no callback query."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.help import HelpHandler
    from src.bot.handlers.auth import AuthHandler

    AuthHandler._authenticated_users = {12345}

    handler = HelpHandler()
    update = make_update(text="/back")
    context = make_context()

    result = await handler.handle_back(update, context)
    assert result is None


# ---------------------------------------------------------------------------
# get_handler
# ---------------------------------------------------------------------------


@patch("src.bot.handlers.help.TranslationService")
def test_get_handler_returns_list(mock_ts_class):
    """get_handler returns a list of handlers."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.help import HelpHandler

    handler = HelpHandler()
    handlers = handler.get_handler()

    assert isinstance(handlers, list)
    assert len(handlers) > 0
