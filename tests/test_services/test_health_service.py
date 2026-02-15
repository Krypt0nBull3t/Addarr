"""
Tests for src/services/health.py -- HealthService singleton.
"""

import asyncio

import aiohttp
import pytest
from aioresponses import aioresponses
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.health import HealthService


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


class TestHealthServiceSingleton:
    def test_singleton(self):
        a = HealthService()
        b = HealthService()
        assert a is b


# ---------------------------------------------------------------------------
# get_status
# ---------------------------------------------------------------------------


class TestGetStatus:
    def test_get_status_initial(self):
        service = HealthService()
        status = service.get_status()

        assert status["running"] is False
        assert status["last_check"] is None
        assert status["unhealthy_services"] == []


# ---------------------------------------------------------------------------
# check_service_health
# ---------------------------------------------------------------------------


class TestCheckServiceHealth:
    @pytest.mark.asyncio
    async def test_check_service_health_success(self):
        service = HealthService()
        url = "http://localhost:7878/"
        api_key = "test-key"

        with aioresponses() as m:
            m.get(
                "http://localhost:7878/api/v3/system/status",
                payload={"version": "4.7.0"},
                status=200,
            )
            healthy, status = await service.check_service_health(
                url, api_key, "radarr"
            )

        assert healthy is True
        assert "Online" in status
        assert "v4.7.0" in status

    @pytest.mark.asyncio
    async def test_check_service_health_connection_error(self):
        service = HealthService()
        url = "http://localhost:7878/"
        api_key = "test-key"

        # Patch the entire check to simulate what happens when a
        # ClientConnectorError is caught by the service method.
        # We use a plain OSError wrapped in ClientConnectorError via
        # the mock, but since ConnectionKey may not exist in all
        # aiohttp versions, we patch at the session level.
        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_session_cls.return_value.__aexit__ = AsyncMock(
                return_value=False
            )
            mock_session.get.side_effect = aiohttp.ClientConnectorError.__new__(
                aiohttp.ClientConnectorError
            )
            # ClientConnectorError needs special init; use a simpler approach
            mock_session.get.side_effect = None

        # Simpler approach: use aioresponses with a generic Exception
        # that the code catches in the broad except, then test the
        # specific ClientConnectorError branch by patching.
        with patch(
            "src.services.health.aiohttp.ClientSession"
        ) as mock_session_cls:
            mock_ctx = AsyncMock()
            mock_session_cls.return_value.__aenter__ = AsyncMock(
                return_value=mock_ctx
            )
            mock_session_cls.return_value.__aexit__ = AsyncMock(
                return_value=False
            )
            # Raise ClientConnectorError on get()
            err = OSError("Connection refused")
            mock_ctx.get = MagicMock(side_effect=aiohttp.ClientConnectorError(
                connection_key=MagicMock(), os_error=err
            ))

            healthy, status = await service.check_service_health(
                url, api_key, "radarr"
            )

        assert healthy is False
        assert "Connection failed" in status


# ---------------------------------------------------------------------------
# run_health_checks
# ---------------------------------------------------------------------------


class TestRunHealthChecks:
    @pytest.mark.asyncio
    async def test_run_health_checks(self):
        service = HealthService()

        with patch.object(
            service,
            "check_service_health",
            new_callable=AsyncMock,
            return_value=(True, "Online (v4.7.0)"),
        ):
            results = await service.run_health_checks()

        assert "media_services" in results
        assert "download_clients" in results
        assert isinstance(results["media_services"], list)
        assert isinstance(results["download_clients"], list)

        # With default mock config, radarr/sonarr/lidarr are enabled
        service_names = [s["name"] for s in results["media_services"]]
        assert "Radarr" in service_names
        assert "Sonarr" in service_names
        assert "Lidarr" in service_names

        for svc in results["media_services"]:
            assert svc["healthy"] is True


# ---------------------------------------------------------------------------
# start / stop
# ---------------------------------------------------------------------------


class TestStartStop:
    @pytest.mark.asyncio
    async def test_start_sets_running(self):
        service = HealthService()
        assert service._running is False

        await service.start(interval_minutes=1)
        assert service._running is True

        # Clean up: cancel the background task
        if service._task and not service._task.done():
            service._task.cancel()
            try:
                await service._task
            except asyncio.CancelledError:
                pass
        service._running = False

    @pytest.mark.asyncio
    async def test_stop_sets_not_running(self):
        service = HealthService()
        service._running = True

        await service.stop()
        assert service._running is False
