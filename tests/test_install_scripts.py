"""Tests for the Linux install script, the PowerShell installer, the systemd unit and the README install text."""

import os

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
