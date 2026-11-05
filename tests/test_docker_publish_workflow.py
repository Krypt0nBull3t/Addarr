"""Tests for .github/workflows/docker-hub-push.yml: the image gets a version tag."""

import ast
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "docker-hub-push.yml"

needs_bash = pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")


@pytest.fixture
def steps():
    """The steps of the buildx job."""
    return yaml.safe_load(WORKFLOW.read_text())["jobs"]["buildx"]["steps"]


@pytest.fixture
def build_step(steps):
    return next(
        s for s in steps if s.get("uses", "").startswith("docker/build-push-action")
    )


@pytest.fixture
def version_step(steps):
    return next(s for s in steps if s.get("name") == "Read version")


def _run_step(step, cwd, github_env):
    return subprocess.run(
        ["bash", "-e", "-c", step["run"]],  # the runner's default shell is bash -e
        cwd=cwd,
        env={"PATH": "/usr/bin:/bin", "GITHUB_ENV": str(github_env)},
        capture_output=True,
        text=True,
    )


def _init_version():
    """__version__ in src/__init__.py, read with ast (conftest injects the import)."""
    tree = ast.parse((ROOT / "src" / "__init__.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and node.targets[0].id == "__version__":
            return node.value.value
    raise AssertionError("no __version__ in src/__init__.py")


def test_tags_hold_latest_and_version_tag(build_step):
    """The image is pushed as :latest and as a version tag."""
    tags = build_step["with"]["tags"].splitlines()

    assert "${{ env.REPO }}:latest" in tags
    assert "${{ env.REPO }}:${{ env.VERSION }}" in tags


def test_version_step_runs_before_build(steps, version_step, build_step):
    """VERSION is set before the build step reads it."""
    assert steps.index(version_step) < steps.index(build_step)


@needs_bash
def test_version_step_writes_version_from_init(version_step, tmp_path):
    """The step puts __version__ from src/__init__.py into GITHUB_ENV."""
    github_env = tmp_path / "github_env"

    result = _run_step(version_step, ROOT, github_env)

    assert result.returncode == 0, result.stderr
    assert github_env.read_text() == f"VERSION={_init_version()}\n"


@needs_bash
def test_version_step_fails_without_version(version_step, tmp_path):
    """No version means a failed job, never an image tagged with an empty version."""
    github_env = tmp_path / "github_env"
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "__init__.py").write_text("__author__ = 'x'\n")

    result = _run_step(version_step, tmp_path, github_env)

    assert result.returncode != 0
    assert not github_env.exists() or github_env.read_text() == ""


def test_login_still_uses_both_secrets(steps):
    """The Docker Hub login keeps reading the two repo secrets."""
    login = next(s for s in steps if s.get("uses", "").startswith("docker/login-action"))

    assert login["with"]["username"] == "${{ secrets.DOCKER_HUB_USERNAME }}"
    assert login["with"]["password"] == "${{ secrets.DOCKER_HUB_ACCESS_TOKEN }}"
