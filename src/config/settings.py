"""
Filename: settings.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Configuration management module.

This module handles loading and validating the application configuration
from YAML files. It provides access to configuration values and ensures
all required settings are present and valid.
"""

import os
import sys
import yaml
import questionary
from typing import Dict, Any, List
from colorama import Fore

from ..definitions import CONFIG_PATH, CONFIG_EXAMPLE_PATH
from ..utils.backup import create_backup


def _is_interactive():
    """Check if we're running in an interactive terminal."""
    return sys.stdin.isatty() and sys.stdout.isatty()


class ConfigurationError(Exception):
    """Base class for configuration errors"""
    pass


def validate_port(port, service_name):
    """Validate that a port number is in the valid range 1-65535."""
    if not isinstance(port, int) or port < 1 or port > 65535:
        raise ConfigurationError(
            f"Invalid port for {service_name}: {port}. Must be between 1 and 65535."
        )


def validate_service_apikey(service_config, service_name):
    """Validate that an enabled service has a non-empty API key."""
    if service_config.get("enable"):
        apikey = service_config.get("auth", {}).get("apikey")
        if not apikey or not str(apikey).strip():
            raise ConfigurationError(
                f"{service_name} is enabled but has no API key configured."
            )


def validate_server_addr(addr, service_name):
    """Validate that a server address is a valid hostname or IP.

    Rejects empty values, protocol prefixes, and whitespace.
    """
    if not addr or not str(addr).strip():
        raise ConfigurationError(
            f"Invalid server address for {service_name}: address is empty."
        )
    addr_str = str(addr)
    if addr_str.startswith(("http://", "https://")):
        raise ConfigurationError(
            f"Invalid server address for {service_name}: '{addr_str}'. "
            f"Remove the protocol prefix (http:// or https://). "
            f"Use the 'ssl' option instead."
        )
    if " " in addr_str.strip():
        raise ConfigurationError(
            f"Invalid server address for {service_name}: '{addr_str}'. "
            f"Address must not contain spaces."
        )


def validate_telegram_token(telegram_config):
    """Validate that the Telegram bot token is configured."""
    if not telegram_config.get("token"):
        raise ConfigurationError(
            "Telegram bot token is not configured."
        )


class Config:
    """Configuration management class"""

    def __init__(self):
        self._config = self._load_config()
        self._validate_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        if not os.path.exists(CONFIG_PATH):
            raise ConfigurationError(f"Configuration file not found: {CONFIG_PATH}")

        with open(CONFIG_PATH, 'r') as f:
            return yaml.safe_load(f)

    def _validate_config(self):
        """Validate configuration against example config"""
        with open(CONFIG_EXAMPLE_PATH, 'r') as f:
            example_config = yaml.safe_load(f)

        missing_keys = self._get_missing_keys(example_config, self._config)
        if missing_keys:
            print(f"\n{Fore.YELLOW}Missing configuration keys detected: {', '.join(missing_keys)}")

            if _is_interactive():
                if questionary.confirm(
                    "Would you like to configure these settings now?"
                ).ask():
                    create_backup()
                    for key in missing_keys:
                        self._configure_missing_key(key)
                    with open(CONFIG_PATH, 'w') as f:
                        yaml.dump(self._config, f, default_flow_style=False)
                    print(f"{Fore.GREEN}✅ Configuration updated successfully!")
                else:
                    raise ConfigurationError(
                        f"Missing required configuration keys: "
                        f"{', '.join(missing_keys)}"
                    )
            else:
                # Non-interactive (e.g. Docker): apply defaults from example
                print(
                    f"{Fore.YELLOW}Non-interactive environment detected. "
                    f"Applying defaults from config_example.yaml..."
                )
                for key in missing_keys:
                    self._apply_default_key(key, example_config)
                print(
                    f"{Fore.GREEN}✅ Defaults applied. "
                    f"Edit config.yaml to customize these settings."
                )

        self._validate_values()

    def _apply_default_key(self, key: str, example_config: Dict):
        """Apply a default value from example config for a missing key."""
        parts = key.split('.')

        # Get default value from example config
        default = example_config
        for part in parts:
            if isinstance(default, dict):
                default = default.get(part)
            else:
                default = None
                break

        # Set value in config
        current = self._config
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = default

    def _configure_missing_key(self, key: str):
        """Configure a missing configuration key"""
        parts = key.split('.')
        current = self._config

        # Build up the configuration path
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Handle specific configuration types
        if key.endswith('.enable'):
            value = questionary.confirm(
                f"Enable {parts[0].title()}?",
                default=False
            ).ask()
        elif key.endswith('.apikey'):
            value = questionary.password(
                f"Enter {parts[0].title()} API key:"
            ).ask()
        elif key.endswith('.token'):
            value = questionary.password(
                f"Enter {parts[0].title()} token:"
            ).ask()
        else:
            # Default to text input
            value = questionary.text(
                f"Enter value for {key}:"
            ).ask()

        # Set the value
        current[parts[-1]] = value

    def _validate_values(self):
        """Validate configuration values"""
        # Validate language
        valid_languages = [
            "de-de", "en-us", "es-es", "fr-fr",
            "it-it", "nl-be", "pl-pl", "pt-pt", "ru-ru"
        ]
        if self._config.get("language") not in valid_languages:
            raise ConfigurationError(
                f"Invalid language. Must be one of: {', '.join(valid_languages)}"
            )

        # Validate server addresses for enabled services
        for service_name in ("radarr", "sonarr", "lidarr", "sabnzbd"):
            service = self._config.get(service_name, {})
            if service.get("enable"):
                addr = service.get("server", {}).get("addr")
                validate_server_addr(addr, service_name)

    def _get_missing_keys(self, example: Dict, config: Dict, prefix="") -> List[str]:
        """Recursively find missing configuration keys"""
        missing = []
        for key, value in example.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if key not in config:
                missing.append(full_key)
            elif isinstance(value, dict):
                missing.extend(
                    self._get_missing_keys(value, config[key], full_key)
                )
        return missing

    def __getitem__(self, key):
        return self._config[key]

    def get(self, key, default=None):
        return self._config.get(key, default)

    def update_nested(self, dotted_key: str, value):
        """Update a nested config value using dot notation."""
        keys = dotted_key.split(".")
        current = self._config
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

    def save(self):
        """Persist current config to disk."""
        create_backup()
        with open(CONFIG_PATH, 'w') as f:
            yaml.dump(self._config, f, default_flow_style=False)


# Create global config instance
config = Config()
