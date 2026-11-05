"""Tests for Dockerfile security and health improvements."""

import os
import re
import subprocess
import time

import pytest

DOCKERFILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "Dockerfile"
)


@pytest.fixture
def dockerfile_lines():
    """Read Dockerfile lines for inspection."""
    with open(DOCKERFILE_PATH, "r") as f:
        return f.readlines()


class TestDockerfileSecurity:
    """Verify Dockerfile follows security best practices."""

    def test_runs_as_non_root_user(self, dockerfile_lines):
        """Container should not run as root."""
        user_lines = [line for line in dockerfile_lines if line.strip().startswith("USER ")]
        assert len(user_lines) > 0, "Dockerfile must contain a USER directive"
        # The USER should not be root
        last_user = user_lines[-1].strip()
        assert "root" not in last_user.lower(), "USER must not be root"

    def test_has_healthcheck(self, dockerfile_lines):
        """Container should declare a HEALTHCHECK."""
        healthcheck_lines = [
            line for line in dockerfile_lines if line.strip().startswith("HEALTHCHECK")
        ]
        assert len(healthcheck_lines) > 0, "Dockerfile must contain a HEALTHCHECK"

    @staticmethod
    def _healthcheck_command(dockerfile_lines):
        """The command of the HEALTHCHECK instruction (continuation lines joined)."""
        text = "".join(dockerfile_lines).replace("\\\n", " ")
        match = re.search(r"^HEALTHCHECK\s.*?\bCMD\s+(.*)$", text, re.MULTILINE)
        assert match, "HEALTHCHECK must have a CMD"
        return match.group(1).strip()

    def test_healthcheck_checks_heartbeat_age(self, dockerfile_lines):
        """The healthcheck reads the heartbeat file age, not the process list."""
        command = self._healthcheck_command(dockerfile_lines)
        assert "stat -c %Y" in command
        assert "-lt 60" in command
        assert "pgrep" not in command

    def test_healthcheck_command_behaviour(self, dockerfile_lines, tmp_path):
        """Healthy for a fresh file; unhealthy for an old or a missing file."""
        command = self._healthcheck_command(dockerfile_lines)
        heartbeat = tmp_path / "heartbeat"
        env = {**os.environ, "ADDARR_HEARTBEAT_FILE": str(heartbeat)}

        def run():
            return subprocess.run(["sh", "-c", command], env=env).returncode

        assert run() == 1  # missing
        heartbeat.touch()
        assert run() == 0  # fresh
        old = time.time() - 120
        os.utime(heartbeat, (old, old))
        assert run() == 1  # older than 60 s

    def test_has_stopsignal(self, dockerfile_lines):
        """Container should handle graceful shutdown."""
        stopsignal_lines = [
            line for line in dockerfile_lines if line.strip().startswith("STOPSIGNAL")
        ]
        assert len(stopsignal_lines) > 0, "Dockerfile must contain a STOPSIGNAL"

    def test_no_typo_in_comments(self, dockerfile_lines):
        """Comments should not contain the known typo."""
        full_text = "".join(dockerfile_lines)
        assert "Install ans build" not in full_text, (
            "Typo 'Install ans build' should be 'Install and build'"
        )

    def test_entrypoint_uses_app_path(self, dockerfile_lines):
        """ENTRYPOINT should reference /app/run.py, not /run.py."""
        entrypoint_lines = [
            line for line in dockerfile_lines if line.strip().startswith("ENTRYPOINT")
        ]
        assert len(entrypoint_lines) > 0, "Dockerfile must have ENTRYPOINT"
        assert "/app/run.py" in entrypoint_lines[-1], (
            "ENTRYPOINT should use /app/run.py"
        )

    def test_creates_data_dir_for_named_volume(self, dockerfile_lines):
        """/app/data must exist in the image, owned by the app user.

        Docker copies that ownership into a new named volume.
        """
        full_text = "".join(dockerfile_lines)
        assert "/app/data" in full_text
