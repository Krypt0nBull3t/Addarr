"""
Tests for src/bot/handlers/downloads.py - DownloadsHandler.

Unified downloads dashboard supporting SABnzbd and Transmission clients.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

QUEUE_DATA = {
    "paused": False,
    "speed": "5.2 MB/s",
    "size_remaining": "1.2 GB",
    "items_count": 2,
    "items": [
        {
            "nzo_id": "nzo_abc",
            "title": "Movie.2024.1080p",
            "status": "Downloading",
            "progress": 72,
            "size": "4.2 GB",
            "timeleft": "0:15:30",
        },
        {
            "nzo_id": "nzo_def",
            "title": "TV.Show.S03E05",
            "status": "Queued",
            "progress": 0,
            "size": "1.1 GB",
            "timeleft": "0:45:00",
        },
    ],
}

HISTORY_DATA = {
    "total": 1,
    "items": [
        {
            "name": "Completed.Movie",
            "status": "Completed",
            "size": "4.2 GB",
            "download_time": 8100,
        },
    ],
}

TX_QUEUE_DATA = {
    "paused": False,
    "speed": "1.0 MB/s",
    "size_remaining": "2.0 GB",
    "items_count": 1,
    "items": [
        {
            "nzo_id": 1,
            "title": "Ubuntu.ISO",
            "status": "Downloading",
            "progress": 50,
            "size": "4.00 GB",
            "timeleft": "1h 0m",
        },
    ],
}


def _make_mock_sab(enabled=True):
    mock = MagicMock()
    mock.is_enabled.return_value = enabled
    mock.get_queue_details = AsyncMock(return_value=QUEUE_DATA)
    mock.get_history = AsyncMock(return_value=HISTORY_DATA)
    mock.pause_item = AsyncMock(return_value=True)
    mock.resume_item = AsyncMock(return_value=True)
    mock.pause_queue = AsyncMock(return_value=True)
    mock.resume_queue = AsyncMock(return_value=True)
    return mock


def _make_mock_tx(enabled=True):
    mock = MagicMock()
    mock.is_enabled.return_value = enabled
    mock.get_queue_details = AsyncMock(return_value=TX_QUEUE_DATA)
    mock.pause_item = AsyncMock(return_value=True)
    mock.resume_item = AsyncMock(return_value=True)
    mock.pause_queue = AsyncMock(return_value=True)
    mock.resume_queue = AsyncMock(return_value=True)
    return mock


def _make_handler(mock_sab_class, mock_ts_class, mock_tx_class,
                  sab_enabled=True, tx_enabled=True):
    """Create DownloadsHandler with configured mocks."""
    mock_sab = _make_mock_sab(sab_enabled)
    mock_sab_class.return_value = mock_sab

    mock_tx = _make_mock_tx(tx_enabled)
    mock_tx_class.return_value = mock_tx

    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.bot.handlers.downloads import DownloadsHandler
    handler = DownloadsHandler()
    return handler, mock_sab, mock_tx, mock_ts


PATCH_SAB = "src.bot.handlers.downloads.SABnzbdService"
PATCH_TX = "src.bot.handlers.downloads.TransmissionService"
PATCH_TS = "src.bot.handlers.downloads.TranslationService"


# ---------------------------------------------------------------------------
# /downloads with SABnzbd only
# ---------------------------------------------------------------------------


class TestDownloadsSabnzbdOnly:
    @pytest.mark.asyncio
    @patch(PATCH_TS)
    @patch(PATCH_TX)
    @patch(PATCH_SAB)
    async def test_shows_queue(
        self, mock_sab_class, mock_tx_class, mock_ts_class,
        make_update, make_context
    ):
        """SABnzbd-only mode shows queue with no client tabs."""
        from src.bot.handlers.auth import AuthHandler
        AuthHandler._authenticated_users = {12345}

        handler, mock_sab, _, _ = _make_handler(
            mock_sab_class, mock_ts_class, mock_tx_class,
            sab_enabled=True, tx_enabled=False,
        )

        update = make_update(text="/downloads")
        context = make_context()

        await handler.handle_downloads(update, context)

        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        assert call_args[1].get("reply_markup") is not None
        mock_sab.get_queue_details.assert_awaited_once()

    @pytest.mark.asyncio
    @patch(PATCH_TS)
    @patch(PATCH_TX)
    @patch(PATCH_SAB)
    async def test_history_tab_available(
        self, mock_sab_class, mock_tx_class, mock_ts_class,
        make_update, make_context
    ):
        """SABnzbd-only: history tab works."""
        handler, mock_sab, _, _ = _make_handler(
            mock_sab_class, mock_ts_class, mock_tx_class,
            sab_enabled=True, tx_enabled=False,
        )

        update = make_update(callback_data="dl_tab_history")
        context = make_context(user_data={"dl_client": "sabnzbd"})

        await handler.handle_downloads_tab(update, context)

        mock_sab.get_history.assert_awaited_once()


# ---------------------------------------------------------------------------
# /downloads with Transmission only
# ---------------------------------------------------------------------------


class TestDownloadsTransmissionOnly:
    @pytest.mark.asyncio
    @patch(PATCH_TS)
    @patch(PATCH_TX)
    @patch(PATCH_SAB)
    async def test_shows_queue(
        self, mock_sab_class, mock_tx_class, mock_ts_class,
        make_update, make_context
    ):
        """Transmission-only mode shows queue."""
        from src.bot.handlers.auth import AuthHandler
        AuthHandler._authenticated_users = {12345}

        handler, _, mock_tx, _ = _make_handler(
            mock_sab_class, mock_ts_class, mock_tx_class,
            sab_enabled=False, tx_enabled=True,
        )

        update = make_update(text="/downloads")
        context = make_context()

        await handler.handle_downloads(update, context)

        update.message.reply_text.assert_called_once()
        mock_tx.get_queue_details.assert_awaited_once()

    @pytest.mark.asyncio
    @patch(PATCH_TS)
    @patch(PATCH_TX)
    @patch(PATCH_SAB)
    async def test_no_history_tab(
        self, mock_sab_class, mock_tx_class, mock_ts_class,
        make_update, make_context
    ):
        """Transmission-only: no history tab in keyboard."""
        from src.bot.handlers.auth import AuthHandler
        AuthHandler._authenticated_users = {12345}

        handler, _, mock_tx, _ = _make_handler(
            mock_sab_class, mock_ts_class, mock_tx_class,
            sab_enabled=False, tx_enabled=True,
        )

        update = make_update(text="/downloads")
        context = make_context()

        await handler.handle_downloads(update, context)

        keyboard = update.message.reply_text.call_args[1]["reply_markup"]
        callbacks = [
            btn.callback_data
            for row in keyboard.inline_keyboard for btn in row
        ]
        assert "dl_tab_history" not in callbacks


# ---------------------------------------------------------------------------
# /downloads with both clients
# ---------------------------------------------------------------------------


class TestDownloadsBothClients:
    @pytest.mark.asyncio
    @patch(PATCH_TS)
    @patch(PATCH_TX)
    @patch(PATCH_SAB)
    async def test_shows_client_tabs(
        self, mock_sab_class, mock_tx_class, mock_ts_class,
        make_update, make_context
    ):
        """Both clients: keyboard shows client tabs."""
        from src.bot.handlers.auth import AuthHandler
        AuthHandler._authenticated_users = {12345}

        handler, _, _, _ = _make_handler(
            mock_sab_class, mock_ts_class, mock_tx_class,
            sab_enabled=True, tx_enabled=True,
        )

        update = make_update(text="/downloads")
        context = make_context()

        await handler.handle_downloads(update, context)

        keyboard = update.message.reply_text.call_args[1]["reply_markup"]
        callbacks = [
            btn.callback_data
            for row in keyboard.inline_keyboard for btn in row
        ]
        assert "dl_client_sab" in callbacks
        assert "dl_client_tx" in callbacks

    @pytest.mark.asyncio
    @patch(PATCH_TS)
    @patch(PATCH_TX)
    @patch(PATCH_SAB)
    async def test_client_switch_to_transmission(
        self, mock_sab_class, mock_tx_class, mock_ts_class,
        make_update, make_context
    ):
        """dl_client_tx switches to Transmission and refreshes."""
        handler, _, mock_tx, _ = _make_handler(
            mock_sab_class, mock_ts_class, mock_tx_class,
            sab_enabled=True, tx_enabled=True,
        )

        update = make_update(callback_data="dl_client_tx")
        context = make_context(user_data={"dl_client": "sabnzbd", "dl_tab": "queue"})

        await handler.handle_client_switch(update, context)

        assert context.user_data["dl_client"] == "transmission"
        assert context.user_data["dl_page"] == 0
        mock_tx.get_queue_details.assert_awaited_once()

    @pytest.mark.asyncio
    @patch(PATCH_TS)
    @patch(PATCH_TX)
    @patch(PATCH_SAB)
    async def test_client_switch_to_sabnzbd(
        self, mock_sab_class, mock_tx_class, mock_ts_class,
        make_update, make_context
    ):
        """dl_client_sab switches to SABnzbd and refreshes."""
        handler, mock_sab, _, _ = _make_handler(
            mock_sab_class, mock_ts_class, mock_tx_class,
            sab_enabled=True, tx_enabled=True,
        )

        update = make_update(callback_data="dl_client_sab")
        context = make_context(user_data={"dl_client": "transmission", "dl_tab": "queue"})

        await handler.handle_client_switch(update, context)

        assert context.user_data["dl_client"] == "sabnzbd"
        mock_sab.get_queue_details.assert_awaited_once()


# ---------------------------------------------------------------------------
# /downloads with neither client
# ---------------------------------------------------------------------------


class TestDownloadsNeitherClient:
    @pytest.mark.asyncio
    @patch(PATCH_TS)
    @patch(PATCH_TX)
    @patch(PATCH_SAB)
    async def test_shows_not_enabled(
        self, mock_sab_class, mock_tx_class, mock_ts_class,
        make_update, make_context
    ):
        """Neither client: shows DownloadsNotEnabled message."""
        from src.bot.handlers.auth import AuthHandler
        AuthHandler._authenticated_users = {12345}

        handler, _, _, _ = _make_handler(
            mock_sab_class, mock_ts_class, mock_tx_class,
            sab_enabled=False, tx_enabled=False,
        )

        update = make_update(text="/downloads")
        context = make_context()

        await handler.handle_downloads(update, context)

        text_arg = update.message.reply_text.call_args[0][0]
        assert "DownloadsNotEnabled" in text_arg


# ---------------------------------------------------------------------------
# Pause/resume delegating to active client
# ---------------------------------------------------------------------------


class TestDownloadsPauseResume:
    @pytest.mark.asyncio
    @patch(PATCH_TS)
    @patch(PATCH_TX)
    @patch(PATCH_SAB)
    async def test_pause_item_delegates_to_sabnzbd(
        self, mock_sab_class, mock_tx_class, mock_ts_class,
        make_update, make_context
    ):
        handler, mock_sab, _, _ = _make_handler(
            mock_sab_class, mock_ts_class, mock_tx_class
        )

        update = make_update(callback_data="dl_pause_nzo_abc")
        context = make_context(user_data={"dl_client": "sabnzbd", "dl_tab": "queue"})

        await handler.handle_downloads_pause_item(update, context)

        mock_sab.pause_item.assert_awaited_once_with("nzo_abc")

    @pytest.mark.asyncio
    @patch(PATCH_TS)
    @patch(PATCH_TX)
    @patch(PATCH_SAB)
    async def test_pause_item_delegates_to_transmission(
        self, mock_sab_class, mock_tx_class, mock_ts_class,
        make_update, make_context
    ):
        handler, _, mock_tx, _ = _make_handler(
            mock_sab_class, mock_ts_class, mock_tx_class
        )

        update = make_update(callback_data="dl_pause_42")
        context = make_context(user_data={"dl_client": "transmission", "dl_tab": "queue"})

        await handler.handle_downloads_pause_item(update, context)

        mock_tx.pause_item.assert_awaited_once_with(42)

    @pytest.mark.asyncio
    @patch(PATCH_TS)
    @patch(PATCH_TX)
    @patch(PATCH_SAB)
    async def test_resume_item_delegates_to_active_client(
        self, mock_sab_class, mock_tx_class, mock_ts_class,
        make_update, make_context
    ):
        handler, _, mock_tx, _ = _make_handler(
            mock_sab_class, mock_ts_class, mock_tx_class
        )

        update = make_update(callback_data="dl_resume_7")
        context = make_context(user_data={"dl_client": "transmission", "dl_tab": "queue"})

        await handler.handle_downloads_resume_item(update, context)

        mock_tx.resume_item.assert_awaited_once_with(7)

    @pytest.mark.asyncio
    @patch(PATCH_TS)
    @patch(PATCH_TX)
    @patch(PATCH_SAB)
    async def test_pause_all_delegates_to_active_client(
        self, mock_sab_class, mock_tx_class, mock_ts_class,
        make_update, make_context
    ):
        handler, _, mock_tx, _ = _make_handler(
            mock_sab_class, mock_ts_class, mock_tx_class
        )

        update = make_update(callback_data="dl_pauseall")
        context = make_context(user_data={"dl_client": "transmission", "dl_tab": "queue"})

        await handler.handle_downloads_pauseall(update, context)

        mock_tx.pause_queue.assert_awaited_once()

    @pytest.mark.asyncio
    @patch(PATCH_TS)
    @patch(PATCH_TX)
    @patch(PATCH_SAB)
    async def test_resume_all_delegates_to_active_client(
        self, mock_sab_class, mock_tx_class, mock_ts_class,
        make_update, make_context
    ):
        handler, mock_sab, _, _ = _make_handler(
            mock_sab_class, mock_ts_class, mock_tx_class
        )

        update = make_update(callback_data="dl_resumeall")
        context = make_context(user_data={"dl_client": "sabnzbd", "dl_tab": "queue"})

        await handler.handle_downloads_resumeall(update, context)

        mock_sab.resume_queue.assert_awaited_once()

    @pytest.mark.asyncio
    @patch(PATCH_TS)
    @patch(PATCH_TX)
    @patch(PATCH_SAB)
    async def test_pause_item_failure_shows_alert(
        self, mock_sab_class, mock_tx_class, mock_ts_class,
        make_update, make_context
    ):
        handler, mock_sab, _, _ = _make_handler(
            mock_sab_class, mock_ts_class, mock_tx_class
        )
        mock_sab.pause_item = AsyncMock(return_value=False)

        update = make_update(callback_data="dl_pause_nzo_abc")
        context = make_context(user_data={"dl_client": "sabnzbd", "dl_tab": "queue"})

        await handler.handle_downloads_pause_item(update, context)

        answer_call = update.callback_query.answer.call_args
        assert answer_call[1].get("show_alert") is True

    @pytest.mark.asyncio
    @patch(PATCH_TS)
    @patch(PATCH_TX)
    @patch(PATCH_SAB)
    async def test_resume_item_failure_shows_alert(
        self, mock_sab_class, mock_tx_class, mock_ts_class,
        make_update, make_context
    ):
        handler, mock_sab, _, _ = _make_handler(
            mock_sab_class, mock_ts_class, mock_tx_class
        )
        mock_sab.resume_item = AsyncMock(return_value=False)

        update = make_update(callback_data="dl_resume_nzo_abc")
        context = make_context(user_data={"dl_client": "sabnzbd", "dl_tab": "queue"})

        await handler.handle_downloads_resume_item(update, context)

        answer_call = update.callback_query.answer.call_args
        assert answer_call[1].get("show_alert") is True


# ---------------------------------------------------------------------------
# Tab switch, pagination, refresh, noop
# ---------------------------------------------------------------------------


class TestDownloadsNavigation:
    @pytest.mark.asyncio
    @patch(PATCH_TS)
    @patch(PATCH_TX)
    @patch(PATCH_SAB)
    async def test_tab_switch_resets_page(
        self, mock_sab_class, mock_tx_class, mock_ts_class,
        make_update, make_context
    ):
        handler, _, _, _ = _make_handler(
            mock_sab_class, mock_ts_class, mock_tx_class
        )

        update = make_update(callback_data="dl_tab_history")
        context = make_context(user_data={"dl_client": "sabnzbd", "dl_page": 3})

        await handler.handle_downloads_tab(update, context)

        assert context.user_data["dl_page"] == 0

    @pytest.mark.asyncio
    @patch(PATCH_TS)
    @patch(PATCH_TX)
    @patch(PATCH_SAB)
    async def test_pagination_updates_page(
        self, mock_sab_class, mock_tx_class, mock_ts_class,
        make_update, make_context
    ):
        handler, _, _, _ = _make_handler(
            mock_sab_class, mock_ts_class, mock_tx_class
        )

        update = make_update(callback_data="dl_page_2")
        context = make_context(user_data={"dl_client": "sabnzbd", "dl_tab": "queue"})

        await handler.handle_downloads_page(update, context)

        assert context.user_data["dl_page"] == 2

    @pytest.mark.asyncio
    @patch(PATCH_TS)
    @patch(PATCH_TX)
    @patch(PATCH_SAB)
    async def test_refresh_re_fetches(
        self, mock_sab_class, mock_tx_class, mock_ts_class,
        make_update, make_context
    ):
        handler, mock_sab, _, _ = _make_handler(
            mock_sab_class, mock_ts_class, mock_tx_class
        )

        update = make_update(callback_data="dl_refresh")
        context = make_context(user_data={"dl_client": "sabnzbd", "dl_tab": "queue"})

        await handler.handle_downloads_refresh(update, context)

        update.callback_query.answer.assert_called_once()
        mock_sab.get_queue_details.assert_awaited_once()

    @pytest.mark.asyncio
    @patch(PATCH_TS)
    @patch(PATCH_TX)
    @patch(PATCH_SAB)
    async def test_noop_answers_query(
        self, mock_sab_class, mock_tx_class, mock_ts_class,
        make_update, make_context
    ):
        handler, _, _, _ = _make_handler(
            mock_sab_class, mock_ts_class, mock_tx_class
        )

        update = make_update(callback_data="dl_noop")
        context = make_context()

        await handler.handle_downloads_noop(update, context)

        update.callback_query.answer.assert_called_once()

    @pytest.mark.asyncio
    @patch(PATCH_TS)
    @patch(PATCH_TX)
    @patch(PATCH_SAB)
    async def test_no_user_returns_none(
        self, mock_sab_class, mock_tx_class, mock_ts_class,
        make_update, make_context
    ):
        from src.bot.handlers.auth import AuthHandler
        AuthHandler._authenticated_users = {12345}

        handler, _, _, _ = _make_handler(
            mock_sab_class, mock_ts_class, mock_tx_class
        )

        update = make_update(text="/downloads")
        update.effective_user = None
        context = make_context()

        result = await handler.handle_downloads(update, context)
        assert result is None


# ---------------------------------------------------------------------------
# get_handler
# ---------------------------------------------------------------------------


class TestDownloadsGetHandler:
    @patch(PATCH_TS)
    @patch(PATCH_TX)
    @patch(PATCH_SAB)
    def test_returns_list_when_enabled(
        self, mock_sab_class, mock_tx_class, mock_ts_class
    ):
        handler, _, _, _ = _make_handler(
            mock_sab_class, mock_ts_class, mock_tx_class,
            sab_enabled=True, tx_enabled=False,
        )
        handlers = handler.get_handler()
        assert isinstance(handlers, list)
        assert len(handlers) > 0

    @patch(PATCH_TS)
    @patch(PATCH_TX)
    @patch(PATCH_SAB)
    def test_returns_empty_when_neither_enabled(
        self, mock_sab_class, mock_tx_class, mock_ts_class
    ):
        handler, _, _, _ = _make_handler(
            mock_sab_class, mock_ts_class, mock_tx_class,
            sab_enabled=False, tx_enabled=False,
        )
        handlers = handler.get_handler()
        assert isinstance(handlers, list)
        assert len(handlers) == 0


# ---------------------------------------------------------------------------
# Transmission-specific: int ID parsing for pause/resume
# ---------------------------------------------------------------------------


class TestDownloadsTransmissionIdParsing:
    @pytest.mark.asyncio
    @patch(PATCH_TS)
    @patch(PATCH_TX)
    @patch(PATCH_SAB)
    async def test_transmission_pause_uses_int_id(
        self, mock_sab_class, mock_tx_class, mock_ts_class,
        make_update, make_context
    ):
        """Transmission torrent IDs are ints, not strings."""
        handler, _, mock_tx, _ = _make_handler(
            mock_sab_class, mock_ts_class, mock_tx_class
        )

        update = make_update(callback_data="dl_pause_123")
        context = make_context(user_data={"dl_client": "transmission", "dl_tab": "queue"})

        await handler.handle_downloads_pause_item(update, context)

        mock_tx.pause_item.assert_awaited_once_with(123)

    @pytest.mark.asyncio
    @patch(PATCH_TS)
    @patch(PATCH_TX)
    @patch(PATCH_SAB)
    async def test_sabnzbd_pause_uses_string_id(
        self, mock_sab_class, mock_tx_class, mock_ts_class,
        make_update, make_context
    ):
        """SABnzbd nzo_ids are strings."""
        handler, mock_sab, _, _ = _make_handler(
            mock_sab_class, mock_ts_class, mock_tx_class
        )

        update = make_update(callback_data="dl_pause_nzo_abc")
        context = make_context(user_data={"dl_client": "sabnzbd", "dl_tab": "queue"})

        await handler.handle_downloads_pause_item(update, context)

        mock_sab.pause_item.assert_awaited_once_with("nzo_abc")

    @pytest.mark.asyncio
    @patch(PATCH_TS)
    @patch(PATCH_TX)
    @patch(PATCH_SAB)
    async def test_transmission_invalid_id_falls_back_to_string(
        self, mock_sab_class, mock_tx_class, mock_ts_class,
        make_update, make_context
    ):
        """Non-numeric ID for Transmission falls back to string."""
        handler, _, mock_tx, _ = _make_handler(
            mock_sab_class, mock_ts_class, mock_tx_class
        )

        update = make_update(callback_data="dl_pause_not_a_number")
        context = make_context(user_data={"dl_client": "transmission", "dl_tab": "queue"})

        await handler.handle_downloads_pause_item(update, context)

        mock_tx.pause_item.assert_awaited_once_with("not_a_number")


# ---------------------------------------------------------------------------
# Text formatting coverage
# ---------------------------------------------------------------------------


class TestDownloadsTextFormatting:
    @pytest.mark.asyncio
    @patch(PATCH_TS)
    @patch(PATCH_TX)
    @patch(PATCH_SAB)
    async def test_empty_queue_text(
        self, mock_sab_class, mock_tx_class, mock_ts_class,
        make_update, make_context
    ):
        """Empty queue shows DownloadsEmpty."""
        from src.bot.handlers.auth import AuthHandler
        AuthHandler._authenticated_users = {12345}

        handler, mock_sab, _, _ = _make_handler(
            mock_sab_class, mock_ts_class, mock_tx_class,
            sab_enabled=True, tx_enabled=False,
        )
        mock_sab.get_queue_details = AsyncMock(return_value={
            "paused": False, "speed": "0 KB/s",
            "size_remaining": "0 MB", "items_count": 0, "items": [],
        })

        update = make_update(text="/downloads")
        context = make_context()

        await handler.handle_downloads(update, context)

        text_arg = update.message.reply_text.call_args[0][0]
        assert "DownloadsEmpty" in text_arg

    @pytest.mark.asyncio
    @patch(PATCH_TS)
    @patch(PATCH_TX)
    @patch(PATCH_SAB)
    async def test_paused_queue_text(
        self, mock_sab_class, mock_tx_class, mock_ts_class,
        make_update, make_context
    ):
        """Paused queue shows DownloadsPaused."""
        from src.bot.handlers.auth import AuthHandler
        AuthHandler._authenticated_users = {12345}

        handler, mock_sab, _, _ = _make_handler(
            mock_sab_class, mock_ts_class, mock_tx_class,
            sab_enabled=True, tx_enabled=False,
        )
        mock_sab.get_queue_details = AsyncMock(return_value={
            "paused": True, "speed": "0 KB/s",
            "size_remaining": "1 GB", "items_count": 1,
            "items": [{"nzo_id": "x", "title": "T", "status": "Paused",
                       "progress": 50, "size": "1 GB", "timeleft": ""}],
        })

        update = make_update(text="/downloads")
        context = make_context()

        await handler.handle_downloads(update, context)

        text_arg = update.message.reply_text.call_args[0][0]
        assert "DownloadsPaused" in text_arg

    @pytest.mark.asyncio
    @patch(PATCH_TS)
    @patch(PATCH_TX)
    @patch(PATCH_SAB)
    async def test_empty_history_text(
        self, mock_sab_class, mock_tx_class, mock_ts_class,
        make_update, make_context
    ):
        """Empty history shows DownloadsHistoryEmpty."""
        handler, mock_sab, _, _ = _make_handler(
            mock_sab_class, mock_ts_class, mock_tx_class,
            sab_enabled=True, tx_enabled=False,
        )
        mock_sab.get_history = AsyncMock(return_value={
            "total": 0, "items": [],
        })

        update = make_update(callback_data="dl_tab_history")
        context = make_context(user_data={"dl_client": "sabnzbd"})

        await handler.handle_downloads_tab(update, context)

        text_arg = update.callback_query.message.edit_text.call_args[0][0]
        assert "DownloadsHistoryEmpty" in text_arg

    @pytest.mark.asyncio
    @patch(PATCH_TS)
    @patch(PATCH_TX)
    @patch(PATCH_SAB)
    async def test_history_item_no_download_time(
        self, mock_sab_class, mock_tx_class, mock_ts_class,
        make_update, make_context
    ):
        """History item with download_time=0 shows no time."""
        handler, mock_sab, _, _ = _make_handler(
            mock_sab_class, mock_ts_class, mock_tx_class,
            sab_enabled=True, tx_enabled=False,
        )
        mock_sab.get_history = AsyncMock(return_value={
            "total": 1,
            "items": [{"name": "Failed", "status": "Failed",
                       "size": "0 B", "download_time": 0}],
        })

        update = make_update(callback_data="dl_tab_history")
        context = make_context(user_data={"dl_client": "sabnzbd"})

        await handler.handle_downloads_tab(update, context)

        text_arg = update.callback_query.message.edit_text.call_args[0][0]
        assert "Failed" in text_arg
