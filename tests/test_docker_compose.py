"""Tests for docker-compose.yml improvements."""

import os
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

    def test_has_resource_limits(self, compose_config):
        """Service should define resource limits."""
        service = compose_config["services"]["addarr"]
        deploy = service.get("deploy", {})
        resources = deploy.get("resources", {})
        limits = resources.get("limits", {})
        assert limits.get("memory") == "256M", "Service must define memory limit of 256M"

    def test_has_backup_volume(self, compose_config):
        """Service should mount backup directory for persistence."""
        service = compose_config["services"]["addarr"]
        volumes = service.get("volumes", [])
        backup_mounts = [v for v in volumes if v.startswith("./backup:")]
        assert len(backup_mounts) > 0, "Service must mount ./backup volume"
