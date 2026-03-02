"""Connection testing and port validation for setup wizard."""

import asyncio

import aiohttp
import questionary
from colorama import Fore


async def validate_service_connection(
    service: str, url: str, port: int, ssl: bool, apikey: str = None
) -> bool:
    """Validate connection to a service by testing its API endpoint.

    Returns True if connection is successful.
    """
    protocol = "https" if ssl else "http"
    base_url = f"{protocol}://{url}:{port}"

    # Define test endpoints and expected responses for each service
    endpoints = {
        "radarr": {
            "path": "/api/v3/system/status",
            "headers": {"X-Api-Key": apikey} if apikey else {},
            "expected_keys": ["version"],
        },
        "sonarr": {
            "path": "/api/v3/system/status",
            "headers": {"X-Api-Key": apikey} if apikey else {},
            "expected_keys": ["version"],
        },
        "lidarr": {
            "path": "/api/v1/system/status",
            "headers": {"X-Api-Key": apikey} if apikey else {},
            "expected_keys": ["version"],
        },
        "transmission": {
            "path": "/transmission/rpc",
            "headers": {},
            "expected_status": [200, 401, 409],
        },
        "sabnzbd": {
            "path": "/api",
            "headers": {"X-Api-Key": apikey} if apikey else {},
            "params": {"mode": "version"},
            "expected_keys": ["version"],
        },
    }

    if service not in endpoints:
        return False

    endpoint = endpoints[service]
    full_url = f"{base_url}{endpoint['path']}"

    try:
        print(f"{Fore.YELLOW}Testing connection to {full_url}...")
        async with aiohttp.ClientSession() as session:
            async with session.get(
                full_url,
                headers=endpoint["headers"],
                params=endpoint.get("params", {}),
                ssl=False,
                timeout=5,
            ) as response:
                # Check if status code is in expected list (if defined)
                if "expected_status" in endpoint:
                    if response.status in endpoint["expected_status"]:
                        print(
                            f"{Fore.GREEN}✅ Service responded "
                            f"with status {response.status}"
                        )
                        return True
                    print(f"{Fore.RED}❌ Unexpected status code: {response.status}")
                    return False

                # For regular API endpoints, check response content
                if response.status == 200:
                    try:
                        data = await response.json()
                        if all(
                            key in data for key in endpoint["expected_keys"]
                        ):
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

    except aiohttp.ClientError as e:
        print(f"{Fore.RED}❌ Connection error: {str(e)}")
        return False
    except asyncio.TimeoutError:
        print(f"{Fore.RED}❌ Connection timed out")
        return False
    except Exception as e:
        print(f"{Fore.RED}❌ Unexpected error: {str(e)}")
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
