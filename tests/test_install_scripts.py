"""Tests for the Linux install script, the PowerShell installer, the systemd unit and the README install text."""

import os
import re
import shutil
import subprocess

import pytest

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


class TestSudoHandling:
    """Verify install.sh asks for sudo only for packages, so it can run as the current user."""

    def test_system_packages_use_sudo_prefix(self):
        """Every Linux package-manager call in install_system_packages starts with $SUDO."""
        body = function_text(read(INSTALL_SH), "install_system_packages")
        calls = [
            line.strip()
            for line in body.splitlines()
            if re.match(r"\s*(\$SUDO\s+)?(apt-get|dnf|yum|pacman)\b", line)
        ]
        assert len(calls) >= 5
        assert [c for c in calls if not c.startswith("$SUDO ")] == []

    def test_check_sudo_does_not_require_root(self):
        """check_sudo no longer exits for a non-root user or tells them to rerun with sudo."""
        body = function_text(read(INSTALL_SH), "check_sudo")
        assert "sudo $0" not in body
        assert "-ne 0" not in body

    def test_every_package_install_uses_sudo_prefix(self):
        """No executed line calls sudo directly or runs a package manager without $SUDO."""
        offenders = []
        for number, line in enumerate(read(INSTALL_SH).splitlines(), start=1):
            code = line.strip()
            if code.startswith(("echo", "#")):
                continue  # hints for the user, not commands
            for match in re.finditer(r"(\$SUDO\s+|sudo\s+)?\b(apt-get|dnf|yum|pacman)\s+(update|install|-S)", code):
                if match.group(1) != "$SUDO ":
                    offenders.append(f"install.sh:{number}")
        assert offenders == []

    @pytest.mark.parametrize(
        "uid, has_sudo, call_check, returncode, prefix",
        [
            (0, False, True, 0, "[]"),
            (0, True, True, 0, "[]"),
            (1000, True, True, 0, "[sudo]"),
            (1000, False, False, 0, "[sudo]"),
            (1000, False, True, 1, None),
        ],
        ids=[
            "root-without-sudo",
            "root-with-sudo",
            "user-with-sudo",
            "user-without-sudo-nothing-to-install",
            "user-without-sudo-must-install",
        ],
    )
    def test_sudo_prefix_by_user(self, uid, has_sudo, call_check, returncode, prefix):
        """Root needs no prefix. A user needs sudo, and its absence fails only when a package must be installed."""
        script_text = read(INSTALL_SH)
        script = (
            'RED=""; YELLOW=""; NC=""\n'
            f"id() {{ echo {uid}; }}\n"
            + ("sudo() { :; }\n" if has_sudo else "")
            + f'{function_text(script_text, "set_sudo")}\n{function_text(script_text, "check_sudo")}\n'
            + "set_sudo\n"
            + ("check_sudo\n" if call_check else "")
            + 'echo "[$SUDO]"\n'
        )
        # An empty PATH hides a real sudo, so only the stub above can satisfy `command -v sudo`.
        result = subprocess.run(
            [shutil.which("bash"), "-c", script], env={"PATH": ""}, capture_output=True, text=True
        )
        assert result.returncode == returncode
        if prefix is not None:
            assert result.stdout.strip() == prefix

    @pytest.mark.parametrize(
        "anchor",
        ["Installing pip...", "check_git() {", "install_python() {"],
    )
    def test_check_sudo_runs_before_each_install_path(self, anchor):
        """A path that installs a package calls check_sudo before its first $SUDO call."""
        script = read(INSTALL_SH)
        start = script.index(anchor)
        first_install = script.index("$SUDO ", start)
        assert "check_sudo" in script[start:first_install]

    def test_venv_install_checks_sudo_in_each_installing_arm(self):
        """The arch arm installs nothing, so only the three installing arms call check_sudo."""
        body = function_text(read(INSTALL_SH), "install_python_venv")
        assert body.count("check_sudo") == 3


class TestReadmeInstallCommand:
    """Verify the README install command runs as the current user."""

    def test_readme_has_no_sudo_pipe(self):
        """`| sudo bash` sets HOME=/root on Ubuntu, so the install lands under /root."""
        assert "| sudo bash" not in read(README)
