"""
Integration tests for the /downloads dashboard.

Uses downloads_harness fixture which enables both Transmission and SABnzbd
services so DownloadsHandler registers its handlers.
"""

import json

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


@pytest.mark.asyncio
async def test_downloads_error_view_when_clients_fail(downloads_harness):
    """A failed fetch shows an error with Refresh, not the empty message."""
    with (
        patch.object(
            TransmissionService, "get_queue_details",
            new_callable=AsyncMock, return_value=None,
        ),
        patch.object(
            SABnzbdService, "get_queue_details",
            new_callable=AsyncMock, return_value=None,
        ),
    ):
        resp = await downloads_harness.send_command("/downloads")

    assert resp is not None
    assert "No items in the download queue" not in resp.text
    markup = json.loads(resp.reply_markup)
    callbacks = [
        b["callback_data"] for row in markup["inline_keyboard"] for b in row
    ]
    assert "dl_refresh" in callbacks
    assert "dl_client_tx" in callbacks


@pytest.mark.asyncio
async def test_stale_transmission_button_acts_on_transmission(
    downloads_harness,
):
    """A Transmission Pause button works while the open view is SABnzbd."""
    with (
        patch.object(
            TransmissionService, "get_queue_details",
            new_callable=AsyncMock, return_value=DOWNLOADS_EMPTY_QUEUE,
        ),
        patch.object(
            SABnzbdService, "get_queue_details",
            new_callable=AsyncMock, return_value=DOWNLOADS_QUEUE,
        ),
        patch.object(
            TransmissionService, "pause_item",
            new_callable=AsyncMock, return_value=True,
        ) as tx_pause,
        patch.object(
            SABnzbdService, "pause_item",
            new_callable=AsyncMock, return_value=True,
        ) as sab_pause,
    ):
        await downloads_harness.send_command("/downloads")  # SABnzbd view
        await downloads_harness.tap_button("dl_pause_tx_7")

    tx_pause.assert_awaited_once_with(7)
    sab_pause.assert_not_awaited()
