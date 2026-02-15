"""
Tests for src/bot/handlers/sabnzbd.py - SabnzbdHandler.

SabnzbdHandler.__init__ creates SABnzbdService() inside a try/except.
If SABnzbdService() raises (e.g., sabnzbd not enabled), self.sabnzbd_service
is set to None. get_handler returns [] when service is None.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


# ---------------------------------------------------------------------------
# handle_sabnzbd
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.sabnzbd.TranslationService")
@patch("src.bot.handlers.sabnzbd.SABnzbdService")
async def test_handle_sabnzbd_not_available(
    mock_sab_class, mock_ts_class, make_update, make_context
):
    """When sabnzbd_service is None, reply with 'not enabled' message."""
    mock_sab_class.side_effect = ValueError("SABnzbd is not enabled")

    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.sabnzbd import SabnzbdHandler
    from src.bot.handlers.auth import AuthHandler

    AuthHandler._authenticated_users = {12345}

    handler = SabnzbdHandler()
    assert handler.sabnzbd_service is None

    handler.translation = mock_ts

    update = make_update(text="/sabnzbd")
    context = make_context()

    await handler.handle_sabnzbd(update, context)

    update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
@patch("src.bot.handlers.sabnzbd.TranslationService")
@patch("src.bot.handlers.sabnzbd.SABnzbdService")
async def test_handle_sabnzbd_available(
    mock_sab_class, mock_ts_class, make_update, make_context
):
    """When sabnzbd service is available, show speed selection keyboard."""
    mock_sab_class.return_value = MagicMock()

    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.sabnzbd import SabnzbdHandler
    from src.bot.handlers.auth import AuthHandler

    AuthHandler._authenticated_users = {12345}

    handler = SabnzbdHandler()

    update = make_update(text="/sabnzbd")
    context = make_context()

    await handler.handle_sabnzbd(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    assert call_args[1].get("reply_markup") is not None


@pytest.mark.asyncio
@patch("src.bot.handlers.sabnzbd.TranslationService")
@patch("src.bot.handlers.sabnzbd.SABnzbdService")
async def test_handle_sabnzbd_no_user(
    mock_sab_class, mock_ts_class, make_update, make_context
):
    """handle_sabnzbd returns when no effective_user."""
    mock_sab_class.return_value = MagicMock()
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.sabnzbd import SabnzbdHandler
    from src.bot.handlers.auth import AuthHandler

    AuthHandler._authenticated_users = {12345}

    handler = SabnzbdHandler()
    update = make_update(text="/sabnzbd")
    update.effective_user = None
    context = make_context()

    result = await handler.handle_sabnzbd(update, context)

    assert result is None


# ---------------------------------------------------------------------------
# handle_speed_selection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("speed", [25, 50, 100])
@pytest.mark.asyncio
@patch("src.bot.handlers.sabnzbd.TranslationService")
@patch("src.bot.handlers.sabnzbd.SABnzbdService")
async def test_handle_speed_selection_success(
    mock_sab_class, mock_ts_class, make_update, make_context, speed
):
    """Speed selection sets speed and shows confirmation."""
    mock_sab = MagicMock()
    mock_sab.set_speed_limit = AsyncMock(return_value=True)
    mock_sab_class.return_value = mock_sab

    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.sabnzbd import SabnzbdHandler

    handler = SabnzbdHandler()

    update = make_update(callback_data=f"sabnzbd_speed_{speed}")
    context = make_context()

    await handler.handle_speed_selection(update, context)

    update.callback_query.answer.assert_called_once()
    update.callback_query.message.edit_text.assert_called_once()
    mock_sab.set_speed_limit.assert_awaited_once_with(speed)


@pytest.mark.asyncio
@patch("src.bot.handlers.sabnzbd.TranslationService")
@patch("src.bot.handlers.sabnzbd.SABnzbdService")
async def test_handle_speed_selection_exception(
    mock_sab_class, mock_ts_class, make_update, make_context
):
    """Speed selection with error shows error message."""
    mock_sab = MagicMock()
    mock_sab.set_speed_limit = AsyncMock(side_effect=Exception("Error"))
    mock_sab_class.return_value = mock_sab

    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.sabnzbd import SabnzbdHandler

    handler = SabnzbdHandler()

    update = make_update(callback_data="sabnzbd_speed_50")
    context = make_context()

    await handler.handle_speed_selection(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert "Error" in str(call_args)


@pytest.mark.asyncio
@patch("src.bot.handlers.sabnzbd.TranslationService")
@patch("src.bot.handlers.sabnzbd.SABnzbdService")
async def test_handle_speed_selection_no_query(
    mock_sab_class, mock_ts_class, make_update, make_context
):
    """handle_speed_selection returns when no callback_query."""
    mock_sab_class.return_value = MagicMock()
    mock_ts = MagicMock()
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.sabnzbd import SabnzbdHandler

    handler = SabnzbdHandler()
    update = make_update(text="/test")
    update.callback_query = None
    context = make_context()

    result = await handler.handle_speed_selection(update, context)

    assert result is None


# ---------------------------------------------------------------------------
# get_handler
# ---------------------------------------------------------------------------


@patch("src.bot.handlers.sabnzbd.TranslationService")
@patch("src.bot.handlers.sabnzbd.SABnzbdService")
def test_get_handler_returns_empty_when_unavailable(mock_sab_class, mock_ts_class):
    """get_handler returns empty list when service is not available."""
    mock_sab_class.side_effect = ValueError("SABnzbd is not enabled")
    mock_ts_class.return_value = MagicMock()

    from src.bot.handlers.sabnzbd import SabnzbdHandler

    handler = SabnzbdHandler()
    handlers = handler.get_handler()

    assert isinstance(handlers, list)
    assert len(handlers) == 0


@patch("src.bot.handlers.sabnzbd.TranslationService")
@patch("src.bot.handlers.sabnzbd.SABnzbdService")
def test_get_handler_returns_list(mock_sab_class, mock_ts_class):
    """get_handler returns a list of handlers when service is available."""
    mock_sab_class.return_value = MagicMock()
    mock_ts_class.return_value = MagicMock()

    from src.bot.handlers.sabnzbd import SabnzbdHandler

    handler = SabnzbdHandler()
    handlers = handler.get_handler()

    assert isinstance(handlers, list)
    assert len(handlers) > 0
