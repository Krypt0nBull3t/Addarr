"""Tests for src/utils/config_handler.py"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.utils.config_handler import ConfigHandler, config_handler


@pytest.fixture
def colors():
    """Mock colors object with Fore attributes."""
    c = MagicMock()
    c.Fore.GREEN = ""
    c.Fore.RED = ""
    c.Fore.YELLOW = ""
    return c


@pytest.fixture
def handler(tmp_path, colors):
    """ConfigHandler wired to tmp_path for safe file I/O."""
    h = ConfigHandler(colors)
    h.root_dir = str(tmp_path)
    h.config_path = str(tmp_path / "config.yaml")
    h.config_example_path = str(tmp_path / "config_example.yaml")
    return h


@pytest.fixture
def example_yaml(tmp_path):
    """Create a config_example.yaml in tmp_path."""
    path = tmp_path / "config_example.yaml"
    path.write_text("telegram:\n  token: ''\n", encoding="utf-8")
    return path


@pytest.fixture
def config_yaml(tmp_path):
    """Create a config.yaml in tmp_path."""
    path = tmp_path / "config.yaml"
    path.write_text("telegram:\n  token: 'old-token'\n", encoding="utf-8")
    return path


# ---- __init__ ----


class TestConfigHandlerInit:
    """Tests for ConfigHandler.__init__."""

    def test_sets_colors(self, colors):
        """Stores the colors object."""
        h = ConfigHandler(colors)
        assert h.colors is colors

    def test_sets_root_dir(self):
        """root_dir points to the project root (3 levels up from this file)."""
        h = ConfigHandler(None)
        assert os.path.isabs(h.root_dir)

    def test_sets_config_paths(self):
        """config_path and config_example_path are under root_dir."""
        h = ConfigHandler(None)
        assert h.config_path.endswith("config.yaml")
        assert h.config_example_path.endswith("config_example.yaml")

    def test_none_colors_accepted(self):
        """colors=None is valid (used by global instance)."""
        h = ConfigHandler(None)
        assert h.colors is None


# ---- create_from_example ----


class TestCreateFromExample:
    """Tests for create_from_example."""

    def test_copies_example_to_config(self, handler, example_yaml):
        """Copies config_example.yaml to config.yaml."""
        result = handler.create_from_example()
        assert result is True
        assert os.path.exists(handler.config_path)
        content = Path(handler.config_path).read_text(encoding="utf-8")
        assert "telegram" in content

    def test_backs_up_existing_config(self, handler, example_yaml, config_yaml):
        """Creates backup when config.yaml already exists."""
        result = handler.create_from_example()
        assert result is True
        backup_dir = os.path.join(handler.root_dir, "backup")
        assert os.path.isdir(backup_dir)
        backups = os.listdir(backup_dir)
        assert len(backups) == 1
        assert backups[0].startswith("config_")

    def test_returns_false_on_error(self, handler, capsys):
        """Returns False when example file doesn't exist."""
        # example_yaml fixture not created — copy will fail
        result = handler.create_from_example()
        assert result is False
        captured = capsys.readouterr()
        assert "Error creating config" in captured.out


# ---- load_config ----


class TestLoadConfig:
    """Tests for load_config."""

    def test_loads_valid_yaml(self, handler, config_yaml):
        """Returns parsed dict from valid YAML file."""
        result = handler.load_config()
        assert isinstance(result, dict)
        assert "telegram" in result
        assert result["telegram"]["token"] == "old-token"

    def test_returns_empty_dict_on_missing_file(self, handler, capsys):
        """Returns {} when config file doesn't exist."""
        result = handler.load_config()
        assert result == {}
        captured = capsys.readouterr()
        assert "Error loading config" in captured.out

    def test_returns_empty_dict_on_empty_file(self, handler, tmp_path):
        """An empty config.yaml loads as {} so --setup can repair it."""
        Path(handler.config_path).write_text("", encoding="utf-8")
        assert handler.load_config() == {}

    def test_returns_empty_dict_on_invalid_yaml(self, handler, tmp_path, capsys):
        """Returns {} on malformed YAML."""
        bad = tmp_path / "config.yaml"
        bad.write_text("{{invalid yaml: [", encoding="utf-8")
        result = handler.load_config()
        assert result == {}


# ---- save_config ----


class TestSaveConfig:
    """Tests for save_config."""

    def test_saves_config_to_file(self, handler, config_yaml):
        """Writes config dict as YAML to config_path."""
        data = {"telegram": {"token": "new-token"}}
        result = handler.save_config(data)
        assert result is True
        loaded = handler.load_config()
        assert loaded["telegram"]["token"] == "new-token"

    def test_creates_backup_before_save(self, handler, config_yaml):
        """Backs up existing config before overwriting."""
        handler.save_config({"key": "val"})
        backup_dir = os.path.join(handler.root_dir, "backup")
        assert os.path.isdir(backup_dir)
        assert len(os.listdir(backup_dir)) == 1

    def test_returns_false_on_error(self, handler, config_yaml, capsys):
        """Returns False when write fails."""
        with patch("builtins.open", side_effect=PermissionError("denied")):
            result = handler.save_config({"key": "val"})
        assert result is False
        captured = capsys.readouterr()
        assert "Error saving configuration" in captured.out


# ---- update_value ----


class TestUpdateValue:
    """Tests for update_value."""

    def test_single_key(self):
        """Updates a top-level key."""
        config = {"language": "en-us"}
        ConfigHandler.update_value(None, config, ["language"], "de-de")
        assert config["language"] == "de-de"

    def test_nested_keys(self):
        """Updates a deeply nested key."""
        config = {"telegram": {"token": "old"}}
        ConfigHandler.update_value(None, config, ["telegram", "token"], "new")
        assert config["telegram"]["token"] == "new"

    def test_creates_intermediate_keys(self):
        """Creates missing intermediate dicts via setdefault."""
        config = {}
        ConfigHandler.update_value(
            None, config, ["radarr", "server", "addr"], "localhost"
        )
        assert config["radarr"]["server"]["addr"] == "localhost"

    def test_preserves_sibling_keys(self):
        """Updating one nested key doesn't affect siblings."""
        config = {"telegram": {"token": "abc", "password": "secret"}}
        ConfigHandler.update_value(
            None, config, ["telegram", "token"], "xyz"
        )
        assert config["telegram"]["token"] == "xyz"
        assert config["telegram"]["password"] == "secret"


# ---- global config_handler instance ----


class TestGlobalInstance:
    """Tests for the module-level config_handler."""

    def test_is_config_handler_instance(self):
        """Global instance is a ConfigHandler."""
        assert isinstance(config_handler, ConfigHandler)

    def test_global_instance_has_colors(self):
        """F021: the global instance has real colors without prerun."""
        assert config_handler.colors is not None
        assert hasattr(config_handler.colors.Fore, "GREEN")

    def test_create_from_example_without_config_returns_true(
        self, tmp_path, example_yaml, monkeypatch
    ):
        """F021: create_from_example works on the global instance, no config.yaml."""
        monkeypatch.setattr(config_handler, "config_path", str(tmp_path / "config.yaml"))
        monkeypatch.setattr(config_handler, "config_example_path", str(example_yaml))
        assert config_handler.create_from_example() is True
        assert (tmp_path / "config.yaml").exists()

    def test_load_config_missing_file_on_global_instance(
        self, tmp_path, monkeypatch
    ):
        """F021: the load error path prints with real colors."""
        monkeypatch.setattr(config_handler, "config_path", str(tmp_path / "none.yaml"))
        assert config_handler.load_config() == {}
