"""
Integration tests for the authentication conversation flow.

Tests the full /auth -> password -> authenticated/rejected cycle.
"""

import pytest
from unittest.mock import patch

from src.bot.handlers.auth import AuthHandler


@pytest.mark.asyncio
async def test_auth_correct_password(harness):
    """Unauthenticated user sends /auth, types correct password, becomes authenticated."""
    # Remove pre-seeded auth
    AuthHandler._authenticated_users.discard(12345)

    with patch.object(AuthHandler, "_save_authenticated_users"):
        resp = await harness.send_command("/auth")
        assert resp is not None
        # Should ask for password ("Authorize" translation key)
        assert resp.text

        # Type correct password
        await harness.send_text("test-pass")
        # check_password deletes the message, then sends success
        assert len(harness.responses) >= 1
        # User should now be authenticated
        assert AuthHandler.is_authenticated(12345)


@pytest.mark.asyncio
async def test_auth_wrong_password(harness):
    """Unauthenticated user sends wrong password, stays unauthenticated."""
    AuthHandler._authenticated_users.discard(12345)

    with patch.object(AuthHandler, "_save_authenticated_users"):
        await harness.send_command("/auth")
        await harness.send_text("wrong-password")
        assert len(harness.responses) >= 1
        # User should NOT be authenticated
        assert not AuthHandler.is_authenticated(12345)


@pytest.mark.asyncio
async def test_auth_then_movie(harness):
    """Authenticate first, then /movie should enter SEARCHING state."""
    AuthHandler._authenticated_users.discard(12345)

    with patch.object(AuthHandler, "_save_authenticated_users"):
        await harness.send_command("/auth")
        await harness.send_text("test-pass")
        assert AuthHandler.is_authenticated(12345)

    # Now send /movie — should proceed since authenticated
    resp = await harness.send_command("/movie")
    assert resp is not None
    assert "Title" in resp.text
    state = harness.get_conversation_state("media_conversation", 12345, 12345)
    assert state == 1  # SEARCHING
