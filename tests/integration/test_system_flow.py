"""
Integration tests for the SystemHandler flow.

Tests /status command and system_* callbacks through the full handler chain.
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.services.health import health_service


MOCK_STATUS = {
    "running": True,
    "last_check": None,
    "unhealthy_services": [],
}

MOCK_HEALTH_RESULTS = {
    "media_services": [
        {"name": "Radarr", "healthy": True, "status": "OK"},
        {"name": "Sonarr", "healthy": True, "status": "OK"},
    ],
    "download_clients": [],
}

MOCK_DISK_SPACE = [
    {
        "path": "/data",
        "freeSpace": 500000000000,
        "totalSpace": 1000000000000,
    },
]


def _find_response(harness, method):
    """Find the first captured response matching a given API method."""
    for resp in harness.responses:
        if resp.method == method:
            return resp
    return None


@pytest.mark.asyncio
async def test_status_command_shows_status(harness):
    """/status returns sendMessage with system status text."""
    with patch.object(health_service, "get_status", return_value=MOCK_STATUS):
        resp = await harness.send_command("/status")
        assert resp is not None
        assert resp.method == "sendMessage"
        assert "System Status" in resp.text


@pytest.mark.asyncio
async def test_system_refresh_reruns_checks(harness):
    """system_refresh callback edits message with refreshed status."""
    with (
        patch.object(
            health_service, "run_health_checks",
            new_callable=AsyncMock, return_value=MOCK_HEALTH_RESULTS,
        ),
        patch.object(health_service, "get_status", return_value=MOCK_STATUS),
    ):
        await harness.tap_button("system_refresh")
        resp = _find_response(harness, "editMessageText")
        assert resp is not None
        assert "System Status" in resp.text


@pytest.mark.asyncio
async def test_system_details_shows_services(harness):
    """system_details callback edits message with per-service health info."""
    with patch.object(
        health_service, "run_health_checks",
        new_callable=AsyncMock, return_value=MOCK_HEALTH_RESULTS,
    ):
        await harness.tap_button("system_details")
        resp = _find_response(harness, "editMessageText")
        assert resp is not None
        assert "Radarr" in resp.text


@pytest.mark.asyncio
async def test_system_diskspace_shows_drives(harness):
    """system_diskspace callback edits message with disk space info."""
    with patch.object(
        health_service, "get_disk_space",
        new_callable=AsyncMock, return_value=MOCK_DISK_SPACE,
    ):
        await harness.tap_button("system_diskspace")
        resp = _find_response(harness, "editMessageText")
        assert resp is not None
        assert "Disk Space" in resp.text


@pytest.mark.asyncio
async def test_system_back_returns_to_main_menu(harness):
    """system_back callback edits message to main menu."""
    await harness.tap_button("system_back")
    resp = _find_response(harness, "editMessageText")
    assert resp is not None
    assert "Main Menu" in resp.text
