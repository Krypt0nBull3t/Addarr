"""
Filename: validation.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Configuration check module.

This module checks the loaded configuration and prints the results
(used by startup and `run.py --check`).
"""

from colorama import Fore
from .logger import get_logger
from ..config.settings import config

logger = get_logger("addarr.validation")


def check_config() -> bool:
    """Check configuration status and display results"""
    print(f"\n{Fore.CYAN}{'═' * 50}")
    print(f"{Fore.CYAN} 🔍 Checking configuration status...")
    print(f"{Fore.CYAN}{'═' * 50}")

    try:
        # Check core settings
        print(f"\n{Fore.YELLOW}Core Settings:")
        _check_core_settings()

        # Check media services
        print(f"\n{Fore.YELLOW}Media Services:")
        _check_media_services()

        # Check download clients
        print(f"\n{Fore.YELLOW}Download Clients:")
        _check_download_clients()

        # Check security settings
        print(f"\n{Fore.YELLOW}Security Settings:")
        _check_security_settings()

        print(f"\n{Fore.GREEN}✅ Configuration check completed successfully!")
        return True

    except Exception as e:
        print(f"\n{Fore.RED}❌ Error checking configuration: {str(e)}")
        return False


def _check_core_settings():
    """Check core configuration settings"""
    # Check Telegram settings
    if not config.get("telegram", {}).get("token"):
        print(f"{Fore.RED}❌ Telegram bot token not configured")
    else:
        print(f"{Fore.GREEN}✅ Telegram bot token configured")

    # Check language setting
    language = config.get("language", "")
    valid_languages = ["de-de", "en-us", "es-es", "fr-fr", "it-it", "nl-be", "pl-pl", "pt-pt", "ru-ru"]
    if language in valid_languages:
        print(f"{Fore.GREEN}✅ Language set to: {language}")
    else:
        print(f"{Fore.RED}❌ Invalid language setting: {language}")


def _check_media_services():
    """Check media service configurations"""
    services = {
        "Radarr": config.get("radarr", {}),
        "Sonarr": config.get("sonarr", {}),
        "Lidarr": config.get("lidarr", {})
    }

    for name, service in services.items():
        if service.get("enable"):
            if service.get("auth", {}).get("apikey"):
                print(f"{Fore.GREEN}✅ {name} enabled and configured")
            else:
                print(f"{Fore.YELLOW}⚠️ {name} enabled but API key missing")
        else:
            print(f"{Fore.BLUE}ℹ️ {name} disabled")


def _check_download_clients():
    """Check download client configurations"""
    # Check Transmission
    transmission = config.get("transmission", {})
    if transmission.get("enable"):
        print(f"{Fore.GREEN}✅ Transmission enabled")
        if transmission.get("authentication"):
            if transmission.get("username") and transmission.get("password"):
                print(f"{Fore.GREEN}  ✓ Authentication configured")
            else:
                print(f"{Fore.YELLOW}  ⚠️ Authentication enabled but credentials missing")
    else:
        print(f"{Fore.BLUE}ℹ️ Transmission disabled")

    # Check SABnzbd
    sabnzbd = config.get("sabnzbd", {})
    if sabnzbd.get("enable"):
        print(f"{Fore.GREEN}✅ SABnzbd enabled")
        if sabnzbd.get("auth", {}).get("apikey"):
            print(f"{Fore.GREEN}  ✓ API key configured")
        else:
            print(f"{Fore.YELLOW}  ⚠️ API key missing")
    else:
        print(f"{Fore.BLUE}ℹ️ SABnzbd disabled")


def _check_security_settings():
    """Check security configuration"""
    security = config.get("security", {})

    # Check admin mode
    if security.get("enableAdmin"):
        if config.get("admins"):
            logger.info("✅ Admin mode enabled with %d admin(s)", len(config.get("admins", [])))
        else:
            logger.warning("⚠️ Admin mode enabled but no admins configured")
    else:
        logger.info("ℹ️ Admin mode disabled")

    # Check allowlist
    if security.get("enableAllowlist"):
        if config.get("allow_list"):
            logger.info("✅ Allowlist enabled with %d user(s)", len(config.get("allow_list", [])))
        else:
            logger.warning("⚠️ Allowlist enabled but no users configured")
    else:
        logger.info("ℹ️ Allowlist disabled")
