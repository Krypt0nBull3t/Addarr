"""Tests for docker-compose.yml improvements."""

import os
import subprocess
import time

import pytest
import yaml

COMPOSE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "docker-compose.yml"
)


@pytest.fixture
def compose_config():
    """Load docker-compose.yml as parsed YAML."""
    with open(COMPOSE_PATH, "r") as f:
        return yaml.safe_load(f)


class TestDockerCompose:
    """Verify docker-compose.yml best practices."""

    def test_has_healthcheck(self, compose_config):
        """Service should define a healthcheck."""
        service = compose_config["services"]["addarr"]
        assert "healthcheck" in service, "Service must define a healthcheck"

    @staticmethod
    def _healthcheck_command(compose_config):
        test = compose_config["services"]["addarr"]["healthcheck"]["test"]
        assert test[0] == "CMD-SHELL"
        return test[1].replace("$$", "$")  # compose turns $$ into $

    def test_healthcheck_checks_heartbeat_age(self, compose_config):
        """The healthcheck reads the heartbeat file age, not the process list."""
        command = self._healthcheck_command(compose_config)
        assert "stat -c %Y" in command
        assert "-lt 60" in command
        assert "pgrep" not in command

    def test_healthcheck_command_behaviour(self, compose_config, tmp_path):
        """Healthy for a fresh file; unhealthy for an old or a missing file."""
        command = self._healthcheck_command(compose_config)
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

    def test_has_resource_limits(self, compose_config):
        """Service should define resource limits."""
        service = compose_config["services"]["addarr"]
        deploy = service.get("deploy", {})
        resources = deploy.get("resources", {})
        limits = resources.get("limits", {})
        assert limits.get("memory") == "256M", "Service must define memory limit of 256M"

    def test_logging_is_capped(self, compose_config):
        """Console logs rotate so the log file cannot grow without limit."""
        logging = compose_config["services"]["addarr"]["logging"]
        assert logging["driver"] == "json-file"
        assert logging["options"]["max-size"] == "10m"
        assert logging["options"]["max-file"] == "3"

    def test_has_backup_volume(self, compose_config):
        """Service should mount backup directory for persistence."""
        service = compose_config["services"]["addarr"]
        volumes = service.get("volumes", [])
        assert "./backup:/app/backup:rw" in volumes, (
            "Service must mount ./backup:/app/backup:rw volume"
        )

    def test_backup_volume_is_read_write(self, compose_config):
        """Backup volume should be mounted read-write."""
        service = compose_config["services"]["addarr"]
        volumes = service.get("volumes", [])
        backup_mounts = [v for v in volumes if v.startswith("./backup:")]
        assert any(":rw" in v for v in backup_mounts), "Backup volume must be :rw"

    def test_has_pythonpath_env(self, compose_config):
        """Service should set PYTHONPATH environment variable."""
        service = compose_config["services"]["addarr"]
        env = service.get("environment", [])
        assert any("PYTHONPATH=/app" in e for e in env), "PYTHONPATH=/app must be set"

    def test_config_volume_is_writable(self, compose_config):
        """/auth and settings changes save config.yaml, so it must not be :ro."""
        volumes = compose_config["services"]["addarr"].get("volumes", [])
        config_mounts = [v for v in volumes if v.startswith("./config.yaml:")]
        assert config_mounts, "config.yaml must be mounted"
        assert not any(v.endswith(":ro") for v in config_mounts)

    def test_data_folder_is_a_named_volume(self, compose_config):
        """user_preferences.json lives in /app/data and must survive recreates.

        A named volume (not a ./data bind mount) starts with the image's
        ownership, so the non-root user can write it on a fresh install.
        """
        volumes = compose_config["services"]["addarr"].get("volumes", [])
        data_mounts = [v for v in volumes if ":/app/data" in v]
        assert len(data_mounts) == 1
        name = data_mounts[0].split(":")[0]
        assert not name.startswith((".", "/")), "must be a named volume"
        assert name in compose_config.get("volumes", {})
