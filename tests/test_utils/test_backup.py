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


def _stamps(count):
    """`count` consecutive datetimes, one second apart."""
    import datetime

    return [datetime.datetime(2026, 1, 1, 0, 0, i) for i in range(count)]


def _make_backups(source, count):
    """Run create_backup `count` times with one-second-apart timestamps."""
    with patch("src.utils.backup.datetime") as mock_dt:
        mock_dt.datetime.now.side_effect = _stamps(count)
        return [create_backup(str(source)) for _ in range(count)]


class TestBackupRetentionAndMode:
    """Backups keep their newest 10 and stay private (F013)."""

    def test_backups_are_pruned_to_newest_ten(self, tmp_path):
        """11 backups leave the newest 10; the oldest is gone."""
        source = tmp_path / "config.yaml"
        source.write_text("telegram:\n  token: test\n")

        _make_backups(source, 11)

        names = sorted(p.name for p in (tmp_path / "backup").glob("config_*.yaml"))
        assert len(names) == 10
        assert "config_20260101_000000.yaml" not in names
        assert "config_20260101_000010.yaml" in names

    def test_backups_are_owner_only(self, tmp_path):
        """A backup has mode 0o600 even when the source is 0o644."""
        import os
        import stat

        source = tmp_path / "config.yaml"
        source.write_text("telegram:\n  token: test\n")
        os.chmod(source, 0o644)

        result = _make_backups(source, 1)[0]

        assert stat.S_IMODE(os.stat(result).st_mode) == 0o600

    def test_new_backup_dir_is_owner_only(self, tmp_path):
        """A newly created backup/ folder has mode 0o700."""
        import os
        import stat

        source = tmp_path / "config.yaml"
        source.write_text("x: 1\n")

        _make_backups(source, 1)

        mode = stat.S_IMODE(os.stat(tmp_path / "backup").st_mode)
        assert mode == 0o700

    def test_prune_keeps_unrelated_files(self, tmp_path):
        """Prune deletes only config_<date>_<time>.yaml files."""
        source = tmp_path / "config.yaml"
        source.write_text("x: 1\n")
        backup_dir = tmp_path / "backup"
        backup_dir.mkdir()
        other = backup_dir / "config_example_20260101_000000.yaml"
        notes = backup_dir / "notes.txt"
        other.write_text("other")
        notes.write_text("notes")

        _make_backups(source, 11)

        assert other.exists()
        assert notes.exists()

    def test_fewer_than_ten_backups_delete_nothing(self, tmp_path):
        """Nothing is pruned below the limit."""
        source = tmp_path / "config.yaml"
        source.write_text("x: 1\n")

        _make_backups(source, 3)

        assert len(list((tmp_path / "backup").glob("config_*.yaml"))) == 3


def test_dockerignore_lists_backup_dir():
    """backup/ holds secrets, so the Docker build must not copy it."""
    from pathlib import Path

    text = (Path(__file__).parents[2] / ".dockerignore").read_text()

    assert "backup/" in text.splitlines()
