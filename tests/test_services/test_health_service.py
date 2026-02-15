"""
Tests for src/services/health.py -- HealthService singleton and display_health_status.
"""

import asyncio

import aiohttp
import pytest
from aioresponses import aioresponses
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.health import HealthService, display_health_status


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


class TestHealthServiceSingleton:
    def test_singleton(self):
        a = HealthService()
        b = HealthService()
        assert a is b


# ---------------------------------------------------------------------------
# display_health_status
# ---------------------------------------------------------------------------


class TestDisplayHealthStatus:
    def test_all_healthy(self, capsys):
        results = {
            "media_services": [
                {"name": "Radarr", "healthy": True, "status": "Online (v4.7.0)"},
                {"name": "Sonarr", "healthy": True, "status": "Online (v3.0.0)"},
            ],
            "download_clients": [
                {"name": "SABnzbd", "healthy": True, "status": "Online (v3.5.0)"},
            ],
        }
        result = display_health_status(results)
        assert result is True

        output = capsys.readouterr().out
        assert "All services are healthy" in output

    def test_some_unhealthy(self, capsys):
        results = {
            "media_services": [
                {"name": "Radarr", "healthy": True, "status": "Online (v4.7.0)"},
                {"name": "Sonarr", "healthy": False, "status": "Error: HTTP 500"},
            ],
            "download_clients": [],
        }
        result = display_health_status(results)
        assert result is False

        output = capsys.readouterr().out
        assert "Some services are not responding" in output

    def test_no_media_services(self, capsys):
        results = {
            "media_services": [],
            "download_clients": [
                {"name": "SABnzbd", "healthy": True, "status": "Online"},
            ],
        }
        result = display_health_status(results)
        assert result is True

    def test_no_download_clients(self, capsys):
        results = {
            "media_services": [
                {"name": "Radarr", "healthy": True, "status": "Online"},
            ],
            "download_clients": [],
        }
        result = display_health_status(results)
        assert result is True


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
    async def test_check_radarr_health_success(self):
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
    async def test_check_sonarr_health_success(self):
        service = HealthService()
        url = "http://localhost:8989/"

        with aioresponses() as m:
            m.get(
                "http://localhost:8989/api/v3/system/status",
                payload={"version": "3.0.0"},
                status=200,
            )
            healthy, status = await service.check_service_health(
                url, "key", "sonarr"
            )

        assert healthy is True
        assert "v3.0.0" in status

    @pytest.mark.asyncio
    async def test_check_lidarr_health_v1_api(self):
        service = HealthService()
        url = "http://localhost:8686/"

        with aioresponses() as m:
            m.get(
                "http://localhost:8686/api/v1/system/status",
                payload={"version": "1.5.0"},
                status=200,
            )
            healthy, status = await service.check_service_health(
                url, "key", "lidarr"
            )

        assert healthy is True
        assert "v1.5.0" in status

    @pytest.mark.asyncio
    async def test_check_unknown_service_type(self):
        service = HealthService()

        healthy, status = await service.check_service_health(
            "http://localhost:1234/", "key", "unknown"
        )

        assert healthy is False
        assert "Unknown service type" in status

    @pytest.mark.asyncio
    async def test_check_service_health_http_error(self):
        service = HealthService()
        url = "http://localhost:7878/"

        with aioresponses() as m:
            m.get(
                "http://localhost:7878/api/v3/system/status",
                status=500,
            )
            healthy, status = await service.check_service_health(
                url, "key", "radarr"
            )

        assert healthy is False
        assert "HTTP 500" in status

    @pytest.mark.asyncio
    async def test_check_service_health_connection_error(self):
        service = HealthService()
        url = "http://localhost:7878/"

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
            err = OSError("Connection refused")
            mock_ctx.get = MagicMock(side_effect=aiohttp.ClientConnectorError(
                connection_key=MagicMock(), os_error=err
            ))

            healthy, status = await service.check_service_health(
                url, "key", "radarr"
            )

        assert healthy is False
        assert "Connection failed" in status

    @pytest.mark.asyncio
    async def test_check_service_health_timeout(self):
        service = HealthService()
        url = "http://localhost:7878/"

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
            mock_ctx.get = MagicMock(side_effect=asyncio.TimeoutError())

            healthy, status = await service.check_service_health(
                url, "key", "radarr"
            )

        assert healthy is False
        assert "timeout" in status.lower()

    @pytest.mark.asyncio
    async def test_check_service_health_generic_exception(self):
        service = HealthService()
        url = "http://localhost:7878/"

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
            mock_ctx.get = MagicMock(side_effect=RuntimeError("Unexpected"))

            healthy, status = await service.check_service_health(
                url, "key", "radarr"
            )

        assert healthy is False
        assert "Unexpected" in status


# ---------------------------------------------------------------------------
# check_sabnzbd_health
# ---------------------------------------------------------------------------


class TestCheckSabnzbdHealth:
    @pytest.mark.asyncio
    async def test_check_sabnzbd_health_success(self):
        service = HealthService()
        url = "http://localhost:8090/"

        import re
        pattern = re.compile(r"^http://localhost:8090/api\b.*$")

        with aioresponses() as m:
            m.get(
                pattern,
                payload={"version": "3.5.0"},
                status=200,
            )
            healthy, status = await service.check_sabnzbd_health(
                url, "test-key"
            )

        assert healthy is True
        assert "v3.5.0" in status

    @pytest.mark.asyncio
    async def test_check_sabnzbd_health_json_fail_valid_text(self):
        """When JSON decode fails, fall back to text response."""
        service = HealthService()
        url = "http://localhost:8090/"

        with patch(
            "src.services.health.aiohttp.ClientSession"
        ) as mock_session_cls:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(side_effect=Exception("JSON decode error"))
            mock_resp.text = AsyncMock(return_value="3.5.0")

            mock_ctx = AsyncMock()
            mock_ctx.get = MagicMock(return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_resp),
                __aexit__=AsyncMock(return_value=False),
            ))
            mock_session_cls.return_value.__aenter__ = AsyncMock(
                return_value=mock_ctx
            )
            mock_session_cls.return_value.__aexit__ = AsyncMock(
                return_value=False
            )

            healthy, status = await service.check_sabnzbd_health(url, "key")

        assert healthy is True
        assert "v3.5.0" in status

    @pytest.mark.asyncio
    async def test_check_sabnzbd_health_json_fail_invalid_text(self):
        """When JSON decode fails and text is too long, return error."""
        service = HealthService()
        url = "http://localhost:8090/"

        with patch(
            "src.services.health.aiohttp.ClientSession"
        ) as mock_session_cls:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(side_effect=Exception("JSON decode error"))
            mock_resp.text = AsyncMock(return_value="A" * 50)

            mock_ctx = AsyncMock()
            mock_ctx.get = MagicMock(return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_resp),
                __aexit__=AsyncMock(return_value=False),
            ))
            mock_session_cls.return_value.__aenter__ = AsyncMock(
                return_value=mock_ctx
            )
            mock_session_cls.return_value.__aexit__ = AsyncMock(
                return_value=False
            )

            healthy, status = await service.check_sabnzbd_health(url, "key")

        assert healthy is False
        assert "Invalid response format" in status

    @pytest.mark.asyncio
    async def test_check_sabnzbd_health_http_error(self):
        service = HealthService()
        url = "http://localhost:8090/"

        import re
        pattern = re.compile(r"^http://localhost:8090/api\b.*$")

        with aioresponses() as m:
            m.get(
                pattern,
                status=500,
            )
            healthy, status = await service.check_sabnzbd_health(url, "key")

        assert healthy is False
        assert "HTTP 500" in status

    @pytest.mark.asyncio
    async def test_check_sabnzbd_health_exception(self):
        service = HealthService()
        url = "http://localhost:8090/"

        with patch(
            "src.services.health.aiohttp.ClientSession"
        ) as mock_session_cls:
            mock_session_cls.return_value.__aenter__ = AsyncMock(
                side_effect=Exception("Connection refused")
            )
            mock_session_cls.return_value.__aexit__ = AsyncMock(
                return_value=False
            )

            healthy, status = await service.check_sabnzbd_health(url, "key")

        assert healthy is False
        assert "Connection refused" in status


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

    @pytest.mark.asyncio
    async def test_run_health_checks_sabnzbd_enabled(self):
        """Test that SABnzbd is checked when enabled in config."""
        service = HealthService()

        with patch(
            "src.services.health.config"
        ) as mock_config:
            mock_config.get.side_effect = lambda key, default=None: (
                {
                    "enable": True,
                    "server": {
                        "addr": "localhost",
                        "port": 8090,
                        "path": "/",
                        "ssl": False,
                    },
                    "auth": {"apikey": "test-key"},
                }
                if key == "sabnzbd"
                else {
                    "enable": True,
                    "server": {
                        "addr": "localhost",
                        "port": 7878,
                        "path": "/",
                        "ssl": False,
                    },
                    "auth": {"apikey": "test-key"},
                }
                if key == "radarr"
                else {
                    "enable": True,
                    "server": {
                        "addr": "localhost",
                        "port": 8989,
                        "path": "/",
                        "ssl": False,
                    },
                    "auth": {"apikey": "test-key"},
                }
                if key == "sonarr"
                else {
                    "enable": True,
                    "server": {
                        "addr": "localhost",
                        "port": 8686,
                        "path": "/",
                        "ssl": False,
                    },
                    "auth": {"apikey": "test-key"},
                }
                if key == "lidarr"
                else default
            )
            with patch.object(
                service,
                "check_service_health",
                new_callable=AsyncMock,
                return_value=(True, "Online"),
            ), patch.object(
                service,
                "check_sabnzbd_health",
                new_callable=AsyncMock,
                return_value=(True, "Online (v3.5.0)"),
            ):
                results = await service.run_health_checks()

        assert len(results["download_clients"]) == 1
        assert results["download_clients"][0]["name"] == "SABnzbd"
        assert results["download_clients"][0]["healthy"] is True


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
    async def test_start_already_running(self):
        service = HealthService()
        service._running = True

        # Should log warning and return early
        await service.start(interval_minutes=1)

        # Still running, but no task created since it was already running
        assert service._running is True

    @pytest.mark.asyncio
    async def test_stop_sets_not_running(self):
        service = HealthService()
        service._running = True

        await service.stop()
        assert service._running is False

    @pytest.mark.asyncio
    async def test_stop_not_running(self):
        service = HealthService()
        service._running = False

        # Should return early without error
        await service.stop()
        assert service._running is False

    @pytest.mark.asyncio
    async def test_stop_with_active_task(self):
        service = HealthService()
        service._running = True

        # Create a real task that sleeps
        async def _dummy():
            await asyncio.sleep(100)

        service._task = asyncio.create_task(_dummy())
        assert not service._task.done()

        await service.stop()
        assert service._running is False

    @pytest.mark.asyncio
    async def test_stop_with_done_task(self):
        service = HealthService()
        service._running = True

        # Create a task that's already done
        async def _done():
            return

        service._task = asyncio.create_task(_done())
        await asyncio.sleep(0.01)  # Let the task finish
        assert service._task.done()

        await service.stop()
        assert service._running is False


# ---------------------------------------------------------------------------
# _monitor_loop
# ---------------------------------------------------------------------------


class TestMonitorLoop:
    @pytest.mark.asyncio
    async def test_monitor_loop_healthy(self):
        service = HealthService()
        service._running = True
        service.interval = 0.01  # Very short interval

        healthy_results = {
            "media_services": [
                {"name": "Radarr", "healthy": True, "status": "Online"},
            ],
            "download_clients": [],
        }

        call_count = 0

        async def _mock_run_health_checks():
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                service._running = False
            return healthy_results

        with patch.object(
            service, "run_health_checks", side_effect=_mock_run_health_checks
        ):
            await service._monitor_loop()

        assert service._last_check is not None
        assert len(service._unhealthy_services) == 0

    @pytest.mark.asyncio
    async def test_monitor_loop_unhealthy_then_recovery(self):
        service = HealthService()
        service._running = True
        service.interval = 0.01

        unhealthy_results = {
            "media_services": [
                {"name": "Radarr", "healthy": False, "status": "Error: HTTP 500"},
            ],
            "download_clients": [],
        }
        healthy_results = {
            "media_services": [
                {"name": "Radarr", "healthy": True, "status": "Online"},
            ],
            "download_clients": [],
        }

        call_count = 0

        async def _mock_checks():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return unhealthy_results
            elif call_count == 2:
                return healthy_results
            else:
                service._running = False
                return healthy_results

        with patch.object(service, "run_health_checks", side_effect=_mock_checks):
            await service._monitor_loop()

        # After recovery, unhealthy should be empty
        assert len(service._unhealthy_services) == 0

    @pytest.mark.asyncio
    async def test_monitor_loop_exception(self):
        service = HealthService()
        service._running = True
        service.interval = 0.01

        call_count = 0

        async def _mock_checks():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Health check failed")
            service._running = False
            return {"media_services": [], "download_clients": []}

        with patch.object(service, "run_health_checks", side_effect=_mock_checks):
            await service._monitor_loop()

        # Should not crash -- the exception is caught and logged
        assert call_count >= 2
