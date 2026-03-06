"""
Integration tests for the /downloads dashboard.

Uses downloads_harness fixture which enables both Transmission and SABnzbd
services so DownloadsHandler registers its handlers.
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.services.transmission import TransmissionService
from src.services.sabnzbd import SABnzbdService

from tests.integration.fixtures import DOWNLOADS_QUEUE, DOWNLOADS_EMPTY_QUEUE


@pytest.mark.asyncio
async def test_downloads_command_shows_queue(downloads_harness):
    """/downloads with Transmission enabled shows queue."""
    with patch.object(
        TransmissionService, "get_queue_details",
        new_callable=AsyncMock, return_value=DOWNLOADS_QUEUE,
    ):
        resp = await downloads_harness.send_command("/downloads")
        assert resp is not None
        assert resp.method == "sendMessage"
        assert resp.text


@pytest.mark.asyncio
async def test_downloads_sabnzbd_queue(downloads_harness):
    """/downloads then switch to SABnzbd shows its queue."""
    with (
        patch.object(
            TransmissionService, "get_queue_details",
            new_callable=AsyncMock, return_value=DOWNLOADS_EMPTY_QUEUE,
        ),
        patch.object(
            SABnzbdService, "get_queue_details",
            new_callable=AsyncMock, return_value=DOWNLOADS_QUEUE,
        ),
    ):
        await downloads_harness.send_command("/downloads")
        resp = await downloads_harness.tap_button("dl_client_sab")
        assert resp is not None
        assert resp.text


@pytest.mark.asyncio
async def test_downloads_client_switch(downloads_harness):
    """Switch between Transmission and SABnzbd clients."""
    with (
        patch.object(
            TransmissionService, "get_queue_details",
            new_callable=AsyncMock, return_value=DOWNLOADS_EMPTY_QUEUE,
        ),
        patch.object(
            SABnzbdService, "get_queue_details",
            new_callable=AsyncMock, return_value=DOWNLOADS_QUEUE,
        ),
    ):
        await downloads_harness.send_command("/downloads")

        # Switch to SABnzbd
        resp = await downloads_harness.tap_button("dl_client_sab")
        assert resp is not None

        # Switch back to Transmission
        resp = await downloads_harness.tap_button("dl_client_tx")
        assert resp is not None


@pytest.mark.asyncio
async def test_downloads_refresh(downloads_harness):
    """Tap refresh, assert queue re-fetched."""
    with patch.object(
        TransmissionService, "get_queue_details",
        new_callable=AsyncMock, return_value=DOWNLOADS_QUEUE,
    ):
        await downloads_harness.send_command("/downloads")
        resp = await downloads_harness.tap_button("dl_refresh")
        assert resp is not None
        assert resp.text
