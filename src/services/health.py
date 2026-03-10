"""
Filename: health.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Health monitoring service module.

This module provides centralized health monitoring functionality for all services.
Includes both one-time checks and periodic monitoring.
"""

import aiohttp
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from colorama import Fore, Style

from src.api.lidarr import LidarrClient
from src.api.radarr import RadarrClient
from src.api.sonarr import SonarrClient
from src.api.transmission import TransmissionClient
from src.config.settings import config
from src.services.notification import NotificationService
from src.utils.logger import get_logger

logger = get_logger("addarr.health")


def display_health_status(results: Dict[str, List[Dict]]) -> bool:
    """Display health check results

    Args:
        results: Health check results

    Returns:
        bool: True if all enabled services are healthy
    """
    print(f"\n{Fore.CYAN}{'═' * 50}")
    print(f"{Fore.CYAN} 🏥 Starting initial service health check...")
    print(f"{Fore.CYAN}{'═' * 50}")

    all_healthy = True

    if results["media_services"]:
        print(f"\n{Fore.YELLOW}Media Services:")
        for service in results["media_services"]:
            status_color = Fore.GREEN if service["healthy"] else Fore.RED
            print(f"• {service['name']}: {status_color}{service['status']}{Style.RESET_ALL}")
            all_healthy &= service["healthy"]

    if results["download_clients"]:
        print(f"\n{Fore.YELLOW}Download Clients:")
        for client in results["download_clients"]:
            status_color = Fore.GREEN if client["healthy"] else Fore.RED
            print(f"• {client['name']}: {status_color}{client['status']}{Style.RESET_ALL}")
            all_healthy &= client["healthy"]

    print(f"\n{Fore.CYAN}{'═' * 50}")

    if all_healthy:
        print(f"{Fore.GREEN}✅ All services are healthy!\n")
    else:
        print(f"{Fore.RED}❌ Some services are not responding!\n")
        print(f"{Fore.YELLOW}Please check your configuration and ensure all services are running.\n")

    return all_healthy


class HealthService:
    """Service for health monitoring"""

    _instance: Optional["HealthService"] = None
    _last_check: Optional[datetime] = None
    _unhealthy_services: set[str]
    _running: bool
    _task: Optional[asyncio.Task[None]] = None
    interval: int
    _failure_counts: Dict[str, int]
    _down_since: Dict[str, datetime]
    _alerted_services: Set[str]

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(HealthService, cls).__new__(cls)
            cls._initialize()
        return cls._instance

    @classmethod
    def _initialize(cls):
        cls._last_check = None
        cls._unhealthy_services = set()
        cls._running = False
        cls._task = None
        cls.interval = 15 * 60  # Default 15 minutes
        cls._failure_counts = {}
        cls._down_since = {}
        cls._alerted_services = set()

    async def start(self, interval_minutes: int = 15):
        """Start periodic health monitoring"""
        if self._running:
            logger.warning("Health monitoring already running")
            return

        self.interval = interval_minutes * 60  # Convert to seconds
        self._running = True
        logger.info(f"🏥 Starting health monitoring (interval: {interval_minutes} minutes)")

        self._task = asyncio.create_task(self._monitor_loop())

    async def stop(self):
        """Stop health monitoring"""
        if not self._running:
            return

        self._running = False
        logger.info("🛑 Stopping health monitoring")

        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format a duration in seconds to a human-readable string."""
        total_seconds = int(seconds)
        if total_seconds < 60:
            return f"{total_seconds} seconds"
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        parts = []
        if hours == 1:
            parts.append("1 hour")
        elif hours > 1:
            parts.append(f"{hours} hours")
        if minutes == 1:
            parts.append("1 minute")
        elif minutes > 1:
            parts.append(f"{minutes} minutes")
        return " ".join(parts) if parts else "0 seconds"

    async def _check_alerts(self, current_unhealthy: set) -> None:
        """Check for state transitions and send alerts via NotificationService."""
        alert_config = config.get("health_alerts", {})
        threshold = alert_config.get("flap_threshold", 2)
        notifier = NotificationService()

        # Extract service names from "ServiceName: Error details" format
        current_names = set()
        name_to_entry: Dict[str, str] = {}
        for entry in current_unhealthy:
            name = entry.split(":")[0].strip()
            current_names.add(name)
            name_to_entry[name] = entry

        # Track failures for currently unhealthy services
        for name in current_names:
            self._failure_counts[name] = self._failure_counts.get(name, 0) + 1
            if name not in self._down_since:
                self._down_since[name] = datetime.now()

            # Alert if at threshold and not already alerted
            if (
                self._failure_counts[name] >= threshold
                and name not in self._alerted_services
            ):
                status = name_to_entry.get(name, name)
                msg = (
                    f"⚠️ {name} is unreachable\n"
                    f"Status: {status}\n"
                    f"Failing since: "
                    f"{self._down_since[name].strftime('%H:%M:%S')}"
                )
                await notifier.notify_admin(msg)
                self._alerted_services.add(name)
                logger.warning(f"Alert sent: {name} is unreachable")

        # Handle recoveries
        previously_tracked = set(self._failure_counts.keys())
        recovered_names = previously_tracked - current_names
        for name in recovered_names:
            if name in self._alerted_services:
                # Was alerted — send recovery
                down_since = self._down_since[name]
                duration_secs = (
                    datetime.now() - down_since
                ).total_seconds()
                duration_str = self._format_duration(duration_secs)
                msg = (
                    f"✅ {name} is back online\n"
                    f"Was down for: {duration_str}"
                )
                await notifier.notify_admin(msg)
                logger.info(f"Recovery alert sent: {name} is back online")

            # Clean up state regardless of whether we alerted
            self._failure_counts.pop(name, None)
            self._down_since.pop(name, None)
            self._alerted_services.discard(name)

    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                logger.info(f"{Fore.CYAN}{'═' * 50}")
                logger.info(f"{Fore.CYAN}🏥 Running health check...{Style.RESET_ALL}")

                results = await self.run_health_checks()
                self._last_check = datetime.now()
                next_check = self._last_check + timedelta(seconds=self.interval)

                current_unhealthy = set()

                # Process results and update status
                for service_type in ["media_services", "download_clients"]:
                    for service in results[service_type]:
                        if not service["healthy"]:
                            error_msg = f"{service['name']}: {service['status']}"
                            current_unhealthy.add(error_msg)

                # Log changes in service health
                new_failures = current_unhealthy - self._unhealthy_services
                if new_failures:
                    logger.error("❌ Services became unhealthy:")
                    for service in new_failures:
                        logger.error(f"  • {service}")

                recovered = self._unhealthy_services - current_unhealthy
                if recovered:
                    logger.info("✅ Services recovered:")
                    for service in recovered:
                        logger.info(f"  • {service}")

                self._unhealthy_services = current_unhealthy

                # Send alerts if enabled
                alert_config = config.get("health_alerts", {})
                if alert_config.get("enable", False):
                    await self._check_alerts(current_unhealthy)

                if not current_unhealthy:
                    logger.info("✅ All services healthy")

                # Show next check time
                logger.info(f"⏰ Next check at: {next_check.strftime('%H:%M:%S')}")
                logger.info(f"{Fore.CYAN}{'═' * 50}{Style.RESET_ALL}")

            except Exception as e:
                logger.error(f"❌ Error in health monitoring: {str(e)}")

            await asyncio.sleep(self.interval)

    async def check_service_health(self, url: str, api_key: str, service_type: str) -> Tuple[bool, str]:
        """Check if a service is responding"""
        try:
            server_url = url.rstrip('/')

            # Different endpoints for different services
            if service_type == "radarr":
                api_url = f"{server_url}/api/v3/system/status"
            elif service_type == "sonarr":
                api_url = f"{server_url}/api/v3/system/status"
            elif service_type == "lidarr":
                api_url = f"{server_url}/api/v1/system/status"
            else:
                return False, f"Unknown service type: {service_type}"

            async with aiohttp.ClientSession() as session:
                headers = {'X-Api-Key': api_key}
                logger.debug(f"Checking health of {service_type} at: {api_url}")

                async with session.get(api_url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        version = data.get('version', 'Unknown')
                        return True, f"Online (v{version})"
                    else:
                        return False, f"Error: HTTP {response.status}"

        except aiohttp.ClientConnectorError:
            return False, "Error: Connection failed"
        except asyncio.TimeoutError:
            return False, "Error: Connection timeout"
        except Exception as e:
            return False, f"Error: {str(e)}"

    async def check_sabnzbd_health(self, url: str, api_key: str) -> Tuple[bool, str]:
        """Check SABnzbd connection"""
        try:
            server_url = url.rstrip('/')
            api_url = f"{server_url}/api"

            params = {
                'apikey': api_key,
                'mode': 'version',
                'output': 'json'
            }

            async with aiohttp.ClientSession() as session:
                logger.debug(f"Checking SABnzbd health at: {api_url}")
                async with session.get(api_url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        try:
                            data = await response.json()
                            version = data.get('version', 'Unknown')
                        except Exception:
                            text = await response.text()
                            if text and len(text) < 20:
                                version = text.strip()
                            else:
                                return False, "Error: Invalid response format"

                        return True, f"Online (v{version})"
                    else:
                        return False, f"Error: HTTP {response.status}"

        except Exception as e:
            return False, f"Error: {str(e)}"

    async def check_transmission_health(self) -> Tuple[bool, str]:
        """Check Transmission connection via RPC client."""
        try:
            client = TransmissionClient()
            data = await client.get_session()
            version = data.get("arguments", {}).get("version", "Unknown")
            return True, f"Online (v{version})"
        except aiohttp.ClientConnectorError:
            return False, "Error: Connection failed"
        except asyncio.TimeoutError:
            return False, "Error: Connection timeout"
        except Exception as e:
            return False, f"Error: {str(e)}"

    async def run_health_checks(self) -> Dict[str, List[Dict]]:
        """Run health checks on all enabled services"""
        results: Dict[str, List[Dict[str, Any]]] = {
            "media_services": [],
            "download_clients": []
        }

        # Check media services
        services = [
            ("Radarr", "radarr"),
            ("Sonarr", "sonarr"),
            ("Lidarr", "lidarr")
        ]

        for service_name, config_key in services:
            service_config = config.get(config_key, {})
            if service_config.get("enable"):
                server_config = service_config.get("server", {})
                protocol = "https" if server_config.get("ssl", False) else "http"
                addr = server_config.get("addr", "localhost")
                port = server_config.get("port", "")
                base_path = server_config.get("path", "").rstrip('/')

                url = f"{protocol}://{addr}:{port}{base_path}"
                api_key = service_config.get("auth", {}).get("apikey")

                is_healthy, status = await self.check_service_health(url, api_key, service_name.lower())
                results["media_services"].append({
                    "name": service_name,
                    "healthy": is_healthy,
                    "status": status
                })

        # Check Transmission
        transmission = config.get("transmission", {})
        if transmission.get("enable"):
            is_healthy, status = await self.check_transmission_health()
            results["download_clients"].append({
                "name": "Transmission",
                "healthy": is_healthy,
                "status": status
            })

        # Check SABnzbd
        sabnzbd = config.get("sabnzbd", {})
        if sabnzbd.get("enable"):
            server_config = sabnzbd.get("server", {})
            protocol = "https" if server_config.get("ssl", False) else "http"
            addr = server_config.get("addr", "localhost")
            port = server_config.get("port", "")
            base_path = server_config.get("path", "").rstrip('/')

            url = f"{protocol}://{addr}:{port}{base_path}"
            api_key = sabnzbd.get("auth", {}).get("apikey")

            is_healthy, status = await self.check_sabnzbd_health(url, api_key)
            results["download_clients"].append({
                "name": "SABnzbd",
                "healthy": is_healthy,
                "status": status
            })

        return results

    def _get_api_client(self, service_key: str) -> Optional[Any]:
        """Create an API client instance for the given service key."""
        client_map: Dict[str, type] = {
            "radarr": RadarrClient,
            "sonarr": SonarrClient,
            "lidarr": LidarrClient,
        }
        cls = client_map.get(service_key)
        if cls is None:
            return None
        return cls()

    async def get_disk_space(self) -> List[Dict]:
        """Get disk space from the first enabled *arr service."""
        services = ["radarr", "sonarr", "lidarr"]

        for service_key in services:
            service_config = config.get(service_key, {})
            if not service_config.get("enable"):
                continue

            client = self._get_api_client(service_key)
            if client is None:
                continue

            try:
                result = await client.get_disk_space()
                if result:
                    return result
            except Exception as e:
                logger.warning(
                    f"Failed to get disk space from {service_key}: {e}"
                )
            finally:
                await client.close()

        return []

    def get_status(self) -> Dict:
        """Get current monitoring status"""
        return {
            "running": self._running,
            "last_check": self._last_check,
            "unhealthy_services": list(self._unhealthy_services)
        }


# Create global instance
health_service = HealthService()
