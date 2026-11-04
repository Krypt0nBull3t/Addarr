"""Tests for the Linux install script, the PowerShell installer, the systemd unit and the README install text."""

import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(__file__))
SERVICE = os.path.join(ROOT, "scripts", "addarr.service")
INSTALL_SH = os.path.join(ROOT, "scripts", "install.sh")
INSTALL_PS1 = os.path.join(ROOT, "scripts", "install.ps1")
README = os.path.join(ROOT, "README.md")


def read(path):
    """Return the text of a repo file."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


class TestServiceUnit:
    """Verify the systemd unit lets the bot save its files."""

    def test_service_allows_writes_to_addarr_dir(self):
        """ProtectHome=read-only needs a ReadWritePaths entry for ~/.addarr."""
        lines = [line.strip() for line in read(SERVICE).splitlines()]
        if "ProtectHome=read-only" in lines:
            assert "ReadWritePaths=%h/.addarr" in lines


class TestRepoUrls:
    """Verify the installers and README point to this repo, not upstream."""

    def test_no_upstream_repo_urls(self):
        """No clone, download, wiki or issue URL names cyneric/addarr (case-insensitive).

        Author credit lines name only the profile (github.com/Cyneric), so they pass.
        """
        offenders = []
        for path in (INSTALL_SH, INSTALL_PS1, README):
            for number, line in enumerate(read(path).splitlines(), start=1):
                if "cyneric/addarr" in line.lower():
                    offenders.append(f"{os.path.basename(path)}:{number}")
        assert offenders == []


class TestPythonVersion:
    """Verify the installer and README agree on Python 3.10 as the minimum."""

    def test_install_requires_python_310(self):
        """install.sh and the README name 3.10, not 3.8 or 3.9."""
        script = read(INSTALL_SH)
        readme = read(README)
        assert 'MIN_PYTHON_VERSION="3.10"' in script
        assert "3.8+" not in script
        assert "Python 3.10 or higher" in readme
        assert "Python 3.9 or higher" not in readme


def function_text(script, name):
    """Return the text of a top-level bash function, from `name() {` to its closing `}`."""
    match = re.search(rf"^{name}\(\) \{{\n.*?^\}}\n", script, re.MULTILINE | re.DOTALL)
    assert match, f"{name}() not found"
    return match.group(0)


def run_cleanup(status, with_backup, tmp_path):
    """Run install.sh's cleanup() in bash after a reinstall that left a partial install.

    Returns (install_dir, backup_dir). The backup holds the old config.yaml.
    """
    install_dir = tmp_path / ".addarr"
    backup_dir = tmp_path / ".addarr.backup.1"
    install_dir.mkdir()
    (install_dir / "partial.txt").write_text("new")
    if with_backup:
        backup_dir.mkdir()
        (backup_dir / "config.yaml").write_text("old")
    script = (
        f'YELLOW=""; NC=""; INSTALL_DIR="{install_dir}"; '
        f'BACKUP_DIR="{backup_dir if with_backup else ""}"\n'
        f'{function_text(read(INSTALL_SH), "cleanup")}\ncleanup {status}\n'
    )
    subprocess.run(["bash", "-c", script], check=True, capture_output=True)
    return install_dir, backup_dir


class TestBackupRestore:
    """Verify a failed reinstall puts the old install back."""

    def test_restore_trap_set_before_backup_move(self):
        """The EXIT trap is set before the backup mv, or an early exit loses the old install."""
        lines = read(INSTALL_SH).splitlines()
        trap = next(i for i, line in enumerate(lines) if line.strip() == "trap 'cleanup $?' EXIT")
        move = next(i for i, line in enumerate(lines) if 'mv "$INSTALL_DIR" "$BACKUP_DIR"' in line)
        assert trap < move

    def test_signals_exit_with_non_zero_status(self):
        """Ctrl+C and TERM exit non-zero, so the EXIT trap restores the backup."""
        script = read(INSTALL_SH)
        assert "trap 'exit 130' INT" in script
        assert "trap 'exit 143' TERM" in script

    def test_cleanup_restores_backup_on_failure(self, tmp_path):
        """A non-zero status removes the partial install and restores the old one."""
        install_dir, backup_dir = run_cleanup(1, True, tmp_path)
        assert (install_dir / "config.yaml").read_text() == "old"
        assert not (install_dir / "partial.txt").exists()
        assert not backup_dir.exists()

    def test_cleanup_keeps_new_install_on_success(self, tmp_path):
        """A zero status leaves the new install and the backup alone."""
        install_dir, backup_dir = run_cleanup(0, True, tmp_path)
        assert (install_dir / "partial.txt").exists()
        assert (backup_dir / "config.yaml").exists()

    def test_cleanup_without_backup_does_nothing(self, tmp_path):
        """A failed first install (no backup) must not delete anything."""
        install_dir, _ = run_cleanup(1, False, tmp_path)
        assert (install_dir / "partial.txt").exists()

    def test_clone_failure_is_detected(self):
        """The clone status is git's own (PIPESTATUS[0]), not the progress loop's."""
        script = read(INSTALL_SH)
        start = script.index("Cloning Addarr repository")
        end = script.index("Repository cloned successfully")
        assert "PIPESTATUS[0]" in script[start:end]
