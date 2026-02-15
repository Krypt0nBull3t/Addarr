"""Tests for Dockerfile security and health improvements."""

import os
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
        user_lines = [l for l in dockerfile_lines if l.strip().startswith("USER ")]
        assert len(user_lines) > 0, "Dockerfile must contain a USER directive"
        # The USER should not be root
        last_user = user_lines[-1].strip()
        assert "root" not in last_user.lower(), "USER must not be root"

    def test_has_healthcheck(self, dockerfile_lines):
        """Container should declare a HEALTHCHECK."""
        healthcheck_lines = [
            l for l in dockerfile_lines if l.strip().startswith("HEALTHCHECK")
        ]
        assert len(healthcheck_lines) > 0, "Dockerfile must contain a HEALTHCHECK"

    def test_has_stopsignal(self, dockerfile_lines):
        """Container should handle graceful shutdown."""
        stopsignal_lines = [
            l for l in dockerfile_lines if l.strip().startswith("STOPSIGNAL")
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
            l for l in dockerfile_lines if l.strip().startswith("ENTRYPOINT")
        ]
        assert len(entrypoint_lines) > 0, "Dockerfile must have ENTRYPOINT"
        assert "/app/run.py" in entrypoint_lines[-1], (
            "ENTRYPOINT should use /app/run.py"
        )
