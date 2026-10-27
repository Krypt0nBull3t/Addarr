"""Tests for src/utils/backup.py"""

from unittest.mock import patch

from src.utils.backup import create_backup


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

    def test_create_backup_exception(self, tmp_path):
        """Returns None when an exception occurs during backup."""
        source = tmp_path / "config.yaml"
        source.write_text("content")

        with (
            patch("src.utils.backup.CONFIG_PATH", str(source)),
            patch("shutil.copy2", side_effect=PermissionError("denied")),
        ):
            result = create_backup(str(source))

        assert result is None
