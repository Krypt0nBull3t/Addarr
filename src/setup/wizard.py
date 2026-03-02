"""
Filename: setup.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Interactive setup script for Addarr.

This script guides users through the initial setup process, helping them:
1. Create necessary directories
2. Configure media services (Radarr, Sonarr, Lidarr)
3. Set up Telegram bot settings
4. Configure access control
5. Generate config.yaml
"""

import os
import sys
from pathlib import Path
from typing import Any, List
import questionary
from colorama import Fore, init
import asyncio
from ruamel.yaml import YAML

from src.setup.prompts import (
    select_services,
    configure_language,
    configure_telegram,
    configure_access_control,
    configure_logging,
    configure_arr_features,
    configure_required_value,
)
from src.setup.service_config import (
    get_default_service_config,
    get_valid_service_config,
)
from src.utils.splash import show_splash_screen
from src.definitions import LOG_PATH
from src.utils.config_handler import config_handler
from src.utils.backup import create_backup

# Initialize colorama
init(autoreset=True)

# Initialize YAML handler
yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)


class SetupWizard:
    def __init__(self):
        """Initialize setup wizard"""
        self.config = config_handler.load_config()
        # Add root directory path
        self.root_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )

    def _save_config(self):
        """Save config while preserving formatting and comments"""
        config_handler.save_config(self.config)

    def _update_config_value(self, path: List[str], value: Any):
        """Update a config value while preserving structure"""
        config_handler.update_value(self.config, path, value)

    def run(self, reset: bool = False):
        """Run the setup wizard synchronously"""
        show_splash_screen()

        if reset:
            self._reset_config()

        print(f"\n{Fore.GREEN}Welcome to the Addarr Setup Wizard! 🧙‍♂️")
        print("This wizard will help you create your configuration file.")

        self._create_directories()

        try:
            # Get or create event loop
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Run async setup
            loop.run_until_complete(self._async_setup())

        except Exception as e:
            print(f"{Fore.RED}Error during setup: {e}")
            sys.exit(1)

        print(f"\n{Fore.GREEN}✅ Setup completed successfully!")
        print(f"{Fore.CYAN}You can now start Addarr with: python run.py\n")

    async def _async_setup(self):
        """Async portion of the setup process"""
        # Configure language first
        self.config["language"] = await configure_language()

        # Select services to configure
        services = await select_services()

        # Configure selected services
        for service in services:
            await self._configure_service(service)

        # Configure Telegram bot
        self.config["telegram"] = await configure_telegram()

        # Configure access control
        access_config = await configure_access_control()
        self.config["security"] = access_config["security"]
        self.config["admins"] = access_config["admins"]
        if "allow_list" in access_config:
            self.config["allow_list"] = access_config["allow_list"]

        # Configure logging
        self.config["logging"] = await configure_logging()

        # Save configuration
        self._save_config()

    def _create_directories(self):
        """Create necessary directories"""
        directories = [
            os.path.dirname(LOG_PATH),
            "translations"
        ]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

    async def _configure_service(self, service: str):
        """Configure a specific service"""
        print(f"\n{Fore.CYAN}Configuring {service.title()} 🔧")

        # Service was selected by user, so it is enabled
        enabled = True

        config = get_default_service_config(service)
        config["enable"] = enabled

        if enabled:
            try:
                # Get validated service configuration
                service_config = await get_valid_service_config(service)
                config.update(service_config)

                if service in ["radarr", "sonarr", "lidarr"]:
                    config["features"] = await configure_arr_features(service)
            except Exception as e:
                print(f"{Fore.RED}Error configuring {service}: {e}")
                print(f"{Fore.YELLOW}Using default configuration for {service}")
                config["enable"] = False

        self.config[service] = config

    async def _configure_required_value(self, service: str, value: str):
        """Configure a single required value for a service"""
        default_config = None
        if service in ['radarr', 'sonarr', 'lidarr']:
            default_config = get_default_service_config(service)
        self.config = await configure_required_value(
            self.config, service, value, default_config=default_config
        )

    def _backup_config(self):
        """Create a backup of the current configuration

        Returns:
            str: Path to backup file if successful, None if failed
        """
        # Create backup and return the backup file path
        return create_backup()

    def _reset_config(self):
        """Reset configuration to default state"""
        try:
            print(f"\n{Fore.YELLOW}⚠️  Warning: This will reset your configuration to default values!")
            print(f"{Fore.CYAN}• A backup of your current config will be created in the backup directory")
            print(f"{Fore.CYAN}• A new configuration file will be created from the example config")
            print(f"{Fore.CYAN}• You will be guided through the setup wizard to configure the bot from scratch")

            # Modified confirmation prompt
            if not questionary.confirm(
                "Do you want to continue?",  # Removed the \n and using questionary's default formatting
                default=False,
                style=questionary.Style([
                    ('question', 'fg:yellow bold'),  # Style the question text
                    ('pointer', 'fg:cyan bold'),     # Style the pointer (>)
                    ('highlighted', 'fg:cyan bold')  # Style the highlighted option
                ])
            ).ask():
                print(f"\n{Fore.YELLOW}Reset cancelled. Your configuration remains unchanged.")
                sys.exit(0)

            # Create backup before resetting
            backup_file = self._backup_config()
            if not backup_file:
                print(f"{Fore.RED}❌ Failed to create backup. Reset cancelled.")
                sys.exit(1)

            # Load example config
            example_path = os.path.join(self.root_dir, "config_example.yaml")
            if not os.path.exists(example_path):
                print(f"{Fore.RED}❌ Config example not found: {example_path}")
                sys.exit(1)

            # Use ruamel.yaml's load method
            with open(example_path, 'r') as f:
                self.config = yaml.load(f)

            # Save the reset config
            self._save_config()

            print(f"\n{Fore.GREEN}✅ Configuration reset to default values")
            print(f"{Fore.CYAN}Starting setup wizard...")

            # Run the setup wizard
            self.run()

        except Exception as e:
            print(f"{Fore.RED}❌ Error resetting configuration: {str(e)}")
            sys.exit(1)

    def configure_services(self):
        """Configure media services and download clients"""
        try:
            show_splash_screen()

            print(f"\n{Fore.GREEN}Welcome to the Addarr Service Configuration! 🧙‍♂️")
            print("This wizard will help you configure your media services and download clients.")

            # Configure media services
            print(f"\n{Fore.CYAN}Media Services Configuration")
            print("=" * 50)

            services = ["radarr", "sonarr", "lidarr"]
            for service in services:
                if questionary.confirm(f"Configure {service.title()}?", default=False).ask():
                    if not self.config.get(service):
                        self.config[service] = {}

                    self.config[service]["enable"] = True

                    # Get service configuration
                    service_config = asyncio.run(get_valid_service_config(service))
                    self.config[service].update(service_config)

            # Configure download clients
            print(f"\n{Fore.CYAN}Download Clients Configuration")
            print("=" * 50)

            # Configure Transmission
            if questionary.confirm("Configure Transmission?", default=False).ask():
                if not self.config.get("transmission"):
                    self.config["transmission"] = {}
                self.config["transmission"]["enable"] = True

                # Configure authentication if needed
                if questionary.confirm("Enable Transmission authentication?", default=False).ask():
                    self.config["transmission"]["authentication"] = True
                    username = questionary.text("Username:").ask()
                    password = questionary.password("Password:").ask()
                    self.config["transmission"]["username"] = username
                    self.config["transmission"]["password"] = password

            # Configure SABnzbd
            if questionary.confirm("Configure SABnzbd?", default=False).ask():
                if not self.config.get("sabnzbd"):
                    self.config["sabnzbd"] = {}
                self.config["sabnzbd"]["enable"] = True

                # Get SABnzbd configuration
                sabnzbd_config = asyncio.run(get_valid_service_config("sabnzbd"))
                self.config["sabnzbd"].update(sabnzbd_config)

            # Save the updated configuration
            self._save_config()

            print(f"\n{Fore.GREEN}✅ Service configuration completed successfully!")
            print(f"{Fore.CYAN}Run 'python run.py' to start the bot.")

        except Exception as e:
            print(f"{Fore.RED}❌ Error configuring services: {str(e)}")
            sys.exit(1)


def main():
    """Run the setup wizard"""
    reset = '--reset' in sys.argv
    wizard = SetupWizard()
    wizard.run(reset)


if __name__ == "__main__":
    main()
