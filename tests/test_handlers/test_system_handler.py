"""
Tests for src/bot/handlers/system.py - SystemHandler.

SystemHandler owns /status and system_* callbacks.  show_status and
handle_system_action are decorated with @require_auth.
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime


# ---------------------------------------------------------------------------
# show_status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_show_status_direct(system_handler, make_update, make_context):
    """show_status replies with status text and system keyboard via command."""
    update = make_update(text="/status")
    context = make_context()

    await system_handler.show_status(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    assert "Status" in call_args[0][0]
    assert call_args[1]["reply_markup"] == system_handler._mock_kbd.return_value


@pytest.mark.asyncio
async def test_show_status_callback(system_handler, make_update, make_context):
    """show_status edits message when invoked via callback query."""
    update = make_update(callback_data="menu_status")
    context = make_context()

    await system_handler.show_status(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert "Status" in call_args[0][0]


@pytest.mark.asyncio
async def test_show_status_includes_health_info(
    system_handler, make_update, make_context
):
    """show_status includes running state and healthy message."""
    update = make_update(text="/status")
    context = make_context()

    await system_handler.show_status(update, context)

    status_text = update.message.reply_text.call_args[0][0]
    assert "Running" in status_text or "Stopped" in status_text


@pytest.mark.asyncio
async def test_show_status_with_last_check(
    system_handler, make_update, make_context
):
    """show_status shows last check time when available."""
    system_handler._mock_health.get_status.return_value = {
        "running": True,
        "last_check": datetime(2024, 1, 1, 12, 0, 0),
        "unhealthy_services": [],
    }
    update = make_update(text="/status")
    context = make_context()

    await system_handler.show_status(update, context)

    status_text = update.message.reply_text.call_args[0][0]
    assert "2024" in status_text


@pytest.mark.asyncio
async def test_show_status_with_unhealthy(
    system_handler, make_update, make_context
):
    """show_status lists unhealthy services."""
    system_handler._mock_health.get_status.return_value = {
        "running": True,
        "last_check": None,
        "unhealthy_services": ["Radarr: Connection failed"],
    }
    update = make_update(text="/status")
    context = make_context()

    await system_handler.show_status(update, context)

    status_text = update.message.reply_text.call_args[0][0]
    assert "Radarr" in status_text


@pytest.mark.asyncio
async def test_show_status_no_user(system_handler, make_update, make_context):
    """show_status returns None when effective_user is None."""
    update = make_update(text="/status")
    update.effective_user = None
    context = make_context()

    result = await system_handler.show_status(update, context)
    assert result is None


@pytest.mark.asyncio
@patch("src.bot.handlers.system.health_service")
@patch("src.bot.handlers.system.get_system_keyboard")
@patch("src.bot.handlers.system.get_main_menu_keyboard")
async def test_show_status_not_authenticated(
    mock_menu_kbd, mock_kbd, mock_health, make_update, make_context
):
    """show_status rejects unauthenticated users via @require_auth."""
    from src.bot.handlers.system import SystemHandler
    from src.bot.handlers.auth import AuthHandler

    AuthHandler._authenticated_users = set()
    handler = SystemHandler()
    update = make_update(text="/status")
    context = make_context()

    result = await handler.show_status(update, context)
    assert result is None


# ---------------------------------------------------------------------------
# handle_system_action — refresh
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_refresh(system_handler, make_update, make_context):
    """system_refresh re-runs health checks and edits message."""
    system_handler._mock_health.run_health_checks = AsyncMock(return_value={
        "media_services": [
            {"name": "Radarr", "healthy": True, "status": "Online (v5.0)"}
        ],
        "download_clients": [],
    })
    update = make_update(callback_data="system_refresh")
    context = make_context()

    await system_handler.handle_system_action(update, context)

    system_handler._mock_health.run_health_checks.assert_awaited_once()
    update.callback_query.answer.assert_called_once()
    update.callback_query.message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_refresh_error(system_handler, make_update, make_context):
    """system_refresh shows error on exception."""
    system_handler._mock_health.run_health_checks = AsyncMock(
        side_effect=Exception("Connection failed")
    )
    update = make_update(callback_data="system_refresh")
    context = make_context()

    await system_handler.handle_system_action(update, context)

    update.callback_query.answer.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert "Error" in call_args[0][0]


# ---------------------------------------------------------------------------
# handle_system_action — details
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_details(system_handler, make_update, make_context):
    """system_details shows per-service health information."""
    system_handler._mock_health.run_health_checks = AsyncMock(return_value={
        "media_services": [
            {"name": "Radarr", "healthy": True, "status": "Online (v5.0)"},
            {"name": "Sonarr", "healthy": False, "status": "Error: HTTP 500"},
        ],
        "download_clients": [
            {"name": "SABnzbd", "healthy": True, "status": "Online (v4.0)"},
        ],
    })
    update = make_update(callback_data="system_details")
    context = make_context()

    await system_handler.handle_system_action(update, context)

    system_handler._mock_health.run_health_checks.assert_awaited_once()
    call_args = update.callback_query.message.edit_text.call_args
    details_text = call_args[0][0]
    assert "Radarr" in details_text
    assert "Sonarr" in details_text
    assert "SABnzbd" in details_text


@pytest.mark.asyncio
async def test_handle_details_empty(system_handler, make_update, make_context):
    """system_details shows message when no services are enabled."""
    update = make_update(callback_data="system_details")
    context = make_context()

    await system_handler.handle_system_action(update, context)

    call_args = update.callback_query.message.edit_text.call_args
    assert "No services" in call_args[0][0]


@pytest.mark.asyncio
async def test_handle_details_error(system_handler, make_update, make_context):
    """system_details shows error on exception."""
    system_handler._mock_health.run_health_checks = AsyncMock(
        side_effect=Exception("Timeout")
    )
    update = make_update(callback_data="system_details")
    context = make_context()

    await system_handler.handle_system_action(update, context)

    call_args = update.callback_query.message.edit_text.call_args
    assert "Error" in call_args[0][0]


# ---------------------------------------------------------------------------
# handle_system_action — back
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_back(system_handler, make_update, make_context):
    """system_back edits message with main menu keyboard."""
    update = make_update(callback_data="system_back")
    context = make_context()

    await system_handler.handle_system_action(update, context)

    update.callback_query.message.edit_text.assert_called_once()
    call_args = update.callback_query.message.edit_text.call_args
    assert call_args[1]["reply_markup"] == \
        system_handler._mock_menu_kbd.return_value


# ---------------------------------------------------------------------------
# handle_system_action — unknown / no callback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_unknown_action(
    system_handler, make_update, make_context
):
    """Unknown system action answers with error."""
    update = make_update(callback_data="system_foobar")
    context = make_context()

    await system_handler.handle_system_action(update, context)

    update.callback_query.answer.assert_called_once()
    call_args = update.callback_query.answer.call_args
    assert "Unknown" in str(call_args)


@pytest.mark.asyncio
async def test_handle_no_callback(system_handler, make_update, make_context):
    """handle_system_action returns None when no callback query."""
    update = make_update(text="/system")
    context = make_context()

    result = await system_handler.handle_system_action(update, context)
    assert result is None


# ---------------------------------------------------------------------------
# get_handler
# ---------------------------------------------------------------------------


def test_get_handler_returns_list(system_handler):
    """get_handler returns a list of handlers."""
    handlers = system_handler.get_handler()
    assert isinstance(handlers, list)
    assert len(handlers) >= 2
