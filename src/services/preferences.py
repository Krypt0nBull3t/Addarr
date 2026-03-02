"""
Filename: preferences.py
Author: Addarr Contributors
Created Date: 2026-03-02
Description: Per-user preferences service.

Persists user preferences (e.g. view mode) to a JSON file.
Singleton pattern matching TranslationService.
"""

import json
from typing import Any, Optional

from src.definitions import PREFERENCES_PATH
from src.utils.logger import get_logger

logger = get_logger("addarr.preferences")


class PreferencesService:
    """Service for managing per-user preferences."""

    _instance = None
    _preferences: dict = {}

    def __new__(cls):
        """Ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super(PreferencesService, cls).__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        """Load preferences from disk."""
        try:
            with open(PREFERENCES_PATH, "r") as f:
                self._preferences = json.load(f)
        except FileNotFoundError:
            self._preferences = {}
        except (json.JSONDecodeError, ValueError):
            logger.warning(
                "Corrupt preferences file, resetting to empty"
            )
            self._preferences = {}

    def _save(self):
        """Persist preferences to disk."""
        with open(PREFERENCES_PATH, "w") as f:
            json.dump(self._preferences, f, indent=2)

    def get_preference(
        self, user_id: str, key: str, default: Optional[Any] = None
    ) -> Any:
        """Get a preference value for a user."""
        return self._preferences.get(str(user_id), {}).get(key, default)

    def set_preference(self, user_id: str, key: str, value: Any):
        """Set a preference value for a user and persist."""
        uid = str(user_id)
        if uid not in self._preferences:
            self._preferences[uid] = {}
        self._preferences[uid][key] = value
        self._save()

    def get_view_mode(self, user_id: str) -> str:
        """Get user's preferred view mode. Defaults to 'card'."""
        return self.get_preference(str(user_id), "view_mode", default="card")

    def toggle_view_mode(self, user_id: str) -> str:
        """Toggle between 'card' and 'list'. Returns the new mode."""
        current = self.get_view_mode(str(user_id))
        new_mode = "list" if current == "card" else "card"
        self.set_preference(str(user_id), "view_mode", new_mode)
        return new_mode
