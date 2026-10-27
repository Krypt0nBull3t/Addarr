"""
Filename: backup.py
Author: Christian Blank (https://github.com/Cyneric)
Created Date: 2024-11-08
Description: Backup utility module.

This module provides backup functionality for Addarr configuration files.
"""

import os
import shutil
import datetime
from pathlib import Path
from colorama import Fore
from typing import Optional

from src.definitions import CONFIG_PATH


def create_backup(source_path: str = CONFIG_PATH) -> Optional[str]:
    """Create a backup of a configuration file

    Args:
        source_path: Path to the file to backup (default: config.yaml)

    Returns:
        Optional[str]: Path to backup file if successful, None otherwise
    """
    if os.path.exists(source_path):
        try:
            # Create backup directory if it doesn't exist
            backup_dir = os.path.join(os.path.dirname(source_path), "backup")
            Path(backup_dir).mkdir(parents=True, exist_ok=True)

            # Generate timestamp for backup file
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.basename(source_path)
            backup_file = os.path.join(backup_dir, f"{filename.rsplit('.', 1)[0]}_{timestamp}.yaml")

            # Copy file to backup directory
            shutil.copy2(source_path, backup_file)

            # Only print once
            print(f"{Fore.GREEN}✅ Configuration backed up to: {backup_file}")

            return backup_file

        except Exception as e:
            error_msg = f"Error creating backup: {str(e)}"
            print(f"{Fore.RED}❌ {error_msg}")
            return None
    else:
        print(f"{Fore.YELLOW}⚠️ No configuration file found to backup.")
        return None
