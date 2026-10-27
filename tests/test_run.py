"""Tests for run.py, the command line entry point."""

import os
import subprocess
import sys

import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Runs in a fresh interpreter: the test session already holds a mocked config
WIZARD_SCRIPT = """
import sys
from unittest.mock import patch

import run

sys.argv = ["run.py", sys.argv[1]]
with (
    patch("run.prerun_checker.run_checks", return_value=True),
    patch("src.setup.SetupWizard") as wizard,
):
    run.main()
assert wizard.called, "wizard did not run"
loaded = "src.config.settings" in sys.modules
print("CONFIG LOADED" if loaded else "CONFIG NOT LOADED")
"""


@pytest.mark.parametrize("flag", ["--setup", "--configure", "--reset"])
def test_wizard_flags_do_not_load_existing_config(flag):
    """The wizard must start even when config.yaml is broken."""
    result = subprocess.run(
        [sys.executable, "-c", WIZARD_SCRIPT, flag],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert "CONFIG NOT LOADED" in result.stdout, result.stdout + result.stderr
