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


class TestHeartbeatFile:
    @staticmethod
    def _heartbeat_in_fresh_process(env_value):
        """Import src.definitions in a new process so the env var is read at import."""
        import subprocess
        import sys

        env = {k: v for k, v in os.environ.items() if k != "ADDARR_HEARTBEAT_FILE"}
        if env_value is not None:
            env["ADDARR_HEARTBEAT_FILE"] = env_value
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        out = subprocess.run(
            [sys.executable, "-c",
             "from src.definitions import HEARTBEAT_FILE; print(HEARTBEAT_FILE)"],
            cwd=root, env=env, capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()

    def test_default_is_in_the_temp_directory(self):
        import tempfile
        assert self._heartbeat_in_fresh_process(None) == os.path.join(
            tempfile.gettempdir(), "addarr-heartbeat"
        )

    def test_env_overrides_default(self):
        assert self._heartbeat_in_fresh_process("/data/hb") == "/data/hb"


class TestIsAdmin:
    def test_is_admin_not_defined_in_definitions(self):
        """The shared check is src.utils.helpers.is_admin; no second copy."""
        from src import definitions

        assert not hasattr(definitions, "is_admin")
