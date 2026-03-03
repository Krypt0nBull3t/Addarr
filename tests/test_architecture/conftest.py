"""
Architecture test fixtures.

Provides PyTestArch evaluable architecture and layer definitions
for import dependency rule tests.
"""

import ast
import os
import sys

import pytest
from pytestarch import LayeredArchitecture, get_evaluable_architecture
from pytestarch.eval_structure_generation.file_import.parser import (
    NamedModule,
    Parser,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
SRC_ROOT = os.path.join(PROJECT_ROOT, "src")

# Monkey-patch PyTestArch's file parser to use UTF-8 encoding on Windows.
# The upstream _parse_file opens files without specifying encoding, which
# defaults to cp1252 on Windows and chokes on emoji characters in source.
if sys.platform == "win32":
    _original_parse_file = Parser._parse_file

    def _parse_file_utf8(self, path):
        absolute_path = path.resolve()
        if self._file_should_be_parsed(absolute_path):
            with open(absolute_path, encoding="utf-8") as file:
                code = file.read()
            module_name = self._get_module_name(path)
            self._all_modules.append(module_name)
            return NamedModule(ast.parse(code), module_name)
        return None

    Parser._parse_file = _parse_file_utf8


@pytest.fixture(scope="session")
def evaluable():
    """Scan src/ and build an evaluable import graph for PyTestArch rules.

    Using SRC_ROOT as both root and source path so module names match
    the import-style dotted paths (e.g., src.bot.handlers, src.services).
    """
    return get_evaluable_architecture(SRC_ROOT, SRC_ROOT)


@pytest.fixture(scope="session")
def layered_architecture():
    """Define the five architectural layers and their module roots."""
    return (
        LayeredArchitecture()
        .layer("handlers")
        .containing_modules(["src.bot.handlers"])
        .layer("services")
        .containing_modules(["src.services"])
        .layer("api")
        .containing_modules(["src.api"])
        .layer("config")
        .containing_modules(["src.config"])
        .layer("utils")
        .containing_modules(["src.utils"])
    )
