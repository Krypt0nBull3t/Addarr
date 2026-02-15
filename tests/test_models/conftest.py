"""
conftest.py for test_models -- Ensure src.models is importable.

The root conftest.py injects a fake 'src' module into sys.modules to
intercept src.config.settings. This prevents normal import of src.models.
We fix that here by loading the real models package via importlib from
disk and wiring it into the fake 'src' module.

We also override the autouse fixtures from the root conftest that try to
import src.services (which is not wired up and not needed for model tests).
"""

import importlib.util
import os
import sys

import pytest

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _load_real_module(dotted_name, file_path):
    """Load a module from a file path and register it in sys.modules."""
    spec = importlib.util.spec_from_file_location(dotted_name, file_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[dotted_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _wire_models():
    """Register the real src.models package under the fake src module."""
    fake_src = sys.modules.get("src")
    if fake_src is None:
        return

    # Already wired
    if "src.models" in sys.modules:
        return

    models_dir = os.path.join(_PROJECT_ROOT, "src", "models")

    # Load src.models.media first (no __init__ dependency)
    _load_real_module(
        "src.models.media",
        os.path.join(models_dir, "media.py"),
    )

    # Load src.models.notification
    _load_real_module(
        "src.models.notification",
        os.path.join(models_dir, "notification.py"),
    )

    # Load src.models.__init__ (imports from .media and .notification)
    models_pkg = _load_real_module(
        "src.models",
        os.path.join(models_dir, "__init__.py"),
    )
    models_pkg.__path__ = [models_dir]
    models_pkg.__package__ = "src.models"
    fake_src.models = models_pkg


_wire_models()


# ---------------------------------------------------------------------------
# Override root-level autouse fixtures that import src.services.*
# Model tests don't need singleton resets or translation mocking.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_singletons():
    """No-op override -- model tests have no singletons to reset."""
    yield


@pytest.fixture(autouse=True)
def mock_translation():
    """No-op override -- model tests don't use TranslationService."""
    yield
