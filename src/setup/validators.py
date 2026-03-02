"""Connection testing and port validation for setup wizard."""

import asyncio

import aiohttp
import questionary
from colorama import Fore

# Service API paths — separated from auth config to avoid taint tracking
# through shared data structures (CodeQL clear-text logging rule).
SERVICE_PATHS = {
    "radarr": "/api/v3/system/status",
    "sonarr": "/api/v3/system/status",
    "lidarr": "/api/v1/system/status",
    "transmission": "/transmission/rpc",
    "sabnzbd": "/api",
}

# Services that use status-code-only validation (no JSON body check)
TRANSMISSION_EXPECTED_STATUS = [200, 401, 409]


def _build_headers(service: str, apikey: str = None) -> dict:
    """Build request headers for a service. Kept separate from logged data."""
    if service == "transmission" or not apikey:
        return {}
    return {"X-Api-Key": apikey}


async def validate_service_connection(
    service: str, url: str, port: int, ssl: bool, apikey: str = None
) -> bool:
    """Validate connection to a service by testing its API endpoint.

    Returns True if connection is successful.
    """
    if service not in SERVICE_PATHS:
        return False

    protocol = "https" if ssl else "http"
    path = SERVICE_PATHS[service]
    full_url = f"{protocol}://{url}:{port}{path}"
    headers = _build_headers(service, apikey)
    params = {"mode": "version"} if service == "sabnzbd" else {}

    try:
        print(f"{Fore.YELLOW}Testing connection to {full_url}...")
        async with aiohttp.ClientSession() as session:
            async with session.get(
                full_url,
                headers=headers,
                params=params,
                ssl=False,
                timeout=5,
            ) as response:
                # Transmission: validate by status code only
                if service == "transmission":
                    if response.status in TRANSMISSION_EXPECTED_STATUS:
                        print(
                            f"{Fore.GREEN}✅ Service responded "
                            f"with status {response.status}"
                        )
                        return True
                    print(f"{Fore.RED}❌ Unexpected status code: {response.status}")
                    return False

                # API services: check JSON response content
                if response.status == 200:
                    try:
                        data = await response.json()
                        if "version" in data:
                            print(
                                f"{Fore.GREEN}✅ Service API "
                                f"responded successfully"
                            )
                            return True
                        print(f"{Fore.RED}❌ Response missing expected data")
                        return False
                    except ValueError:
                        print(f"{Fore.RED}❌ Invalid JSON response")
                        return False
                else:
                    print(
                        f"{Fore.RED}❌ Service returned "
                        f"status code {response.status}"
                    )
                    return False

    except aiohttp.ClientError:
        print(f"{Fore.RED}❌ Connection error for {service}")
        return False
    except asyncio.TimeoutError:
        print(f"{Fore.RED}❌ Connection timed out")
        return False
    except Exception:
        print(f"{Fore.RED}❌ Unexpected error connecting to {service}")
        return False


async def get_valid_port(message: str, default: str) -> int:
    """Get a valid port number from user input.

    Loops until user provides a valid port (1-65535).
    """
    while True:
        try:
            port = await questionary.text(
                message,
                default=default,
            ).ask_async()
            port_num = int(port)
            if 1 <= port_num <= 65535:
                return port_num
            print(f"{Fore.RED}Port must be between 1 and 65535")
        except ValueError:
            print(f"{Fore.RED}Please enter a valid port number")
