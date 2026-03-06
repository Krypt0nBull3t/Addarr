"""
Tests for auth pre-seeding and conversation state inspection.

Validates that:
1. Unauthenticated users are blocked from protected commands
2. Authenticated users proceed into conversation flows
3. Conversation state is inspectable via BotHarness
"""

import pytest

from src.bot.handlers.auth import AuthHandler


@pytest.mark.asyncio
async def test_unauthenticated_user_blocked(harness):
    """Unauthenticated user sending /movie gets auth-required message."""
    # Remove the default pre-seeded user
    AuthHandler._authenticated_users.discard(12345)

    resp = await harness.send_command("/movie")
    assert resp is not None
    assert "authenticate" in resp.text.lower() or "auth" in resp.text.lower()


@pytest.mark.asyncio
async def test_authenticated_user_proceeds(harness):
    """Authenticated user sending /movie gets the search prompt."""
    # User 12345 is pre-seeded by the harness fixture
    resp = await harness.send_command("/movie")
    assert resp is not None
    # TranslationService mock returns the key, so we expect "Title"
    assert "Title" in resp.text


@pytest.mark.asyncio
async def test_conversation_state_after_command(harness):
    """After /movie, harness reports conversation is in SEARCHING state."""
    await harness.send_command("/movie")
    state = harness.get_conversation_state("media_conversation", 12345, 12345)
    # SEARCHING = 1 (from dispatch.py)
    assert state == 1
