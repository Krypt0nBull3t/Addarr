"""
Tests for src/definitions.py -- path definitions and helper functions.

Uses tmp_path + monkeypatch to avoid touching real config files.
"""

import pytest
import yaml


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


class TestGetAllowedUsers:
    def test_get_allowed_users(self, tmp_path, monkeypatch):
        config_data = {"allow_list": [333, 444]}
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config_data))
        monkeypatch.chdir(tmp_path)

        from src.definitions import get_allowed_users

        assert get_allowed_users() == [333, 444]


class TestGetAllowedChats:
    def test_get_allowed_chats(self, tmp_path, monkeypatch):
        config_data = {"chat_id": [555, 666]}
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config_data))
        monkeypatch.chdir(tmp_path)

        from src.definitions import get_allowed_chats

        assert get_allowed_chats() == [555, 666]


class TestIsAdmin:
    def test_is_admin_true(self, tmp_path, monkeypatch):
        config_data = {"admins": [111, 222]}
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config_data))
        monkeypatch.chdir(tmp_path)

        from src.definitions import is_admin

        assert is_admin(111) is True

    def test_is_admin_false(self, tmp_path, monkeypatch):
        config_data = {"admins": [111]}
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config_data))
        monkeypatch.chdir(tmp_path)

        from src.definitions import is_admin

        assert is_admin(999) is False


class TestIsAllowedUser:
    def test_allowlist_disabled(self, tmp_path, monkeypatch):
        config_data = {
            "security": {"enableAllowlist": False},
            "allow_list": [111],
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config_data))
        monkeypatch.chdir(tmp_path)

        from src.definitions import is_allowed_user

        # When allowlist is disabled, all users are allowed
        assert is_allowed_user(999) is True

    def test_allowlist_enabled_allowed(self, tmp_path, monkeypatch):
        config_data = {
            "security": {"enableAllowlist": True},
            "allow_list": [111, 222],
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config_data))
        monkeypatch.chdir(tmp_path)

        from src.definitions import is_allowed_user

        assert is_allowed_user(111) is True

    def test_allowlist_enabled_not_allowed(self, tmp_path, monkeypatch):
        config_data = {
            "security": {"enableAllowlist": True},
            "allow_list": [111],
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config_data))
        monkeypatch.chdir(tmp_path)

        from src.definitions import is_allowed_user

        assert is_allowed_user(999) is False


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
