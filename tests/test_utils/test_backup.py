"""Tests for src/utils/backup.py"""

from unittest.mock import patch

from src.utils.backup import create_backup, restore_backup, list_backups


class TestCreateBackup:
    """Tests for create_backup."""

    def test_create_backup_success(self, tmp_path):
        """Creates a backup file and returns its path."""
        source = tmp_path / "config.yaml"
        source.write_text("telegram:\n  token: test\n")

        with patch("src.utils.backup.CONFIG_PATH", str(source)):
            result = create_backup(str(source))

        assert result is not None
        assert result.endswith(".yaml")

        # Verify the backup file exists and matches the source
        from pathlib import Path

        backup_file = Path(result)
        assert backup_file.exists()
        assert backup_file.read_text() == "telegram:\n  token: test\n"

    def test_create_backup_no_source(self, tmp_path):
        """Returns None when the source file does not exist."""
        missing = str(tmp_path / "nonexistent.yaml")

        with patch("src.utils.backup.CONFIG_PATH", missing):
            result = create_backup(missing)

        assert result is None


class TestRestoreBackup:
    """Tests for restore_backup."""

    def test_restore_backup_success(self, tmp_path):
        """Restores a backup to CONFIG_PATH and returns True."""
        # Set up a current config
        config_file = tmp_path / "config.yaml"
        config_file.write_text("current: true\n")

        # Set up a backup file
        backup_file = tmp_path / "backup_config.yaml"
        backup_file.write_text("restored: true\n")

        with patch("src.utils.backup.CONFIG_PATH", str(config_file)):
            result = restore_backup(str(backup_file))

        assert result is True
        assert config_file.read_text() == "restored: true\n"

    def test_restore_backup_no_file(self, tmp_path):
        """Returns False when the backup file does not exist."""
        missing = str(tmp_path / "nonexistent_backup.yaml")
        config_file = str(tmp_path / "config.yaml")

        with patch("src.utils.backup.CONFIG_PATH", config_file):
            result = restore_backup(missing)

        assert result is False


class TestListBackups:
    """Tests for list_backups."""

    def test_list_backups_empty(self, tmp_path):
        """Returns an empty list when no backup directory exists."""
        config_file = tmp_path / "config.yaml"
        with patch("src.utils.backup.CONFIG_PATH", str(config_file)):
            result = list_backups()

        assert result == []

    def test_list_backups_sorted(self, tmp_path):
        """Returns backup filenames sorted in reverse order."""
        # Create a backup directory next to the config path
        backup_dir = tmp_path / "backup"
        backup_dir.mkdir()

        # Create some backup files
        (backup_dir / "config_20240101_120000.yaml").write_text("a")
        (backup_dir / "config_20240201_120000.yaml").write_text("b")
        (backup_dir / "config_20240301_120000.yaml").write_text("c")
        # Add a non-yaml file that should be excluded
        (backup_dir / "notes.txt").write_text("ignore me")

        config_file = tmp_path / "config.yaml"
        with patch("src.utils.backup.CONFIG_PATH", str(config_file)):
            result = list_backups()

        assert len(result) == 3
        # Verify reverse-sorted order (newest first)
        assert result[0] == "config_20240301_120000.yaml"
        assert result[1] == "config_20240201_120000.yaml"
        assert result[2] == "config_20240101_120000.yaml"
