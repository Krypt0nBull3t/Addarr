"""
Tests for src/bot/handlers/sabnzbd.py - SabnzbdHandler.

SabnzbdHandler.__init__ creates SABnzbdService() inside a try/except.
If SABnzbdService() raises (e.g., sabnzbd not enabled), self.sabnzbd_service
is set to None. get_handler returns [] when service is None.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


# ---------------------------------------------------------------------------
# handle_sabnzbd - service not available
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.sabnzbd.TranslationService")
@patch("src.bot.handlers.sabnzbd.SABnzbdService")
async def test_handle_sabnzbd_not_available(
    mock_sab_class, mock_ts_class, make_update, make_context
):
    """When sabnzbd_service is None, reply with 'not enabled' message."""
    # SABnzbdService() raises -> service set to None
    mock_sab_class.side_effect = ValueError("SABnzbd is not enabled")

    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.sabnzbd import SabnzbdHandler
    from src.bot.handlers.auth import AuthHandler

    AuthHandler._authenticated_users = {12345}

    handler = SabnzbdHandler()
    assert handler.sabnzbd_service is None

    # Manually set translation since __init__ may not set it when exception occurs
    handler.translation = mock_ts

    update = make_update(text="/sabnzbd")
    context = make_context()

    await handler.handle_sabnzbd(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    assert "NotEnabled" in str(call_args) or "Sabnzbd" in str(call_args)


# ---------------------------------------------------------------------------
# handle_sabnzbd - service available
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.sabnzbd.TranslationService")
@patch("src.bot.handlers.sabnzbd.SABnzbdService")
async def test_handle_sabnzbd_available(
    mock_sab_class, mock_ts_class, make_update, make_context
):
    """When sabnzbd service is available, show speed selection keyboard."""
    mock_sab = MagicMock()
    mock_sab_class.return_value = mock_sab

    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.sabnzbd import SabnzbdHandler
    from src.bot.handlers.auth import AuthHandler

    AuthHandler._authenticated_users = {12345}

    handler = SabnzbdHandler()
    assert handler.sabnzbd_service is not None

    update = make_update(text="/sabnzbd")
    context = make_context()

    await handler.handle_sabnzbd(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    # Verify reply_markup was passed (speed keyboard)
    assert call_args[1].get("reply_markup") is not None


# ---------------------------------------------------------------------------
# get_handler - service not available
# ---------------------------------------------------------------------------


@patch("src.bot.handlers.sabnzbd.TranslationService")
@patch("src.bot.handlers.sabnzbd.SABnzbdService")
def test_get_handler_returns_empty_when_unavailable(mock_sab_class, mock_ts_class):
    """get_handler returns empty list when service is not available."""
    mock_sab_class.side_effect = ValueError("SABnzbd is not enabled")
    mock_ts = MagicMock()
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.sabnzbd import SabnzbdHandler

    handler = SabnzbdHandler()
    handlers = handler.get_handler()

    assert isinstance(handlers, list)
    assert len(handlers) == 0


# ---------------------------------------------------------------------------
# get_handler - service available
# ---------------------------------------------------------------------------


@patch("src.bot.handlers.sabnzbd.TranslationService")
@patch("src.bot.handlers.sabnzbd.SABnzbdService")
def test_get_handler_returns_list(mock_sab_class, mock_ts_class):
    """get_handler returns a list of handlers when service is available."""
    mock_sab_class.return_value = MagicMock()
    mock_ts = MagicMock()
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.sabnzbd import SabnzbdHandler

    handler = SabnzbdHandler()
    handlers = handler.get_handler()

    assert isinstance(handlers, list)
    assert len(handlers) > 0
