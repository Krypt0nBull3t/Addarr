"""
Tests for src/definitions.py -- path definitions and helper functions.

Uses tmp_path + monkeypatch to avoid touching real config files.
"""

import os

import pytest
import yaml


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


class TestLoadConfig:
    def test_load_config_success(self, tmp_path, monkeypatch):
        config_data = {"admins": [111], "language": "en-us"}
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config_data))
        monkeypatch.chdir(tmp_path)

        from src.definitions import load_config

        result = load_config()
        assert result["admins"] == [111]
        assert result["language"] == "en-us"

    def test_load_config_file_not_found(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        from src.definitions import load_config

        with pytest.raises(FileNotFoundError, match="config.yaml not found"):
            load_config()


class TestGetAdmins:
    def test_get_admins(self, tmp_path, monkeypatch):
        config_data = {"admins": [111, 222]}
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config_data))
        monkeypatch.chdir(tmp_path)

        from src.definitions import get_admins

        assert get_admins() == [111, 222]

    def test_get_admins_empty(self, tmp_path, monkeypatch):
        config_data = {"language": "en-us"}
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config_data))
        monkeypatch.chdir(tmp_path)

        from src.definitions import get_admins

        assert get_admins() == []


class TestGetAllowedChats:
    def test_get_allowed_chats(self, tmp_path, monkeypatch):
        config_data = {"chat_id": [555, 666]}
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config_data))
        monkeypatch.chdir(tmp_path)

        from src.definitions import get_allowed_chats

        assert get_allowed_chats() == [555, 666]


class TestIsAdmin:
    def test_is_admin_not_defined_in_definitions(self):
        """The shared check is src.utils.helpers.is_admin; no second copy."""
        from src import definitions

        assert not hasattr(definitions, "is_admin")


class TestIsAllowedChat:
    def test_is_allowed_chat_true(self, tmp_path, monkeypatch):
        config_data = {"chat_id": [555]}
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config_data))
        monkeypatch.chdir(tmp_path)

        from src.definitions import is_allowed_chat

        assert is_allowed_chat(555) is True

    def test_is_allowed_chat_false(self, tmp_path, monkeypatch):
        config_data = {"chat_id": [555]}
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config_data))
        monkeypatch.chdir(tmp_path)

        from src.definitions import is_allowed_chat

        assert is_allowed_chat(999) is False
