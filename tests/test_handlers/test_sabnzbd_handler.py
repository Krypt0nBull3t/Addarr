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
    """When sabnzbd service is not enabled, reply with 'not enabled' message."""
    mock_sab = MagicMock()
    mock_sab.is_enabled.return_value = False
    mock_sab_class.return_value = mock_sab

    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.sabnzbd import SabnzbdHandler
    from src.bot.handlers.auth import AuthHandler

    AuthHandler._authenticated_users = {12345}

    handler = SabnzbdHandler()
    assert handler.sabnzbd_service.is_enabled() is False

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
    mock_sab = MagicMock()
    mock_sab.is_enabled.return_value = False
    mock_sab_class.return_value = mock_sab
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


# ---------------------------------------------------------------------------
# handle_downloads — /downloads command
# ---------------------------------------------------------------------------


def _make_handler_with_mocks(mock_sab_class, mock_ts_class, enabled=True):
    """Helper to create a SabnzbdHandler with properly configured mocks."""
    mock_sab = MagicMock()
    mock_sab.is_enabled.return_value = enabled
    mock_sab.get_queue_details = AsyncMock(return_value={
        'paused': False,
        'speed': '5.2 MB/s',
        'size_remaining': '1.2 GB',
        'items_count': 2,
        'items': [
            {
                'nzo_id': 'nzo_abc',
                'title': 'Movie.2024.1080p',
                'status': 'Downloading',
                'progress': 72,
                'size': '4.2 GB',
                'timeleft': '0:15:30',
            },
            {
                'nzo_id': 'nzo_def',
                'title': 'TV.Show.S03E05',
                'status': 'Queued',
                'progress': 0,
                'size': '1.1 GB',
                'timeleft': '0:45:00',
            },
        ],
    })
    mock_sab.get_history = AsyncMock(return_value={
        'total': 1,
        'items': [
            {
                'name': 'Completed.Movie',
                'status': 'Completed',
                'size': '4.2 GB',
                'download_time': 8100,
            },
        ],
    })
    mock_sab.pause_item = AsyncMock(return_value=True)
    mock_sab.resume_item = AsyncMock(return_value=True)
    mock_sab.pause_queue = AsyncMock(return_value=True)
    mock_sab.resume_queue = AsyncMock(return_value=True)
    mock_sab_class.return_value = mock_sab

    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.sabnzbd import SabnzbdHandler
    handler = SabnzbdHandler()
    return handler, mock_sab, mock_ts


@pytest.mark.asyncio
@patch("src.bot.handlers.sabnzbd.TranslationService")
@patch("src.bot.handlers.sabnzbd.SABnzbdService")
async def test_handle_downloads_shows_queue(
    mock_sab_class, mock_ts_class, make_update, make_context
):
    """handle_downloads shows queue view with keyboard."""
    from src.bot.handlers.auth import AuthHandler
    AuthHandler._authenticated_users = {12345}

    handler, mock_sab, _ = _make_handler_with_mocks(
        mock_sab_class, mock_ts_class
    )

    update = make_update(text="/downloads")
    context = make_context()

    await handler.handle_downloads(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    assert call_args[1].get("reply_markup") is not None
    mock_sab.get_queue_details.assert_awaited_once()


@pytest.mark.asyncio
@patch("src.bot.handlers.sabnzbd.TranslationService")
@patch("src.bot.handlers.sabnzbd.SABnzbdService")
async def test_handle_downloads_not_enabled(
    mock_sab_class, mock_ts_class, make_update, make_context
):
    """handle_downloads shows error when service not enabled."""
    from src.bot.handlers.auth import AuthHandler
    AuthHandler._authenticated_users = {12345}

    handler, _, _ = _make_handler_with_mocks(
        mock_sab_class, mock_ts_class, enabled=False
    )

    update = make_update(text="/downloads")
    context = make_context()

    await handler.handle_downloads(update, context)

    update.message.reply_text.assert_called_once()
    text_arg = update.message.reply_text.call_args[0][0]
    assert "DownloadsNotEnabled" in text_arg


@pytest.mark.asyncio
@patch("src.bot.handlers.sabnzbd.TranslationService")
@patch("src.bot.handlers.sabnzbd.SABnzbdService")
async def test_handle_downloads_no_user(
    mock_sab_class, mock_ts_class, make_update, make_context
):
    """handle_downloads returns early when no effective_user."""
    from src.bot.handlers.auth import AuthHandler
    AuthHandler._authenticated_users = {12345}

    handler, _, _ = _make_handler_with_mocks(
        mock_sab_class, mock_ts_class
    )

    update = make_update(text="/downloads")
    update.effective_user = None
    context = make_context()

    result = await handler.handle_downloads(update, context)
    assert result is None


# ---------------------------------------------------------------------------
# handle_downloads_tab — tab switching callbacks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.sabnzbd.TranslationService")
@patch("src.bot.handlers.sabnzbd.SABnzbdService")
async def test_tab_switch_to_history(
    mock_sab_class, mock_ts_class, make_update, make_context
):
    """dl_tab_history switches to history view."""
    handler, mock_sab, _ = _make_handler_with_mocks(
        mock_sab_class, mock_ts_class
    )

    update = make_update(callback_data="dl_tab_history")
    context = make_context()

    await handler.handle_downloads_tab(update, context)

    update.callback_query.answer.assert_called_once()
    update.callback_query.message.edit_text.assert_called_once()
    mock_sab.get_history.assert_awaited_once()


@pytest.mark.asyncio
@patch("src.bot.handlers.sabnzbd.TranslationService")
@patch("src.bot.handlers.sabnzbd.SABnzbdService")
async def test_tab_switch_to_queue(
    mock_sab_class, mock_ts_class, make_update, make_context
):
    """dl_tab_queue switches to queue view."""
    handler, mock_sab, _ = _make_handler_with_mocks(
        mock_sab_class, mock_ts_class
    )

    update = make_update(callback_data="dl_tab_queue")
    context = make_context()

    await handler.handle_downloads_tab(update, context)

    update.callback_query.answer.assert_called_once()
    update.callback_query.message.edit_text.assert_called_once()
    mock_sab.get_queue_details.assert_awaited_once()


# ---------------------------------------------------------------------------
# handle_downloads_page — pagination
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.sabnzbd.TranslationService")
@patch("src.bot.handlers.sabnzbd.SABnzbdService")
async def test_pagination_updates_page(
    mock_sab_class, mock_ts_class, make_update, make_context
):
    """dl_page_1 fetches queue and updates with page=1."""
    handler, mock_sab, _ = _make_handler_with_mocks(
        mock_sab_class, mock_ts_class
    )

    update = make_update(callback_data="dl_page_1")
    context = make_context(user_data={"dl_tab": "queue"})

    await handler.handle_downloads_page(update, context)

    update.callback_query.answer.assert_called_once()
    update.callback_query.message.edit_text.assert_called_once()


# ---------------------------------------------------------------------------
# handle_downloads_pause_item / resume_item
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.sabnzbd.TranslationService")
@patch("src.bot.handlers.sabnzbd.SABnzbdService")
async def test_pause_item_success(
    mock_sab_class, mock_ts_class, make_update, make_context
):
    """dl_pause_<nzo_id> pauses item and refreshes."""
    handler, mock_sab, _ = _make_handler_with_mocks(
        mock_sab_class, mock_ts_class
    )

    update = make_update(callback_data="dl_pause_nzo_abc")
    context = make_context(user_data={"dl_tab": "queue"})

    await handler.handle_downloads_pause_item(update, context)

    update.callback_query.answer.assert_called_once()
    mock_sab.pause_item.assert_awaited_once_with("nzo_abc")


@pytest.mark.asyncio
@patch("src.bot.handlers.sabnzbd.TranslationService")
@patch("src.bot.handlers.sabnzbd.SABnzbdService")
async def test_pause_item_failure(
    mock_sab_class, mock_ts_class, make_update, make_context
):
    """dl_pause_<nzo_id> shows error on failure."""
    handler, mock_sab, _ = _make_handler_with_mocks(
        mock_sab_class, mock_ts_class
    )
    mock_sab.pause_item = AsyncMock(return_value=False)

    update = make_update(callback_data="dl_pause_nzo_abc")
    context = make_context(user_data={"dl_tab": "queue"})

    await handler.handle_downloads_pause_item(update, context)

    answer_call = update.callback_query.answer.call_args
    assert answer_call[1].get("show_alert") is True


@pytest.mark.asyncio
@patch("src.bot.handlers.sabnzbd.TranslationService")
@patch("src.bot.handlers.sabnzbd.SABnzbdService")
async def test_resume_item_success(
    mock_sab_class, mock_ts_class, make_update, make_context
):
    """dl_resume_<nzo_id> resumes item and refreshes."""
    handler, mock_sab, _ = _make_handler_with_mocks(
        mock_sab_class, mock_ts_class
    )

    update = make_update(callback_data="dl_resume_nzo_ghi")
    context = make_context(user_data={"dl_tab": "queue"})

    await handler.handle_downloads_resume_item(update, context)

    update.callback_query.answer.assert_called_once()
    mock_sab.resume_item.assert_awaited_once_with("nzo_ghi")


# ---------------------------------------------------------------------------
# handle_downloads_pauseall / resumeall
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.sabnzbd.TranslationService")
@patch("src.bot.handlers.sabnzbd.SABnzbdService")
async def test_pause_all(
    mock_sab_class, mock_ts_class, make_update, make_context
):
    """dl_pauseall pauses entire queue and refreshes."""
    handler, mock_sab, _ = _make_handler_with_mocks(
        mock_sab_class, mock_ts_class
    )

    update = make_update(callback_data="dl_pauseall")
    context = make_context(user_data={"dl_tab": "queue"})

    await handler.handle_downloads_pauseall(update, context)

    update.callback_query.answer.assert_called_once()
    mock_sab.pause_queue.assert_awaited_once()


@pytest.mark.asyncio
@patch("src.bot.handlers.sabnzbd.TranslationService")
@patch("src.bot.handlers.sabnzbd.SABnzbdService")
async def test_resume_all(
    mock_sab_class, mock_ts_class, make_update, make_context
):
    """dl_resumeall resumes entire queue and refreshes."""
    handler, mock_sab, _ = _make_handler_with_mocks(
        mock_sab_class, mock_ts_class
    )

    update = make_update(callback_data="dl_resumeall")
    context = make_context(user_data={"dl_tab": "queue"})

    await handler.handle_downloads_resumeall(update, context)

    update.callback_query.answer.assert_called_once()
    mock_sab.resume_queue.assert_awaited_once()


# ---------------------------------------------------------------------------
# handle_downloads_refresh
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.sabnzbd.TranslationService")
@patch("src.bot.handlers.sabnzbd.SABnzbdService")
async def test_refresh_queue(
    mock_sab_class, mock_ts_class, make_update, make_context
):
    """dl_refresh re-fetches and edits message."""
    handler, mock_sab, _ = _make_handler_with_mocks(
        mock_sab_class, mock_ts_class
    )

    update = make_update(callback_data="dl_refresh")
    context = make_context(user_data={"dl_tab": "queue"})

    await handler.handle_downloads_refresh(update, context)

    update.callback_query.answer.assert_called_once()
    update.callback_query.message.edit_text.assert_called_once()
    mock_sab.get_queue_details.assert_awaited_once()


@pytest.mark.asyncio
@patch("src.bot.handlers.sabnzbd.TranslationService")
@patch("src.bot.handlers.sabnzbd.SABnzbdService")
async def test_refresh_history(
    mock_sab_class, mock_ts_class, make_update, make_context
):
    """dl_refresh on history tab re-fetches history."""
    handler, mock_sab, _ = _make_handler_with_mocks(
        mock_sab_class, mock_ts_class
    )

    update = make_update(callback_data="dl_refresh")
    context = make_context(user_data={"dl_tab": "history"})

    await handler.handle_downloads_refresh(update, context)

    update.callback_query.answer.assert_called_once()
    mock_sab.get_history.assert_awaited_once()


# ---------------------------------------------------------------------------
# command registration
# ---------------------------------------------------------------------------


@patch("src.bot.commands.TranslationService")
@patch("src.bot.commands.config")
def test_downloads_command_registered_when_sabnzbd_enabled(
    mock_config, mock_ts_class
):
    """build_authenticated_commands includes /downloads when sabnzbd enabled."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    mock_config.get = MagicMock(side_effect=lambda key, default=None: {
        "radarr": {"enable": False},
        "sonarr": {"enable": False},
        "lidarr": {"enable": False},
        "transmission": {"enable": False},
        "sabnzbd": {"enable": True},
    }.get(key, default if default is not None else {}))

    from src.bot.commands import build_authenticated_commands
    commands = build_authenticated_commands()
    command_names = [c.command for c in commands]

    assert "downloads" in command_names
    assert "sabnzbd" in command_names


@patch("src.bot.commands.TranslationService")
@patch("src.bot.commands.config")
def test_downloads_command_not_registered_when_sabnzbd_disabled(
    mock_config, mock_ts_class
):
    """build_authenticated_commands excludes /downloads when sabnzbd disabled."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    mock_config.get = MagicMock(side_effect=lambda key, default=None: {
        "radarr": {"enable": False},
        "sonarr": {"enable": False},
        "lidarr": {"enable": False},
        "transmission": {"enable": False},
        "sabnzbd": {"enable": False},
    }.get(key, default if default is not None else {}))

    from src.bot.commands import build_authenticated_commands
    commands = build_authenticated_commands()
    command_names = [c.command for c in commands]

    assert "downloads" not in command_names


# ---------------------------------------------------------------------------
# Edge cases for coverage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.bot.handlers.sabnzbd.TranslationService")
@patch("src.bot.handlers.sabnzbd.SABnzbdService")
async def test_pagination_history_tab(
    mock_sab_class, mock_ts_class, make_update, make_context
):
    """dl_page_0 on history tab fetches history."""
    handler, mock_sab, _ = _make_handler_with_mocks(
        mock_sab_class, mock_ts_class
    )

    update = make_update(callback_data="dl_page_0")
    context = make_context(user_data={"dl_tab": "history"})

    await handler.handle_downloads_page(update, context)

    update.callback_query.answer.assert_called_once()
    mock_sab.get_history.assert_awaited_once()


@pytest.mark.asyncio
@patch("src.bot.handlers.sabnzbd.TranslationService")
@patch("src.bot.handlers.sabnzbd.SABnzbdService")
async def test_pause_item_refreshes_history_tab(
    mock_sab_class, mock_ts_class, make_update, make_context
):
    """Per-item pause on history tab refreshes with history view."""
    handler, mock_sab, _ = _make_handler_with_mocks(
        mock_sab_class, mock_ts_class
    )

    update = make_update(callback_data="dl_pause_nzo_abc")
    context = make_context(user_data={"dl_tab": "history"})

    await handler.handle_downloads_pause_item(update, context)

    mock_sab.get_history.assert_awaited_once()


@pytest.mark.asyncio
@patch("src.bot.handlers.sabnzbd.TranslationService")
@patch("src.bot.handlers.sabnzbd.SABnzbdService")
async def test_downloads_empty_queue(
    mock_sab_class, mock_ts_class, make_update, make_context
):
    """Empty queue shows DownloadsEmpty text."""
    from src.bot.handlers.auth import AuthHandler
    AuthHandler._authenticated_users = {12345}

    handler, mock_sab, _ = _make_handler_with_mocks(
        mock_sab_class, mock_ts_class
    )
    mock_sab.get_queue_details = AsyncMock(return_value={
        'paused': False,
        'speed': '0 KB/s',
        'size_remaining': '0 MB',
        'items_count': 0,
        'items': [],
    })

    update = make_update(text="/downloads")
    context = make_context()

    await handler.handle_downloads(update, context)

    text_arg = update.message.reply_text.call_args[0][0]
    assert "DownloadsEmpty" in text_arg


@pytest.mark.asyncio
@patch("src.bot.handlers.sabnzbd.TranslationService")
@patch("src.bot.handlers.sabnzbd.SABnzbdService")
async def test_downloads_paused_queue_text(
    mock_sab_class, mock_ts_class, make_update, make_context
):
    """Paused queue shows DownloadsPaused in text."""
    from src.bot.handlers.auth import AuthHandler
    AuthHandler._authenticated_users = {12345}

    handler, mock_sab, _ = _make_handler_with_mocks(
        mock_sab_class, mock_ts_class
    )
    mock_sab.get_queue_details = AsyncMock(return_value={
        'paused': True,
        'speed': '0 KB/s',
        'size_remaining': '1.2 GB',
        'items_count': 1,
        'items': [{
            'nzo_id': 'nzo_abc',
            'title': 'Test',
            'status': 'Paused',
            'progress': 50,
            'size': '1 GB',
            'timeleft': '',
        }],
    })

    update = make_update(text="/downloads")
    context = make_context()

    await handler.handle_downloads(update, context)

    text_arg = update.message.reply_text.call_args[0][0]
    assert "DownloadsPaused" in text_arg


@pytest.mark.asyncio
@patch("src.bot.handlers.sabnzbd.TranslationService")
@patch("src.bot.handlers.sabnzbd.SABnzbdService")
async def test_tab_switch_to_empty_history(
    mock_sab_class, mock_ts_class, make_update, make_context
):
    """Switching to history with no items shows DownloadsHistoryEmpty."""
    handler, mock_sab, _ = _make_handler_with_mocks(
        mock_sab_class, mock_ts_class
    )
    mock_sab.get_history = AsyncMock(return_value={
        'total': 0,
        'items': [],
    })

    update = make_update(callback_data="dl_tab_history")
    context = make_context()

    await handler.handle_downloads_tab(update, context)

    text_arg = update.callback_query.message.edit_text.call_args[0][0]
    assert "DownloadsHistoryEmpty" in text_arg


@pytest.mark.asyncio
@patch("src.bot.handlers.sabnzbd.TranslationService")
@patch("src.bot.handlers.sabnzbd.SABnzbdService")
async def test_history_item_no_download_time(
    mock_sab_class, mock_ts_class, make_update, make_context
):
    """History item with download_time=0 shows no time string."""
    handler, mock_sab, _ = _make_handler_with_mocks(
        mock_sab_class, mock_ts_class
    )
    mock_sab.get_history = AsyncMock(return_value={
        'total': 1,
        'items': [{
            'name': 'Failed.Download',
            'status': 'Failed',
            'size': '0 B',
            'download_time': 0,
        }],
    })

    update = make_update(callback_data="dl_tab_history")
    context = make_context()

    await handler.handle_downloads_tab(update, context)

    text_arg = update.callback_query.message.edit_text.call_args[0][0]
    assert "Failed.Download" in text_arg


@pytest.mark.asyncio
@patch("src.bot.handlers.sabnzbd.TranslationService")
@patch("src.bot.handlers.sabnzbd.SABnzbdService")
async def test_resume_item_failure(
    mock_sab_class, mock_ts_class, make_update, make_context
):
    """dl_resume_<nzo_id> shows error on failure."""
    handler, mock_sab, _ = _make_handler_with_mocks(
        mock_sab_class, mock_ts_class
    )
    mock_sab.resume_item = AsyncMock(return_value=False)

    update = make_update(callback_data="dl_resume_nzo_abc")
    context = make_context(user_data={"dl_tab": "queue"})

    await handler.handle_downloads_resume_item(update, context)

    answer_call = update.callback_query.answer.call_args
    assert answer_call[1].get("show_alert") is True


@pytest.mark.asyncio
@patch("src.bot.handlers.sabnzbd.TranslationService")
@patch("src.bot.handlers.sabnzbd.SABnzbdService")
async def test_noop_handler_answers_query(
    mock_sab_class, mock_ts_class, make_update, make_context
):
    """dl_noop handler dismisses loading spinner without side effects."""
    handler, _, _ = _make_handler_with_mocks(
        mock_sab_class, mock_ts_class
    )

    update = make_update(callback_data="dl_noop")
    context = make_context()

    await handler.handle_downloads_noop(update, context)

    update.callback_query.answer.assert_called_once()
