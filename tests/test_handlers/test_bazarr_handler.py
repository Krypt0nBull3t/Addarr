"""
Tests for src/bot/handlers/bazarr.py - BazarrHandler.

BazarrHandler uses BazarrService singleton with is_enabled() gating.
Service methods (search, get_wanted_movies, etc.) are async.
Tests patch at the handler's import site.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from telegram.ext import ConversationHandler

from src.bot.handlers.auth import AuthHandler


# ---------------------------------------------------------------------------
# subtitles_menu
# ---------------------------------------------------------------------------


class TestSubtitlesMenu:
    @pytest.mark.asyncio
    @patch("src.bot.handlers.bazarr.TranslationService")
    @patch("src.bot.handlers.bazarr.BazarrService")
    async def test_not_enabled_via_command(
        self, mock_svc_class, mock_ts_class, make_update, make_context
    ):
        """When bazarr is disabled, reply with not-enabled message."""
        mock_svc = MagicMock()
        mock_svc.is_enabled.return_value = False
        mock_svc_class.return_value = mock_svc
        mock_ts = MagicMock()
        mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
        mock_ts_class.return_value = mock_ts

        from src.bot.handlers.bazarr import BazarrHandler

        handler = BazarrHandler()
        update = make_update(text="/subtitles")
        context = make_context()
        AuthHandler._authenticated_users = {12345}

        await handler.subtitles_menu(update, context)

        update.message.reply_text.assert_called_once()
        call_text = update.message.reply_text.call_args[0][0]
        assert "BazarrNotEnabled" in call_text

    @pytest.mark.asyncio
    @patch("src.bot.handlers.bazarr.TranslationService")
    @patch("src.bot.handlers.bazarr.BazarrService")
    async def test_not_enabled_via_callback(
        self, mock_svc_class, mock_ts_class, make_update, make_context
    ):
        """When bazarr is disabled via callback, edit message with error."""
        mock_svc = MagicMock()
        mock_svc.is_enabled.return_value = False
        mock_svc_class.return_value = mock_svc
        mock_ts = MagicMock()
        mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
        mock_ts_class.return_value = mock_ts

        from src.bot.handlers.bazarr import BazarrHandler

        handler = BazarrHandler()
        update = make_update(callback_data="bazarr_menu")
        context = make_context()
        AuthHandler._authenticated_users = {12345}

        await handler.subtitles_menu(update, context)

        update.callback_query.answer.assert_called_once()
        call_text = update.callback_query.edit_message_text.call_args[0][0]
        assert "BazarrNotEnabled" in call_text

    @pytest.mark.asyncio
    @patch("src.bot.handlers.bazarr.TranslationService")
    @patch("src.bot.handlers.bazarr.BazarrService")
    async def test_enabled_shows_keyboard_via_command(
        self, mock_svc_class, mock_ts_class, make_update, make_context
    ):
        """When bazarr is enabled, show menu keyboard."""
        mock_svc = MagicMock()
        mock_svc.is_enabled.return_value = True
        mock_svc_class.return_value = mock_svc
        mock_ts = MagicMock()
        mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
        mock_ts_class.return_value = mock_ts

        from src.bot.handlers.bazarr import BazarrHandler

        handler = BazarrHandler()
        update = make_update(text="/subtitles")
        context = make_context()
        AuthHandler._authenticated_users = {12345}

        await handler.subtitles_menu(update, context)

        update.message.reply_text.assert_called_once()
        call_kwargs = update.message.reply_text.call_args
        assert call_kwargs.kwargs.get("reply_markup") is not None

    @pytest.mark.asyncio
    @patch("src.bot.handlers.bazarr.TranslationService")
    @patch("src.bot.handlers.bazarr.BazarrService")
    async def test_enabled_shows_keyboard_via_callback(
        self, mock_svc_class, mock_ts_class, make_update, make_context
    ):
        """When invoked via callback, edit_message_text is used."""
        mock_svc = MagicMock()
        mock_svc.is_enabled.return_value = True
        mock_svc_class.return_value = mock_svc
        mock_ts = MagicMock()
        mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
        mock_ts_class.return_value = mock_ts

        from src.bot.handlers.bazarr import BazarrHandler

        handler = BazarrHandler()
        update = make_update(callback_data="bazarr_menu")
        context = make_context()
        AuthHandler._authenticated_users = {12345}

        await handler.subtitles_menu(update, context)

        update.callback_query.answer.assert_called_once()
        update.callback_query.edit_message_text.assert_called_once()


# ---------------------------------------------------------------------------
# prompt_search
# ---------------------------------------------------------------------------


class TestPromptSearch:
    @pytest.mark.asyncio
    @patch("src.bot.handlers.bazarr.TranslationService")
    @patch("src.bot.handlers.bazarr.BazarrService")
    async def test_prompt_search(
        self, mock_svc_class, mock_ts_class, make_update, make_context
    ):
        """prompt_search sends prompt text and returns BAZARR_SEARCH."""
        mock_svc = MagicMock()
        mock_svc_class.return_value = mock_svc
        mock_ts = MagicMock()
        mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
        mock_ts_class.return_value = mock_ts

        from src.bot.handlers.bazarr import BazarrHandler
        from src.bot.states import States

        handler = BazarrHandler()
        update = make_update(callback_data="bazarr_search")
        context = make_context()

        result = await handler.prompt_search(update, context)

        assert result == States.BAZARR_SEARCH
        update.callback_query.answer.assert_called_once()
        update.callback_query.edit_message_text.assert_called_once()


# ---------------------------------------------------------------------------
# handle_search
# ---------------------------------------------------------------------------


class TestHandleSearch:
    @pytest.mark.asyncio
    @patch("src.bot.handlers.bazarr.TranslationService")
    @patch("src.bot.handlers.bazarr.BazarrService")
    async def test_results_found(
        self, mock_svc_class, mock_ts_class, make_update, make_context
    ):
        """When search returns results, display them."""
        mock_svc = MagicMock()
        mock_svc.search = AsyncMock(return_value=[
            {"title": "Test Movie", "missing_subtitles": [{"name": "English"}]},
            {"title": "Complete Movie", "missing_subtitles": []},
        ])
        mock_svc_class.return_value = mock_svc
        mock_ts = MagicMock()
        mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
        mock_ts_class.return_value = mock_ts

        from src.bot.handlers.bazarr import BazarrHandler

        handler = BazarrHandler()
        update = make_update(text="Test Movie")
        context = make_context()

        result = await handler.handle_search(update, context)

        assert result == ConversationHandler.END
        update.message.reply_text.assert_called_once()
        call_text = update.message.reply_text.call_args[0][0]
        assert "Test Movie" in call_text

    @pytest.mark.asyncio
    @patch("src.bot.handlers.bazarr.TranslationService")
    @patch("src.bot.handlers.bazarr.BazarrService")
    async def test_no_results(
        self, mock_svc_class, mock_ts_class, make_update, make_context
    ):
        """When search returns no results, show no-results message."""
        mock_svc = MagicMock()
        mock_svc.search = AsyncMock(return_value=[])
        mock_svc_class.return_value = mock_svc
        mock_ts = MagicMock()
        mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
        mock_ts_class.return_value = mock_ts

        from src.bot.handlers.bazarr import BazarrHandler

        handler = BazarrHandler()
        update = make_update(text="Nonexistent")
        context = make_context()

        result = await handler.handle_search(update, context)

        assert result == ConversationHandler.END
        update.message.reply_text.assert_called_once()
        call_text = update.message.reply_text.call_args[0][0]
        assert "BazarrNoResults" in call_text

    @pytest.mark.asyncio
    @patch("src.bot.handlers.bazarr.TranslationService")
    @patch("src.bot.handlers.bazarr.BazarrService")
    async def test_empty_text(
        self, mock_svc_class, mock_ts_class, make_update, make_context
    ):
        """When message has no text, return END."""
        mock_svc = MagicMock()
        mock_svc_class.return_value = mock_svc
        mock_ts = MagicMock()
        mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
        mock_ts_class.return_value = mock_ts

        from src.bot.handlers.bazarr import BazarrHandler

        handler = BazarrHandler()
        update = make_update(text=None)
        # Ensure message.text is None
        update.message.text = None
        context = make_context()

        result = await handler.handle_search(update, context)

        assert result == ConversationHandler.END


# ---------------------------------------------------------------------------
# wanted_movies
# ---------------------------------------------------------------------------


class TestWantedMovies:
    @pytest.mark.asyncio
    @patch("src.bot.handlers.bazarr.TranslationService")
    @patch("src.bot.handlers.bazarr.BazarrService")
    async def test_results_found(
        self, mock_svc_class, mock_ts_class, make_update, make_context
    ):
        """When wanted movies exist, display them."""
        mock_svc = MagicMock()
        mock_svc.get_wanted_movies = AsyncMock(return_value=[
            {"title": "Missing Movie", "missing_subtitles": [{"name": "English"}]},
        ])
        mock_svc_class.return_value = mock_svc
        mock_ts = MagicMock()
        mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
        mock_ts_class.return_value = mock_ts

        from src.bot.handlers.bazarr import BazarrHandler

        handler = BazarrHandler()
        update = make_update(callback_data="bazarr_wanted_movies")
        context = make_context()

        await handler.wanted_movies(update, context)

        update.callback_query.answer.assert_called_once()
        update.callback_query.edit_message_text.assert_called_once()
        call_text = update.callback_query.edit_message_text.call_args[0][0]
        assert "Missing Movie" in call_text

    @pytest.mark.asyncio
    @patch("src.bot.handlers.bazarr.TranslationService")
    @patch("src.bot.handlers.bazarr.BazarrService")
    async def test_empty_list(
        self, mock_svc_class, mock_ts_class, make_update, make_context
    ):
        """When no wanted movies, show empty message."""
        mock_svc = MagicMock()
        mock_svc.get_wanted_movies = AsyncMock(return_value=[])
        mock_svc_class.return_value = mock_svc
        mock_ts = MagicMock()
        mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
        mock_ts_class.return_value = mock_ts

        from src.bot.handlers.bazarr import BazarrHandler

        handler = BazarrHandler()
        update = make_update(callback_data="bazarr_wanted_movies")
        context = make_context()

        await handler.wanted_movies(update, context)

        update.callback_query.answer.assert_called_once()
        update.callback_query.edit_message_text.assert_called_once()
        call_text = update.callback_query.edit_message_text.call_args[0][0]
        assert "BazarrWantedEmpty" in call_text


# ---------------------------------------------------------------------------
# wanted_episodes
# ---------------------------------------------------------------------------


class TestWantedEpisodes:
    @pytest.mark.asyncio
    @patch("src.bot.handlers.bazarr.TranslationService")
    @patch("src.bot.handlers.bazarr.BazarrService")
    async def test_results_found(
        self, mock_svc_class, mock_ts_class, make_update, make_context
    ):
        """When wanted episodes exist, display them."""
        mock_svc = MagicMock()
        mock_svc.get_wanted_episodes = AsyncMock(return_value=[
            {
                "seriesTitle": "Test Show",
                "episode_number": "S01E01",
                "episodeTitle": "Pilot",
                "missing_subtitles": [{"name": "English"}],
            },
        ])
        mock_svc_class.return_value = mock_svc
        mock_ts = MagicMock()
        mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
        mock_ts_class.return_value = mock_ts

        from src.bot.handlers.bazarr import BazarrHandler

        handler = BazarrHandler()
        update = make_update(callback_data="bazarr_wanted_episodes")
        context = make_context()

        await handler.wanted_episodes(update, context)

        update.callback_query.answer.assert_called_once()
        update.callback_query.edit_message_text.assert_called_once()
        call_text = update.callback_query.edit_message_text.call_args[0][0]
        assert "Test Show" in call_text

    @pytest.mark.asyncio
    @patch("src.bot.handlers.bazarr.TranslationService")
    @patch("src.bot.handlers.bazarr.BazarrService")
    async def test_empty_list(
        self, mock_svc_class, mock_ts_class, make_update, make_context
    ):
        """When no wanted episodes, show empty message."""
        mock_svc = MagicMock()
        mock_svc.get_wanted_episodes = AsyncMock(return_value=[])
        mock_svc_class.return_value = mock_svc
        mock_ts = MagicMock()
        mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
        mock_ts_class.return_value = mock_ts

        from src.bot.handlers.bazarr import BazarrHandler

        handler = BazarrHandler()
        update = make_update(callback_data="bazarr_wanted_episodes")
        context = make_context()

        await handler.wanted_episodes(update, context)

        update.callback_query.answer.assert_called_once()
        update.callback_query.edit_message_text.assert_called_once()
        call_text = update.callback_query.edit_message_text.call_args[0][0]
        assert "BazarrWantedEmpty" in call_text


# ---------------------------------------------------------------------------
# search_subtitles_trigger
# ---------------------------------------------------------------------------


class TestSearchSubtitlesTrigger:
    @pytest.mark.asyncio
    @patch("src.bot.handlers.bazarr.TranslationService")
    @patch("src.bot.handlers.bazarr.BazarrService")
    async def test_movie_success(
        self, mock_svc_class, mock_ts_class, make_update, make_context
    ):
        """Triggering subtitle search for a movie succeeds."""
        mock_svc = MagicMock()
        mock_svc.search_movie_subtitles = AsyncMock(return_value=True)
        mock_svc_class.return_value = mock_svc
        mock_ts = MagicMock()
        mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
        mock_ts_class.return_value = mock_ts

        from src.bot.handlers.bazarr import BazarrHandler

        handler = BazarrHandler()
        update = make_update(callback_data="bazarr_sub_movie_42_en")
        context = make_context()

        await handler.search_subtitles_trigger(update, context)

        update.callback_query.answer.assert_called_once()
        update.callback_query.edit_message_text.assert_called_once()
        call_text = update.callback_query.edit_message_text.call_args[0][0]
        assert "BazarrSearchTriggered" in call_text

    @pytest.mark.asyncio
    @patch("src.bot.handlers.bazarr.TranslationService")
    @patch("src.bot.handlers.bazarr.BazarrService")
    async def test_episode_success(
        self, mock_svc_class, mock_ts_class, make_update, make_context
    ):
        """Triggering subtitle search for an episode succeeds."""
        mock_svc = MagicMock()
        mock_svc.search_episode_subtitles = AsyncMock(return_value=True)
        mock_svc_class.return_value = mock_svc
        mock_ts = MagicMock()
        mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
        mock_ts_class.return_value = mock_ts

        from src.bot.handlers.bazarr import BazarrHandler

        handler = BazarrHandler()
        update = make_update(callback_data="bazarr_sub_episode_99_en")
        context = make_context()

        await handler.search_subtitles_trigger(update, context)

        update.callback_query.answer.assert_called_once()
        call_text = update.callback_query.edit_message_text.call_args[0][0]
        assert "BazarrSearchTriggered" in call_text
        mock_svc.search_episode_subtitles.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.bot.handlers.bazarr.TranslationService")
    @patch("src.bot.handlers.bazarr.BazarrService")
    async def test_movie_failure(
        self, mock_svc_class, mock_ts_class, make_update, make_context
    ):
        """Triggering subtitle search for a movie fails."""
        mock_svc = MagicMock()
        mock_svc.search_movie_subtitles = AsyncMock(return_value=False)
        mock_svc_class.return_value = mock_svc
        mock_ts = MagicMock()
        mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
        mock_ts_class.return_value = mock_ts

        from src.bot.handlers.bazarr import BazarrHandler

        handler = BazarrHandler()
        update = make_update(callback_data="bazarr_sub_movie_42_en")
        context = make_context()

        await handler.search_subtitles_trigger(update, context)

        update.callback_query.answer.assert_called_once()
        update.callback_query.edit_message_text.assert_called_once()
        call_text = update.callback_query.edit_message_text.call_args[0][0]
        assert "BazarrSearchFailed" in call_text


# ---------------------------------------------------------------------------
# cancel
# ---------------------------------------------------------------------------


class TestCancel:
    @pytest.mark.asyncio
    @patch("src.bot.handlers.bazarr.TranslationService")
    @patch("src.bot.handlers.bazarr.BazarrService")
    async def test_cancel_via_callback(
        self, mock_svc_class, mock_ts_class, make_update, make_context
    ):
        """Cancel via callback query edits message."""
        mock_svc = MagicMock()
        mock_svc_class.return_value = mock_svc
        mock_ts = MagicMock()
        mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
        mock_ts_class.return_value = mock_ts

        from src.bot.handlers.bazarr import BazarrHandler

        handler = BazarrHandler()
        update = make_update(callback_data="bazarr_cancel")
        context = make_context()

        result = await handler.cancel(update, context)

        assert result == ConversationHandler.END
        update.callback_query.answer.assert_called_once()
        update.callback_query.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.bot.handlers.bazarr.TranslationService")
    @patch("src.bot.handlers.bazarr.BazarrService")
    async def test_cancel_via_message(
        self, mock_svc_class, mock_ts_class, make_update, make_context
    ):
        """Cancel via text message replies."""
        mock_svc = MagicMock()
        mock_svc_class.return_value = mock_svc
        mock_ts = MagicMock()
        mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
        mock_ts_class.return_value = mock_ts

        from src.bot.handlers.bazarr import BazarrHandler

        handler = BazarrHandler()
        update = make_update(text="/cancel")
        # No callback_query for message variant
        update.callback_query = None
        context = make_context()

        result = await handler.cancel(update, context)

        assert result == ConversationHandler.END
        update.message.reply_text.assert_called_once()


# ---------------------------------------------------------------------------
# get_handler
# ---------------------------------------------------------------------------


class TestGetHandler:
    @patch("src.bot.handlers.bazarr.TranslationService")
    @patch("src.bot.handlers.bazarr.BazarrService")
    def test_get_handler_returns_list(self, mock_svc_class, mock_ts_class):
        """get_handler returns a list with handlers."""
        mock_svc = MagicMock()
        mock_svc_class.return_value = mock_svc
        mock_ts = MagicMock()
        mock_ts_class.return_value = mock_ts

        from src.bot.handlers.bazarr import BazarrHandler

        handler = BazarrHandler()
        handlers = handler.get_handler()

        assert isinstance(handlers, list)
        assert len(handlers) > 0
