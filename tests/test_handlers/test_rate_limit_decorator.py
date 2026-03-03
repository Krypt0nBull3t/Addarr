"""
Tests for the @rate_limit decorator from src/services/rate_limit.py.

Uses the DummyHandler pattern (same as test_auth_handler.py) to test
the decorator in isolation from real handlers.
"""

import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Basic behavior
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.services.rate_limit.TranslationService")
async def test_rate_limit_allows_when_under_limit(
    mock_ts_class, make_update, make_context
):
    """Handler body runs and returns its value when under limit."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.services.rate_limit import rate_limit

    # Enable rate limiting
    with patch("src.services.rate_limit.config") as mock_cfg:
        mock_cfg.get.return_value = {"enable": True, "limits": {}}

        class DummyHandler:
            @rate_limit("search")
            async def guarded(self, update, context):
                return "allowed"

        handler = DummyHandler()
        update = make_update(text="/movie")
        context = make_context()

        result = await handler.guarded(update, context)
        assert result == "allowed"


@pytest.mark.asyncio
@patch("src.services.rate_limit.TranslationService")
async def test_rate_limit_blocks_when_over_limit(
    mock_ts_class, make_update, make_context
):
    """Handler body does NOT run; reply_text called with rate limit message."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.services.rate_limit import rate_limit

    with patch("src.services.rate_limit.config") as mock_cfg:
        mock_cfg.get.return_value = {
            "enable": True,
            "limits": {"search": {"maxRequests": 2, "windowSeconds": 60}},
        }

        class DummyHandler:
            @rate_limit("search")
            async def guarded(self, update, context):
                return "allowed"

        handler = DummyHandler()
        update = make_update(text="/movie")
        context = make_context()

        # Exhaust limit (2 requests)
        await handler.guarded(update, context)
        await handler.guarded(update, context)

        # Third should be blocked
        result = await handler.guarded(update, context)
        assert result is None
        update.effective_message.reply_text.assert_called()


@pytest.mark.asyncio
async def test_rate_limit_noop_when_disabled(make_update, make_context):
    """When is_enabled is False, handler always runs regardless of limits."""
    from src.services.rate_limit import rate_limit

    # Default mock config has rateLimit.enable = False
    class DummyHandler:
        @rate_limit("search")
        async def guarded(self, update, context):
            return "allowed"

    handler = DummyHandler()
    update = make_update(text="/movie")
    context = make_context()

    # Should always pass even with many calls
    for _ in range(20):
        result = await handler.guarded(update, context)
        assert result == "allowed"


@pytest.mark.asyncio
@patch("src.services.rate_limit.TranslationService")
async def test_rate_limit_returns_none_no_user(
    mock_ts_class, make_update, make_context
):
    """When update.effective_user is None, returns None."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.services.rate_limit import rate_limit

    with patch("src.services.rate_limit.config") as mock_cfg:
        mock_cfg.get.return_value = {"enable": True, "limits": {}}

        class DummyHandler:
            @rate_limit("search")
            async def guarded(self, update, context):
                return "allowed"

        handler = DummyHandler()
        update = make_update(text="/movie")
        update.effective_user = None
        context = make_context()

        result = await handler.guarded(update, context)
        assert result is None


# ---------------------------------------------------------------------------
# Retry seconds in blocked response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.services.rate_limit.TranslationService")
async def test_rate_limit_shows_retry_seconds(
    mock_ts_class, make_update, make_context
):
    """Blocked response passes retry_after seconds to translation."""
    mock_ts = MagicMock()
    mock_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_ts_class.return_value = mock_ts

    from src.services.rate_limit import rate_limit

    with patch("src.services.rate_limit.config") as mock_cfg:
        mock_cfg.get.return_value = {
            "enable": True,
            "limits": {"search": {"maxRequests": 1, "windowSeconds": 60}},
        }

        class DummyHandler:
            @rate_limit("search")
            async def guarded(self, update, context):
                return "allowed"

        handler = DummyHandler()
        update = make_update(text="/movie")
        context = make_context()

        # First allowed, second blocked
        await handler.guarded(update, context)
        await handler.guarded(update, context)

        # TranslationService.get_text should have been called with seconds kwarg
        mock_ts.get_text.assert_called()
        call_kwargs = mock_ts.get_text.call_args
        assert "seconds" in call_kwargs.kwargs
        assert call_kwargs.kwargs["seconds"] > 0


# ---------------------------------------------------------------------------
# Stacking with @require_auth
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.services.rate_limit.TranslationService")
@patch("src.bot.handlers.auth.TranslationService")
async def test_stacking_authenticated_and_under_limit(
    mock_auth_ts_class, mock_rl_ts_class, make_update, make_context
):
    """@require_auth + @rate_limit: authenticated + under limit -> runs."""
    mock_auth_ts = MagicMock()
    mock_auth_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_auth_ts_class.return_value = mock_auth_ts

    mock_rl_ts = MagicMock()
    mock_rl_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_rl_ts_class.return_value = mock_rl_ts

    from src.bot.handlers.auth import AuthHandler, require_auth
    from src.services.rate_limit import rate_limit

    AuthHandler._authenticated_users = {12345}

    with patch("src.services.rate_limit.config") as mock_cfg:
        mock_cfg.get.return_value = {"enable": True, "limits": {}}

        class DummyHandler:
            @require_auth
            @rate_limit("search")
            async def guarded(self, update, context):
                return "allowed"

        handler = DummyHandler()
        update = make_update(text="/movie")
        context = make_context()

        result = await handler.guarded(update, context)
        assert result == "allowed"


@pytest.mark.asyncio
@patch("src.services.rate_limit.TranslationService")
@patch("src.bot.handlers.auth.TranslationService")
async def test_stacking_authenticated_but_over_limit(
    mock_auth_ts_class, mock_rl_ts_class, make_update, make_context
):
    """@require_auth + @rate_limit: authenticated + over limit -> rate limit msg."""
    mock_auth_ts = MagicMock()
    mock_auth_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_auth_ts_class.return_value = mock_auth_ts

    mock_rl_ts = MagicMock()
    mock_rl_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_rl_ts_class.return_value = mock_rl_ts

    from src.bot.handlers.auth import AuthHandler, require_auth
    from src.services.rate_limit import rate_limit

    AuthHandler._authenticated_users = {12345}

    with patch("src.services.rate_limit.config") as mock_cfg:
        mock_cfg.get.return_value = {
            "enable": True,
            "limits": {"search": {"maxRequests": 1, "windowSeconds": 60}},
        }

        class DummyHandler:
            @require_auth
            @rate_limit("search")
            async def guarded(self, update, context):
                return "allowed"

        handler = DummyHandler()
        update = make_update(text="/movie")
        context = make_context()

        # First allowed
        result = await handler.guarded(update, context)
        assert result == "allowed"

        # Second blocked by rate limit (not auth)
        result = await handler.guarded(update, context)
        assert result is None
        update.effective_message.reply_text.assert_called()


@pytest.mark.asyncio
@patch("src.services.rate_limit.TranslationService")
@patch("src.bot.handlers.auth.TranslationService")
async def test_stacking_not_authenticated(
    mock_auth_ts_class, mock_rl_ts_class, make_update, make_context
):
    """@require_auth + @rate_limit: not authenticated -> auth message."""
    mock_auth_ts = MagicMock()
    mock_auth_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_auth_ts_class.return_value = mock_auth_ts

    mock_rl_ts = MagicMock()
    mock_rl_ts.get_text = MagicMock(side_effect=lambda key, **kw: key)
    mock_rl_ts_class.return_value = mock_rl_ts

    from src.bot.handlers.auth import AuthHandler, require_auth
    from src.services.rate_limit import rate_limit

    AuthHandler._authenticated_users = set()  # Not authenticated

    with patch("src.services.rate_limit.config") as mock_cfg:
        mock_cfg.get.return_value = {"enable": True, "limits": {}}

        class DummyHandler:
            @require_auth
            @rate_limit("search")
            async def guarded(self, update, context):
                return "allowed"

        handler = DummyHandler()
        update = make_update(text="/movie")
        context = make_context()

        result = await handler.guarded(update, context)
        assert result is None
        # Auth message should be sent (via update.message.reply_text)
        update.message.reply_text.assert_called_once()
