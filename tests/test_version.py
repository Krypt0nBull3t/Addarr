"""Pin the released version string in src/__init__.py.

tests/conftest.py injects its own ``__version__`` into ``src``, so this test
reads the real source file instead of importing the package.
"""

import ast
from pathlib import Path

INIT_FILE = Path(__file__).resolve().parent.parent / "src" / "__init__.py"


def _declared_version() -> str:
    tree = ast.parse(INIT_FILE.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "__version__" for t in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError("src/__init__.py does not define __version__")


def test_version_is_0_9_0():
    assert _declared_version() == "0.9.0"
