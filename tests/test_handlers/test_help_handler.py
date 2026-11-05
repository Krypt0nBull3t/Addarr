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
async def test_show_help_callback_has_back_button(make_update, make_context):
    """show_help via callback query offers a Back button to the main menu."""
    with _help_patches():
        handler = _make_handler()
        update = make_update(callback_data="menu_help")
        await handler.show_help(update, make_context())

        markup = update.callback_query.message.edit_text.call_args.kwargs[
            "reply_markup"
        ]
        callbacks = [b.callback_data for row in markup.inline_keyboard for b in row]
        assert callbacks == ["menu_back"]


@pytest.mark.asyncio
async def test_show_help_command_disables_link_preview(make_update, make_context):
    """The /help reply turns the link preview off with link_preview_options."""
    with _help_patches():
        handler = _make_handler()
        update = make_update(text="/help")
        await handler.show_help(update, make_context())

        kwargs = update.message.reply_text.call_args.kwargs
        assert kwargs["link_preview_options"].is_disabled is True
        assert "disable_web_page_preview" not in kwargs


@pytest.mark.asyncio
async def test_show_help_callback_disables_link_preview(make_update, make_context):
    """The Help callback edit turns the link preview off with link_preview_options."""
    with _help_patches():
        handler = _make_handler()
        update = make_update(callback_data="menu_help")
        await handler.show_help(update, make_context())

        kwargs = update.callback_query.message.edit_text.call_args.kwargs
        assert kwargs["link_preview_options"].is_disabled is True
        assert "disable_web_page_preview" not in kwargs


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


# ---------------------------------------------------------------------------
# Help text against the shipped en-us file and the registered commands (F120)
# ---------------------------------------------------------------------------

ALL_SERVICES = dict(radarr=True, sonarr=True, lidarr=True,
                    transmission=True, sabnzbd=True, bazarr=True)
NEW_COMMANDS = ["/preferences", "/webhooks", "/upcoming", "/missing",
                "/queue", "/history", "/downloads"]


def _en_us_translation():
    """A TranslationService stand-in that reads the shipped en-us file."""
    import yaml
    from pathlib import Path

    path = Path(__file__).parents[2] / "translations" / "addarr.en-us.yml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))["en-us"]

    def get_text(key, **kw):
        value = data[key]
        return value % kw if kw else value

    mock_ts = MagicMock()
    mock_ts.get_text = get_text
    return MagicMock(return_value=mock_ts)


def _real_help_text(**config_kwargs):
    config = _make_config(**config_kwargs)
    with patch("src.bot.handlers.help.TranslationService",
               _en_us_translation()), \
         patch("src.bot.handlers.help.config", config):
        return _make_handler()._build_help_text()


def test_help_lists_new_commands_and_no_library():
    """Help lists the 7 commands the bot registers, and no /library."""
    help_text = _real_help_text(**ALL_SERVICES)

    for command in NEW_COMMANDS:
        assert command in help_text
    assert "/library" not in help_text


def test_help_hides_arr_and_download_commands_when_off():
    """With every service off, gated commands are absent, the rest stay."""
    help_text = _real_help_text()

    for command in ["/upcoming", "/missing", "/queue", "/history",
                    "/downloads"]:
        assert command not in help_text
    assert "/preferences" in help_text
    assert "/webhooks" in help_text


@pytest.mark.parametrize("services", [
    {},
    {"radarr": True},
    {"sonarr": True},
    {"lidarr": True},
    {"transmission": True},
    {"sabnzbd": True},
    {"bazarr": True},
    ALL_SERVICES,
])
def test_help_matches_registered_commands(services):
    """Help lists exactly the commands build_authenticated_commands registers."""
    import re
    from src.bot.commands import build_authenticated_commands

    with patch("src.bot.commands.config", _make_config(**services)):
        registered = {c.command for c in build_authenticated_commands()}

    help_text = _real_help_text(**services)

    assert set(re.findall(r"/(\w+) -", help_text)) == registered
