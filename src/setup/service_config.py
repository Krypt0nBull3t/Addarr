"""Service default configurations and validated config loop for setup wizard."""

from typing import Dict, Any
from urllib.parse import urlparse

import questionary
from colorama import Fore

from src.setup.validators import validate_service_connection, get_valid_port


def get_default_port(service: str) -> str:
    """Get default port for a service."""
    defaults = {
        "radarr": "7878",
        "sonarr": "8989",
        "lidarr": "8686",
        "transmission": "9091",
        "sabnzbd": "8090",
    }
    return defaults.get(service, "8090")


def get_default_service_config(service: str) -> Dict[str, Any]:
    """Get default configuration for a service.

    Returns a dict with the full default config structure.
    Transmission and SABnzbd have different shapes from arr services.
    """
    if service == "transmission":
        return {
            "enable": False,
            "onlyAdmin": True,
            "host": "localhost",
            "authentication": False,
            "username": "",
            "password": "",
        }

    if service == "sabnzbd":
        return {
            "enable": False,
            "onlyAdmin": True,
            "server": {
                "addr": "localhost",
                "port": 8090,
                "path": "/",
                "ssl": False,
            },
            "auth": {
                "apikey": "",
                "username": "",
                "password": "",
            },
        }

    base_config: Dict[str, Any] = {
        "enable": False,
        "server": {
            "addr": "localhost",
            "port": get_default_port(service),
            "path": "/",
            "ssl": False,
        },
        "auth": {
            "apikey": "",
            "username": "",
            "password": "",
        },
        "features": {"search": True},
        "paths": {"excludedRootFolders": [], "narrowRootFolderNames": True},
        "quality": {"excludedProfiles": []},
        "tags": {"default": ["telegram"], "addRequesterIdTag": True},
        "adminRestrictions": False,
    }

    if service == "lidarr":
        base_config["metadataProfileId"] = 1
        base_config["features"]["albumFolder"] = True
        base_config["features"]["monitorOption"] = "all"
    elif service == "radarr":
        base_config["features"]["minimumAvailability"] = "announced"
    elif service == "sonarr":
        base_config["features"]["seasonFolder"] = True

    return base_config


async def get_valid_service_config(service: str) -> Dict[str, Any]:
    """Get valid service configuration with connection testing.

    Prompts user for server address, port, SSL, and API key,
    then validates the connection. Retries on failure if user wants.
    """
    while True:
        # Get server address
        addr = await questionary.text(
            f"Enter {service} server address:",
            default="localhost",
        ).ask_async()

        # Validate URL format
        try:
            parsed = urlparse(f"http://{addr}")
            if not parsed.netloc:
                print(f"{Fore.RED}Invalid server address format")
                continue
        except Exception:
            print(f"{Fore.RED}Invalid server address format")
            continue

        # Get port
        port = await get_valid_port(
            f"Enter {service} port:",
            get_default_port(service),
        )

        # Get SSL setting
        ssl = await questionary.confirm(
            "Use SSL/HTTPS?",
            default=False,
        ).ask_async()

        # Get API key if applicable
        apikey = None
        if service in ["radarr", "sonarr", "lidarr", "sabnzbd"]:
            apikey = await questionary.password(
                f"Enter {service} API key:"
            ).ask_async()

        print(f"{Fore.YELLOW}Testing connection to {service}...")
        if await validate_service_connection(service, addr, port, ssl, apikey):
            print(f"{Fore.GREEN}✅ Successfully connected to {service}")

            if service == "sabnzbd":
                return {
                    "enable": True,
                    "onlyAdmin": True,
                    "server": {
                        "addr": addr,
                        "port": port,
                        "path": "/",
                        "ssl": ssl,
                    },
                    "auth": {
                        "apikey": apikey,
                        "username": "",
                        "password": "",
                    },
                }
            else:
                return {
                    "server": {
                        "addr": addr,
                        "port": port,
                        "path": "/",
                        "ssl": ssl,
                    },
                    "auth": {
                        "apikey": apikey or "",
                        "username": "",
                        "password": "",
                    },
                }
        else:
            print(f"{Fore.RED}❌ Failed to connect to {service}")
            retry = await questionary.confirm(
                "Would you like to try again?",
                default=True,
            ).ask_async()

            if not retry:
                print(f"{Fore.YELLOW}Skipping connection validation")
                if service == "sabnzbd":
                    return {
                        "enable": False,
                        "onlyAdmin": True,
                        "server": {
                            "addr": addr,
                            "port": port,
                            "path": "/",
                            "ssl": ssl,
                        },
                        "auth": {
                            "apikey": apikey or "",
                            "username": "",
                            "password": "",
                        },
                    }
                else:
                    return {
                        "server": {
                            "addr": addr,
                            "port": port,
                            "path": "/",
                            "ssl": ssl,
                        },
                        "auth": {
                            "apikey": apikey or "",
                            "username": "",
                            "password": "",
                        },
                    }
