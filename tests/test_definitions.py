"""
Tests for src/definitions.py -- path and constant definitions.
"""

import os


class TestModuleDoesNotExportDeadCode:
    def test_no_default_settings(self):
        """DEFAULT_SETTINGS was unused dead code and should be removed."""
        from src import definitions
        assert not hasattr(definitions, "DEFAULT_SETTINGS")


class TestPreferencesPath:
    def test_preferences_live_in_data_folder(self):
        """docker-compose.yml persists /app/data, so the file must live there."""
        from src.definitions import DATA_PATH, PREFERENCES_PATH
        assert PREFERENCES_PATH == f"{DATA_PATH}/user_preferences.json".replace("/", os.sep)


class TestIsAdmin:
    def test_is_admin_not_defined_in_definitions(self):
        """The shared check is src.utils.helpers.is_admin; no second copy."""
        from src import definitions

        assert not hasattr(definitions, "is_admin")
