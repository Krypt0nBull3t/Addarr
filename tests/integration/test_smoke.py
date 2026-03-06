"""
Smoke tests for the integration test harness.

These tests validate that BotHarness can:
1. Build a real Application with all handlers
2. Process Update objects through the handler chain
3. Capture bot responses without hitting Telegram's API
"""

import pytest


@pytest.mark.asyncio
async def test_start_command_returns_response(harness):
    """Send /start to a fully wired Application, assert bot responds."""
    resp = await harness.send_command("/start")
    assert resp is not None
    assert resp.method == "sendMessage"
    assert resp.text  # bot should send some text


@pytest.mark.asyncio
async def test_unknown_command_no_crash(harness):
    """Send an unknown command, assert no error raised."""
    # Should not raise — PTB just ignores unmatched commands
    await harness.send_command("/nonexistent")
    # No response expected for unmatched command


@pytest.mark.asyncio
async def test_harness_captures_multiple_responses(harness):
    """Verify harness.responses collects all API calls from a single update."""
    await harness.send_command("/start")
    # /start sends at least one message; responses list should be non-empty
    assert len(harness.responses) >= 1
    # All captured responses should have a method name
    for resp in harness.responses:
        assert resp.method
