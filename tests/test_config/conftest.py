"""Loader that runs the real src/config/settings.py in tests.

The root conftest replaces ``src.config.settings`` in ``sys.modules`` with a
mock, so a normal import never reaches the real ``Config``. ``load_settings``
executes a second copy of the file under another module name, with the file
reads patched, and never registers it in ``sys.modules``.
"""

import builtins
import importlib.util
import io
import os
from contextlib import ExitStack
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any, Callable, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest
import yaml

from src.definitions import CONFIG_EXAMPLE_PATH, CONFIG_PATH

SETTINGS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "src", "config", "settings.py",
)
REAL_MODULE_NAME = "src.config._real_settings"
_real_open = builtins.open
_real_exists = os.path.exists


@dataclass
class LoadedSettings:
    """Result of running the real settings module."""

    module: ModuleType
    config: Optional[Any]
    error: Optional[Exception]
    written: Dict[str, str] = field(default_factory=dict)
    q: Dict[str, MagicMock] = field(default_factory=dict)


class _WriteSink(io.StringIO):
    """A write handle that records its text in ``store`` when closed."""

    def __init__(self, store: Dict[str, str], path: str):
        super().__init__()
        self._store = store
        self._path = path

    def close(self):
        self._store[self._path] = self.getvalue()
        super().close()


def _answer(value: Any) -> MagicMock:
    return MagicMock(ask=MagicMock(return_value=value))


@pytest.fixture
def valid_config_text() -> str:
    """The example config with a Telegram token and password filled in."""
    with _real_open(CONFIG_EXAMPLE_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    data["telegram"] = {"token": "test-token", "password": "test-pass"}
    return yaml.safe_dump(data)


@pytest.fixture
def load_settings() -> Callable[..., LoadedSettings]:
    """Return ``load(config_text, ...)``, which runs the real settings module.

    ``config_text=None`` means config.yaml does not exist. ``example_text=None``
    uses the real config_example.yaml. ``select_answer=None`` makes
    ``questionary.select`` answer with its first choice.
    """

    def load(
        config_text: Optional[str],
        *,
        example_text: Optional[str] = None,
        interactive: bool = False,
        confirm: bool = True,
        select_answer: Optional[str] = None,
    ) -> LoadedSettings:
        if example_text is None:
            with _real_open(CONFIG_EXAMPLE_PATH, "r", encoding="utf-8") as f:
                example_text = f.read()
        files = {CONFIG_EXAMPLE_PATH: example_text}
        if config_text is not None:
            files[CONFIG_PATH] = config_text
        written: Dict[str, str] = {}

        def fake_open(file, mode="r", *args, **kwargs):
            path = os.fspath(file) if isinstance(file, (str, os.PathLike)) else None
            if path in (CONFIG_PATH, CONFIG_EXAMPLE_PATH):
                if "w" in mode:
                    return _WriteSink(written, path)
                return io.StringIO(files[path])
            return _real_open(file, mode, *args, **kwargs)

        def fake_exists(path):
            if os.fspath(path) in (CONFIG_PATH, CONFIG_EXAMPLE_PATH):
                return os.fspath(path) in files
            return _real_exists(path)

        def fake_select(message, choices=None, **kwargs):
            return _answer(select_answer if select_answer else choices[0])

        q = {
            "confirm": MagicMock(return_value=_answer(confirm)),
            "text": MagicMock(return_value=_answer("typed")),
            "password": MagicMock(return_value=_answer("secret")),
            "select": MagicMock(side_effect=fake_select),
        }
        terminal = MagicMock()
        terminal.isatty.return_value = interactive

        spec = importlib.util.spec_from_file_location(REAL_MODULE_NAME, SETTINGS_FILE)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        error: Optional[Exception] = None
        with ExitStack() as stack:
            stack.enter_context(patch("builtins.open", fake_open))
            stack.enter_context(patch("os.path.exists", fake_exists))
            stack.enter_context(patch("sys.stdin", terminal))
            stack.enter_context(patch("sys.stdout", terminal))
            stack.enter_context(patch("src.utils.backup.create_backup"))
            for name, mock in q.items():
                stack.enter_context(patch(f"questionary.{name}", mock))
            try:
                spec.loader.exec_module(module)
            except Exception as exc:  # the error is the result under test
                error = exc
        return LoadedSettings(
            module=module,
            config=getattr(module, "config", None),
            error=error,
            written=written,
            q=q,
        )

    return load
