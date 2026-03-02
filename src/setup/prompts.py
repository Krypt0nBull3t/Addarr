"""User-facing prompts for the setup wizard.

All functions are standalone async, returning values instead of mutating state.
The wizard assigns return values to its config dict.
"""

from typing import Dict, Any, List

import questionary
from colorama import Fore


async def select_services() -> List[str]:
    """Let user select which services to configure.

    Returns list of service names (e.g. ["radarr", "transmission"]).
    Retries if no media service is selected.
    """
    print(f"\n{Fore.CYAN}Media Services Configuration")
    print(f"{Fore.YELLOW}Note: At least one media service must be enabled")
    print(f"{Fore.YELLOW}Select at least one of: Radarr, Sonarr, or Lidarr")

    media_services = await questionary.checkbox(
        "Select media services to enable (select one or more):",
        choices=[
            questionary.Choice("🎬 Radarr - Movies", "radarr"),
            questionary.Choice("📺 Sonarr - TV Shows", "sonarr"),
            questionary.Choice("🎵 Lidarr - Music", "lidarr"),
        ],
    ).ask_async()

    if not media_services:
        print(f"{Fore.RED}⚠️  Error: At least one media service must be selected")
        return await select_services()

    # Optional download clients
    print(f"\n{Fore.CYAN}Download Clients Configuration")
    print(f"{Fore.YELLOW}Note: Download clients are completely optional")

    should_configure_clients = await questionary.confirm(
        "Would you like to configure download clients? (optional)",
        default=False,
    ).ask_async()

    download_clients = []
    if should_configure_clients:
        download_clients = await questionary.checkbox(
            "Select download clients to configure:",
            choices=[
                questionary.Choice(
                    "📥 SABnzbd - Usenet (optional)", "sabnzbd"
                ),
                questionary.Choice(
                    "⬇️ Transmission - Torrents (optional)", "transmission"
                ),
                questionary.Choice(
                    "❌ None - Skip download client configuration", "none"
                ),
            ],
        ).ask_async()

        if not download_clients or "none" in download_clients:
            print(
                f"{Fore.YELLOW}ℹ️  Skipping download client configuration"
            )
            download_clients = []
    else:
        print(f"{Fore.YELLOW}ℹ️  Skipping download client configuration")

    print(f"\n{Fore.GREEN}✅ Selected services:")
    for service in media_services:
        print(f"  • {service.title()} (Media Service)")
    for client in download_clients:
        if client != "none":
            print(f"  • {client.title()} (Download Client)")

    return media_services + download_clients


async def configure_language() -> str:
    """Configure language settings.

    Returns the selected language code (e.g. "en-us").
    """
    print(f"\n{Fore.CYAN}Language Configuration 🌍")

    languages = [
        {"name": "English (US)", "value": "en-us", "description": "American English"},
        {"name": "Deutsch", "value": "de-de", "description": "German"},
        {"name": "Español", "value": "es-es", "description": "Spanish"},
        {"name": "Français", "value": "fr-fr", "description": "French"},
        {"name": "Italiano", "value": "it-it", "description": "Italian"},
        {
            "name": "Nederlands (België)",
            "value": "nl-be",
            "description": "Belgian Dutch",
        },
        {"name": "Polski", "value": "pl-pl", "description": "Polish"},
        {"name": "Português", "value": "pt-pt", "description": "Portuguese"},
        {"name": "Русский", "value": "ru-ru", "description": "Russian"},
    ]

    selected_language = await questionary.select(
        "Select your preferred language:",
        choices=[
            {
                "name": lang["name"],
                "value": lang["value"],
                "help": lang["description"],
            }
            for lang in languages
        ],
        use_shortcuts=True,
        use_indicator=True,
        instruction="Use arrow keys to navigate, Enter to select",
    ).ask_async()

    print(
        f"{Fore.GREEN}✅ Language set to: "
        f"{next(lang['name'] for lang in languages if lang['value'] == selected_language)}"
    )
    return selected_language


async def configure_telegram() -> Dict[str, str]:
    """Configure Telegram bot settings.

    Returns dict with 'token' and 'password' keys.
    """
    print(f"\n{Fore.CYAN}Configuring Telegram Bot 🤖")

    return {
        "token": await questionary.password(
            "Enter your Telegram bot token (from @BotFather):"
        ).ask_async(),
        "password": await questionary.password(
            "Enter a password for chat authentication:"
        ).ask_async(),
    }


async def configure_access_control() -> Dict[str, Any]:
    """Configure access control settings.

    Returns dict with keys: 'security', 'admins', and optionally 'allow_list'.
    """
    print(f"\n{Fore.CYAN}Configuring Access Control 🔒")

    security = {
        "enableAdmin": await questionary.confirm(
            "Enable admin features?",
            default=True,
        ).ask_async(),
        "enableAllowlist": await questionary.confirm(
            "Enable allowlist restriction?",
            default=True,
        ).ask_async(),
    }

    # Admin IDs
    admin_ids = []
    while True:
        admin_id = await questionary.text(
            "Enter admin Telegram ID (or leave empty to finish):"
        ).ask_async()

        if not admin_id:
            break

        try:
            admin_id_int = int(admin_id)
            admin_ids.append(admin_id_int)
        except ValueError:
            print(
                f"{Fore.RED}❌ Invalid ID format. "
                f"Please enter a numeric Telegram ID"
            )
            continue

    result: Dict[str, Any] = {
        "security": security,
        "admins": admin_ids,
    }

    # Allowed users
    if security["enableAllowlist"]:
        allowed_users = []
        while True:
            user_id = await questionary.text(
                "Enter allowed user Telegram ID (or leave empty to finish):"
            ).ask_async()

            if not user_id:
                break

            try:
                user_id_int = int(user_id)
                allowed_users.append(user_id_int)
            except ValueError:
                print(
                    f"{Fore.RED}❌ Invalid ID format. "
                    f"Please enter a numeric Telegram ID"
                )
                continue

        result["allow_list"] = allowed_users

    return result


async def configure_logging() -> Dict[str, Any]:
    """Configure logging settings.

    Returns dict with 'toConsole', 'debug', and 'adminNotifyId' keys.
    """
    print(f"\n{Fore.CYAN}Configuring Logging 📝")

    logging_config: Dict[str, Any] = {
        "toConsole": await questionary.confirm(
            "Enable console logging?",
            default=True,
        ).ask_async(),
        "debug": await questionary.confirm(
            "Enable debug logging?",
            default=False,
        ).ask_async(),
    }

    while True:
        admin_notify = await questionary.text(
            "Enter Telegram chat ID for admin notifications "
            "(or leave empty to skip):"
        ).ask_async()

        if not admin_notify:
            logging_config["adminNotifyId"] = 0
            break

        try:
            notify_id = int(admin_notify)
            logging_config["adminNotifyId"] = notify_id
            break
        except ValueError:
            print(
                f"{Fore.RED}❌ Invalid ID format. "
                f"Please enter a numeric Telegram chat ID"
            )
            continue

    return logging_config


async def configure_arr_features(service: str) -> Dict[str, Any]:
    """Configure *arr specific features.

    Returns dict with feature settings for the given service.
    """
    features: Dict[str, Any] = {
        "search": await questionary.confirm(
            "Enable automatic searching when adding new media?",
            default=True,
        ).ask_async()
    }

    if service == "radarr":
        features["minimumAvailability"] = await questionary.select(
            "Select minimum availability requirement:",
            choices=[
                {
                    "name": "Announced - As soon as movie is announced",
                    "value": "announced",
                },
                {
                    "name": "In Cinemas - When movie is in theaters",
                    "value": "inCinemas",
                },
                {"name": "Released - Physical/Web release", "value": "released"},
                {
                    "name": "PreDB - When release is confirmed",
                    "value": "preDB",
                },
            ],
            use_shortcuts=True,
        ).ask_async()
    elif service == "sonarr":
        features["seasonFolder"] = await questionary.confirm(
            "Organize episodes in season folders?",
            default=True,
        ).ask_async()
    elif service == "lidarr":
        features["albumFolder"] = await questionary.confirm(
            "Organize tracks in album folders?",
            default=True,
        ).ask_async()
        features["monitorOption"] = await questionary.select(
            "Select which releases to monitor:",
            choices=[
                {"name": "All Releases", "value": "all"},
                {"name": "Future Releases Only", "value": "future"},
                {"name": "Missing Releases Only", "value": "missing"},
                {"name": "None", "value": "none"},
            ],
            use_shortcuts=True,
        ).ask_async()

    return features


async def configure_required_value(
    config: Dict[str, Any],
    service: str,
    value: str,
    default_config: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Configure a single required value for a service.

    Mutates and returns the config dict. If the service key doesn't exist,
    initializes it from default_config (or empty dict).
    """
    if service == "telegram":
        if value == "token":
            if "telegram" not in config:
                config["telegram"] = {}
            config["telegram"]["token"] = await questionary.password(
                "Enter your Telegram bot token (from @BotFather):"
            ).ask_async()
            # Add password field if it doesn't exist
            if "password" not in config["telegram"]:
                config["telegram"]["password"] = await questionary.password(
                    "Enter a password for chat authentication:"
                ).ask_async()
    elif service in ["radarr", "sonarr", "lidarr"]:
        if value == "apikey":
            if service not in config:
                config[service] = default_config if default_config else {}
            config[service]["auth"]["apikey"] = await questionary.password(
                f"Enter {service.title()} API key:"
            ).ask_async()

    return config
