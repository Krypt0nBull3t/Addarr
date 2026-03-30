"""
Tests for src/bot/handlers/system.py - SystemHandler.

SystemHandler owns /status and system_* callbacks.  show_status and
handle_system_action are decorated with @require_auth.
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from tests.fixtures.sample_data import RADARR_DISK_SPACE


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
    update.callback_query.message.edit_text.assert_called_once()
    system_handler._mock_ts.get_text.assert_any_call("StatusRefreshed")


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
    system_handler._mock_ts.get_text.assert_any_call("StatusRefreshError")


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

    system_handler._mock_ts.get_text.assert_any_call("StatusDetailsError")


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
    """Unknown system action answers with error toast and re-renders status."""
    update = make_update(callback_data="system_foobar")
    context = make_context()

    await system_handler.handle_system_action(update, context)

    update.callback_query.answer.assert_called_once()
    system_handler._mock_ts.get_text.assert_any_call("UnknownAction")
    # Message must be edited so the loading animation clears
    update.callback_query.message.edit_text.assert_called_once()


@pytest.mark.asyncio
async def test_handle_unknown_action_logs_warning(
    system_handler, make_update, make_context
):
    """Unknown system action logs a warning with the action name."""
    update = make_update(callback_data="system_foobar")
    context = make_context()

    with patch("src.bot.handlers.system.logger") as mock_logger:
        await system_handler.handle_system_action(update, context)

    mock_logger.warning.assert_called_once()
    warning_msg = mock_logger.warning.call_args[0][0]
    assert "foobar" in warning_msg


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


# ---------------------------------------------------------------------------
# _format_usage_bar / _format_bytes (module-level functions)
# ---------------------------------------------------------------------------


def test_format_usage_bar_zero():
    """0% usage shows empty bar."""
    from src.bot.handlers.system import _format_usage_bar
    bar = _format_usage_bar(0)
    assert "░" in bar
    assert "█" not in bar


def test_format_usage_bar_half():
    """50% usage shows half-filled bar."""
    from src.bot.handlers.system import _format_usage_bar
    bar = _format_usage_bar(50)
    assert "█" in bar
    assert "░" in bar


def test_format_usage_bar_full():
    """100% usage shows full bar."""
    from src.bot.handlers.system import _format_usage_bar
    bar = _format_usage_bar(100)
    assert "█" in bar
    assert "░" not in bar


def test_format_bytes_zero():
    """0 bytes formats as 0 B."""
    from src.utils.helpers import format_bytes
    assert format_bytes(0) == "0.0 B"


def test_format_bytes_gb():
    """GB range formats correctly."""
    from src.utils.helpers import format_bytes
    result = format_bytes(1500000000)  # ~1.4 GB
    assert "GB" in result


def test_format_bytes_tb():
    """TB range formats correctly."""
    from src.utils.helpers import format_bytes
    result = format_bytes(2000000000000)  # ~1.82 TB
    assert "TB" in result


# ---------------------------------------------------------------------------
# handle_system_action — diskspace
# ---------------------------------------------------------------------------


def test_build_disk_space_text_zero_total():
    """Drive with totalSpace=0 shows 0% used."""
    from src.bot.handlers.system import _build_disk_space_text
    from unittest.mock import MagicMock
    translation = MagicMock()
    translation.get_text = MagicMock(side_effect=lambda key, **kw: key)
    drives = [{"path": "/empty", "freeSpace": 0, "totalSpace": 0}]
    text = _build_disk_space_text(drives, translation)
    assert "0%" in text
    assert "/empty" in text


@pytest.mark.asyncio
async def test_handle_diskspace(system_handler, make_update, make_context):
    """system_diskspace shows drives with percentage."""
    system_handler._mock_health.get_disk_space = AsyncMock(
        return_value=RADARR_DISK_SPACE
    )
    update = make_update(callback_data="system_diskspace")
    context = make_context()

    await system_handler.handle_system_action(update, context)

    call_args = update.callback_query.message.edit_text.call_args
    text = call_args[0][0]
    assert "/movies" in text
    assert "%" in text


@pytest.mark.asyncio
async def test_handle_diskspace_empty(system_handler, make_update, make_context):
    """system_diskspace shows 'no data' when empty."""
    system_handler._mock_health.get_disk_space = AsyncMock(return_value=[])
    update = make_update(callback_data="system_diskspace")
    context = make_context()

    await system_handler.handle_system_action(update, context)

    call_args = update.callback_query.message.edit_text.call_args
    text = call_args[0][0]
    assert "DiskSpaceNone" in text


@pytest.mark.asyncio
async def test_handle_diskspace_error(system_handler, make_update, make_context):
    """system_diskspace shows error on exception."""
    system_handler._mock_health.get_disk_space = AsyncMock(
        side_effect=Exception("connection refused")
    )
    update = make_update(callback_data="system_diskspace")
    context = make_context()

    await system_handler.handle_system_action(update, context)

    # get_text is called with default= kwarg
    calls = [c[0][0] for c in system_handler._mock_ts.get_text.call_args_list]
    assert "DiskSpaceFailed" in calls


@pytest.mark.asyncio
async def test_handle_diskspace_low_space(system_handler, make_update, make_context):
    """Drives with <10% free show warning emoji."""
    low_space_drives = [
        {
            "path": "/movies",
            "label": "Movies",
            "freeSpace": 5000000000,
            "totalSpace": 1000000000000,
        },
    ]
    system_handler._mock_health.get_disk_space = AsyncMock(
        return_value=low_space_drives
    )
    update = make_update(callback_data="system_diskspace")
    context = make_context()

    await system_handler.handle_system_action(update, context)

    call_args = update.callback_query.message.edit_text.call_args
    text = call_args[0][0]
    # Should contain warning indicator for low space
    assert "⚠" in text
