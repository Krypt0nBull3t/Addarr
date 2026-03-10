"""
Tests for src/services/health.py -- HealthService singleton and display_health_status.
"""

import asyncio

import aiohttp
import pytest
from aioresponses import aioresponses
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.health import HealthService, display_health_status
from tests.fixtures.sample_data import RADARR_DISK_SPACE


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
# check_bazarr_health
# ---------------------------------------------------------------------------


class TestCheckBazarrHealth:
    @pytest.mark.asyncio
    async def test_check_bazarr_health_success(self):
        service = HealthService()
        url = "http://localhost:6767"
        api_key = "test-key"

        with aioresponses() as m:
            m.get(
                "http://localhost:6767/api/system/status",
                payload={
                    "data": {"bazarr_version": "1.4.0"}
                },
                status=200,
            )
            healthy, status = await service.check_bazarr_health(
                url, api_key
            )

        assert healthy is True
        assert "v1.4.0" in status

    @pytest.mark.asyncio
    async def test_check_bazarr_health_http_error(self):
        service = HealthService()
        url = "http://localhost:6767"

        with aioresponses() as m:
            m.get(
                "http://localhost:6767/api/system/status",
                status=500,
            )
            healthy, status = await service.check_bazarr_health(
                url, "key"
            )

        assert healthy is False
        assert "HTTP 500" in status

    @pytest.mark.asyncio
    async def test_check_bazarr_health_timeout(self):
        service = HealthService()
        url = "http://localhost:6767"

        import asyncio

        with aioresponses() as m:
            m.get(
                "http://localhost:6767/api/system/status",
                exception=asyncio.TimeoutError(),
            )
            healthy, status = await service.check_bazarr_health(
                url, "key"
            )

        assert healthy is False
        assert "timeout" in status.lower()

    @pytest.mark.asyncio
    async def test_check_bazarr_health_connection_error(self):
        service = HealthService()
        url = "http://localhost:6767"

        import aiohttp as _aiohttp

        with aioresponses() as m:
            m.get(
                "http://localhost:6767/api/system/status",
                exception=_aiohttp.ClientConnectorError(
                    connection_key=MagicMock(), os_error=OSError("refused")
                ),
            )
            healthy, status = await service.check_bazarr_health(
                url, "key"
            )

        assert healthy is False
        assert "Connection failed" in status

    @pytest.mark.asyncio
    async def test_check_bazarr_health_generic_exception(self):
        service = HealthService()
        url = "http://localhost:6767"

        with aioresponses() as m:
            m.get(
                "http://localhost:6767/api/system/status",
                exception=RuntimeError("unexpected"),
            )
            healthy, status = await service.check_bazarr_health(
                url, "key"
            )

        assert healthy is False
        assert "unexpected" in status


# ---------------------------------------------------------------------------
# check_transmission_health
# ---------------------------------------------------------------------------


class TestCheckTransmissionHealth:
    @pytest.mark.asyncio
    async def test_check_transmission_health_success(self):
        service = HealthService()

        with patch("src.services.health.TransmissionClient") as MockClient:
            mock_instance = AsyncMock()
            MockClient.return_value = mock_instance
            mock_instance.get_session.return_value = {
                "arguments": {"version": "4.0.0"},
                "result": "success",
            }

            healthy, status = await service.check_transmission_health()

        assert healthy is True
        assert "Online" in status
        assert "v4.0.0" in status

    @pytest.mark.asyncio
    async def test_check_transmission_health_missing_version(self):
        service = HealthService()

        with patch("src.services.health.TransmissionClient") as MockClient:
            mock_instance = AsyncMock()
            MockClient.return_value = mock_instance
            mock_instance.get_session.return_value = {
                "arguments": {},
                "result": "success",
            }

            healthy, status = await service.check_transmission_health()

        assert healthy is True
        assert "Online" in status
        assert "vUnknown" in status

    @pytest.mark.asyncio
    async def test_check_transmission_health_connection_error(self):
        service = HealthService()

        with patch("src.services.health.TransmissionClient") as MockClient:
            mock_instance = AsyncMock()
            MockClient.return_value = mock_instance
            err = OSError("Connection refused")
            mock_instance.get_session.side_effect = (
                aiohttp.ClientConnectorError(
                    connection_key=MagicMock(), os_error=err
                )
            )

            healthy, status = await service.check_transmission_health()

        assert healthy is False
        assert "Connection failed" in status

    @pytest.mark.asyncio
    async def test_check_transmission_health_timeout(self):
        service = HealthService()

        with patch("src.services.health.TransmissionClient") as MockClient:
            mock_instance = AsyncMock()
            MockClient.return_value = mock_instance
            mock_instance.get_session.side_effect = asyncio.TimeoutError()

            healthy, status = await service.check_transmission_health()

        assert healthy is False
        assert "timeout" in status.lower()

    @pytest.mark.asyncio
    async def test_check_transmission_health_generic_exception(self):
        service = HealthService()

        with patch("src.services.health.TransmissionClient") as MockClient:
            mock_instance = AsyncMock()
            MockClient.return_value = mock_instance
            mock_instance.get_session.side_effect = RuntimeError("Unexpected")

            healthy, status = await service.check_transmission_health()

        assert healthy is False
        assert "Unexpected" in status


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
        ), patch.object(
            service,
            "check_bazarr_health",
            new_callable=AsyncMock,
            return_value=(True, "Online (v1.4.0)"),
        ):
            results = await service.run_health_checks()

        assert "media_services" in results
        assert "download_clients" in results
        assert isinstance(results["media_services"], list)
        assert isinstance(results["download_clients"], list)

        # With default mock config, radarr/sonarr/lidarr/bazarr are enabled
        service_names = [s["name"] for s in results["media_services"]]
        assert "Radarr" in service_names
        assert "Sonarr" in service_names
        assert "Lidarr" in service_names
        assert "Bazarr" in service_names

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

    @pytest.mark.asyncio
    async def test_run_health_checks_transmission_enabled(self):
        """Test that Transmission is checked when enabled in config."""
        service = HealthService()

        with patch(
            "src.services.health.config"
        ) as mock_config:
            mock_config.get.side_effect = lambda key, default=None: (
                {
                    "enable": True,
                    "host": "localhost",
                    "port": 9091,
                    "ssl": False,
                    "username": None,
                    "password": None,
                }
                if key == "transmission"
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
                if key in ("radarr", "sonarr", "lidarr")
                else default
            )
            with patch.object(
                service,
                "check_service_health",
                new_callable=AsyncMock,
                return_value=(True, "Online"),
            ), patch.object(
                service,
                "check_transmission_health",
                new_callable=AsyncMock,
                return_value=(True, "Online (v4.0.0)"),
            ) as mock_tx_health:
                results = await service.run_health_checks()

        mock_tx_health.assert_called_once()
        tx_entries = [
            c for c in results["download_clients"] if c["name"] == "Transmission"
        ]
        assert len(tx_entries) == 1
        assert tx_entries[0]["healthy"] is True
        assert "v4.0.0" in tx_entries[0]["status"]

    @pytest.mark.asyncio
    async def test_run_health_checks_transmission_disabled(self):
        """Test that Transmission is NOT checked when disabled in config."""
        service = HealthService()

        with patch.object(
            service,
            "check_service_health",
            new_callable=AsyncMock,
            return_value=(True, "Online"),
        ), patch.object(
            service,
            "check_transmission_health",
            new_callable=AsyncMock,
            return_value=(True, "Online (v4.0.0)"),
        ) as mock_tx_health:
            results = await service.run_health_checks()

        mock_tx_health.assert_not_called()
        tx_entries = [
            c for c in results["download_clients"] if c["name"] == "Transmission"
        ]
        assert len(tx_entries) == 0

    @pytest.mark.asyncio
    async def test_run_health_checks_both_download_clients(self):
        """Test that both Transmission and SABnzbd appear when enabled."""
        service = HealthService()

        with patch(
            "src.services.health.config"
        ) as mock_config:
            mock_config.get.side_effect = lambda key, default=None: (
                {
                    "enable": True,
                    "host": "localhost",
                    "port": 9091,
                    "ssl": False,
                    "username": None,
                    "password": None,
                }
                if key == "transmission"
                else {
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
                if key in ("radarr", "sonarr", "lidarr")
                else default
            )
            with patch.object(
                service,
                "check_service_health",
                new_callable=AsyncMock,
                return_value=(True, "Online"),
            ), patch.object(
                service,
                "check_transmission_health",
                new_callable=AsyncMock,
                return_value=(True, "Online (v4.0.0)"),
            ), patch.object(
                service,
                "check_sabnzbd_health",
                new_callable=AsyncMock,
                return_value=(True, "Online (v3.5.0)"),
            ):
                results = await service.run_health_checks()

        names = [c["name"] for c in results["download_clients"]]
        assert "Transmission" in names
        assert "SABnzbd" in names
        assert len(results["download_clients"]) == 2


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


# ---------------------------------------------------------------------------
# _get_api_client
# ---------------------------------------------------------------------------


class TestGetApiClient:
    def test_get_api_client_radarr(self):
        """Returns a RadarrClient for 'radarr' key."""
        service = HealthService()
        with patch("src.services.health.RadarrClient") as MockRadarr:
            mock_instance = MagicMock()
            MockRadarr.return_value = mock_instance
            client = service._get_api_client("radarr")
        assert client is mock_instance

    def test_get_api_client_sonarr(self):
        """Returns a SonarrClient for 'sonarr' key."""
        service = HealthService()
        with patch("src.services.health.SonarrClient") as MockSonarr:
            mock_instance = MagicMock()
            MockSonarr.return_value = mock_instance
            client = service._get_api_client("sonarr")
        assert client is mock_instance

    def test_get_api_client_lidarr(self):
        """Returns a LidarrClient for 'lidarr' key."""
        service = HealthService()
        with patch("src.services.health.LidarrClient") as MockLidarr:
            mock_instance = MagicMock()
            MockLidarr.return_value = mock_instance
            client = service._get_api_client("lidarr")
        assert client is mock_instance

    def test_get_api_client_unknown_returns_none(self):
        """Returns None for unknown service key."""
        service = HealthService()
        client = service._get_api_client("unknown")
        assert client is None


# ---------------------------------------------------------------------------
# get_disk_space
# ---------------------------------------------------------------------------


class TestGetDiskSpace:
    @pytest.mark.asyncio
    async def test_get_disk_space_returns_drives_from_first_enabled(self):
        """Returns drives from the first enabled *arr service."""
        service = HealthService()

        mock_client = AsyncMock()
        mock_client.get_disk_space.return_value = RADARR_DISK_SPACE
        mock_client.close = AsyncMock()

        with patch.object(
            service, "_get_api_client", return_value=mock_client
        ):
            results = await service.get_disk_space()

        assert len(results) == 2
        assert results[0]["path"] == "/movies"
        mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_disk_space_skips_disabled_services(self):
        """Skips disabled services and queries the first enabled one."""
        service = HealthService()

        mock_client = AsyncMock()
        mock_client.get_disk_space.return_value = RADARR_DISK_SPACE
        mock_client.close = AsyncMock()

        with patch("src.services.health.config") as mock_config:
            mock_config.get.side_effect = lambda key, default=None: (
                {"enable": False} if key == "radarr"
                else {"enable": True} if key == "sonarr"
                else {"enable": True} if key == "lidarr"
                else default
            )
            with patch.object(
                service, "_get_api_client", return_value=mock_client
            ) as mock_get:
                results = await service.get_disk_space()

        # Should have been called with sonarr (first enabled after radarr)
        mock_get.assert_called_once_with("sonarr")
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_get_disk_space_no_enabled_services(self):
        """Returns empty list when no services are enabled."""
        service = HealthService()

        with patch("src.services.health.config") as mock_config:
            mock_config.get.return_value = {"enable": False}
            results = await service.get_disk_space()

        assert results == []

    @pytest.mark.asyncio
    async def test_get_disk_space_falls_through_on_error(self):
        """Falls through to next enabled service on client error."""
        service = HealthService()

        failing_client = AsyncMock()
        failing_client.get_disk_space.side_effect = Exception("connection refused")
        failing_client.close = AsyncMock()

        working_client = AsyncMock()
        working_client.get_disk_space.return_value = RADARR_DISK_SPACE
        working_client.close = AsyncMock()

        call_count = 0

        def _mock_get_client(key):
            nonlocal call_count
            call_count += 1
            if key == "radarr":
                return failing_client
            return working_client

        with patch.object(
            service, "_get_api_client", side_effect=_mock_get_client
        ):
            results = await service.get_disk_space()

        assert len(results) == 2
        assert call_count == 2  # radarr failed, sonarr succeeded

    @pytest.mark.asyncio
    async def test_get_disk_space_get_api_client_returns_none(self):
        """Skips service when _get_api_client returns None."""
        service = HealthService()

        mock_client = AsyncMock()
        mock_client.get_disk_space.return_value = RADARR_DISK_SPACE
        mock_client.close = AsyncMock()

        def _mock_get_client(key):
            if key == "radarr":
                return None
            return mock_client

        with patch.object(
            service, "_get_api_client", side_effect=_mock_get_client
        ):
            results = await service.get_disk_space()

        assert len(results) == 2


# ---------------------------------------------------------------------------
# Alert state initialization
# ---------------------------------------------------------------------------


class TestAlertStateInitialization:
    def test_alert_state_attributes_initialized_empty(self):
        """Alert tracking dicts/sets are empty after singleton reset."""
        service = HealthService()
        assert service._failure_counts == {}
        assert service._down_since == {}
        assert service._alerted_services == set()


# ---------------------------------------------------------------------------
# _check_alerts
# ---------------------------------------------------------------------------


class TestCheckAlerts:
    ALERT_CONFIG = {"enable": True, "flap_threshold": 2}

    @pytest.mark.asyncio
    async def test_single_failure_does_not_alert(self):
        """One failure is below default threshold (2) — no notification."""
        service = HealthService()
        mock_notifier = AsyncMock()

        with patch(
            "src.services.health.NotificationService"
        ) as MockNS:
            MockNS.return_value = mock_notifier
            await service._check_alerts(
                {"Radarr: Error: HTTP 500"}, self.ALERT_CONFIG
            )

        mock_notifier.notify_admin.assert_not_called()

    @pytest.mark.asyncio
    async def test_threshold_reached_triggers_alert(self):
        """Two consecutive failures triggers degradation alert."""
        service = HealthService()
        mock_notifier = AsyncMock()

        with patch(
            "src.services.health.NotificationService"
        ) as MockNS:
            MockNS.return_value = mock_notifier
            await service._check_alerts(
                {"Radarr: Error: HTTP 500"}, self.ALERT_CONFIG
            )
            await service._check_alerts(
                {"Radarr: Error: HTTP 500"}, self.ALERT_CONFIG
            )

        mock_notifier.notify_admin.assert_called_once()
        msg = mock_notifier.notify_admin.call_args[0][0]
        assert "Radarr" in msg
        assert "unreachable" in msg.lower() or "⚠️" in msg

    @pytest.mark.asyncio
    async def test_no_duplicate_alert_after_threshold(self):
        """Once alerted, don't re-alert on subsequent failures."""
        service = HealthService()
        mock_notifier = AsyncMock()

        with patch(
            "src.services.health.NotificationService"
        ) as MockNS:
            MockNS.return_value = mock_notifier
            await service._check_alerts(
                {"Radarr: Error: HTTP 500"}, self.ALERT_CONFIG
            )
            await service._check_alerts(
                {"Radarr: Error: HTTP 500"}, self.ALERT_CONFIG
            )
            await service._check_alerts(
                {"Radarr: Error: HTTP 500"}, self.ALERT_CONFIG
            )

        # Only one alert, not two
        mock_notifier.notify_admin.assert_called_once()

    @pytest.mark.asyncio
    async def test_recovery_after_alert_sends_recovery_message(self):
        """Service recovers after being alerted — sends recovery notification."""
        service = HealthService()
        mock_notifier = AsyncMock()

        with patch(
            "src.services.health.NotificationService"
        ) as MockNS:
            MockNS.return_value = mock_notifier
            await service._check_alerts(
                {"Radarr: Error: HTTP 500"}, self.ALERT_CONFIG
            )
            await service._check_alerts(
                {"Radarr: Error: HTTP 500"}, self.ALERT_CONFIG
            )
            await service._check_alerts(set(), self.ALERT_CONFIG)

        # Two calls: one degradation, one recovery
        assert mock_notifier.notify_admin.call_count == 2
        recovery_msg = mock_notifier.notify_admin.call_args_list[1][0][0]
        assert "Radarr" in recovery_msg
        assert "back online" in recovery_msg.lower() or "✅" in recovery_msg

    @pytest.mark.asyncio
    async def test_recovery_before_threshold_sends_no_alerts(self):
        """Service fails once then recovers — no alerts at all."""
        service = HealthService()
        mock_notifier = AsyncMock()

        with patch(
            "src.services.health.NotificationService"
        ) as MockNS:
            MockNS.return_value = mock_notifier
            await service._check_alerts(
                {"Radarr: Error: HTTP 500"}, self.ALERT_CONFIG
            )
            await service._check_alerts(set(), self.ALERT_CONFIG)

        mock_notifier.notify_admin.assert_not_called()
        # State cleaned up
        assert service._failure_counts == {}
        assert service._down_since == {}

    @pytest.mark.asyncio
    async def test_recovery_cleans_up_state(self):
        """After recovery, all tracking state for that service is cleared."""
        service = HealthService()
        mock_notifier = AsyncMock()

        with patch(
            "src.services.health.NotificationService"
        ) as MockNS:
            MockNS.return_value = mock_notifier
            await service._check_alerts(
                {"Radarr: Error: HTTP 500"}, self.ALERT_CONFIG
            )
            await service._check_alerts(
                {"Radarr: Error: HTTP 500"}, self.ALERT_CONFIG
            )
            await service._check_alerts(set(), self.ALERT_CONFIG)

        assert "Radarr" not in service._failure_counts
        assert "Radarr" not in service._down_since
        assert "Radarr" not in service._alerted_services


class TestAlertsDisabled:
    @pytest.mark.asyncio
    async def test_monitor_loop_skips_alerts_when_disabled(self):
        """When health_alerts.enable is false, _check_alerts is not called."""
        service = HealthService()
        service._running = True
        service.interval = 0.01

        unhealthy_results = {
            "media_services": [
                {"name": "Radarr", "healthy": False, "status": "Error: HTTP 500"},
            ],
            "download_clients": [],
        }

        call_count = 0

        async def _mock_checks():
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                service._running = False
            return unhealthy_results

        with patch.object(
            service, "run_health_checks", side_effect=_mock_checks
        ), patch(
            "src.services.health.config"
        ) as mock_config:
            mock_config.get.side_effect = lambda key, default=None: (
                {"enable": False}
                if key == "health_alerts"
                else default
            )
            with patch.object(
                service, "_check_alerts", new_callable=AsyncMock
            ) as mock_check:
                await service._monitor_loop()

        mock_check.assert_not_called()

    @pytest.mark.asyncio
    async def test_monitor_loop_calls_alerts_when_enabled(self):
        """When health_alerts.enable is true, _check_alerts is called."""
        service = HealthService()
        service._running = True
        service.interval = 0.01

        unhealthy_results = {
            "media_services": [
                {"name": "Radarr", "healthy": False, "status": "Error: HTTP 500"},
            ],
            "download_clients": [],
        }

        call_count = 0

        async def _mock_checks():
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                service._running = False
            return unhealthy_results

        with patch.object(
            service, "run_health_checks", side_effect=_mock_checks
        ), patch(
            "src.services.health.config"
        ) as mock_config:
            mock_config.get.side_effect = lambda key, default=None: (
                {"enable": True, "flap_threshold": 2}
                if key == "health_alerts"
                else default
            )
            with patch.object(
                service, "_check_alerts", new_callable=AsyncMock
            ) as mock_check:
                await service._monitor_loop()

        assert mock_check.call_count >= 1


class TestFormatDuration:
    def test_format_seconds(self):
        service = HealthService()
        assert service._format_duration(30) == "30 seconds"

    def test_format_minutes(self):
        service = HealthService()
        assert service._format_duration(300) == "5 minutes"

    def test_format_hours_and_minutes(self):
        service = HealthService()
        assert service._format_duration(5400) == "1 hour 30 minutes"

    def test_format_exact_hour(self):
        service = HealthService()
        assert service._format_duration(3600) == "1 hour"

    def test_format_one_minute(self):
        service = HealthService()
        assert service._format_duration(60) == "1 minute"

    def test_format_multiple_hours(self):
        service = HealthService()
        assert service._format_duration(7200) == "2 hours"
