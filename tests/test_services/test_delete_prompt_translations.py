"""
Tests that read the real translations/addarr.*.yml files.

The autouse translation mock hides translation text, so the delete prompt
(issue 196) is checked here against the files themselves.
"""

from pathlib import Path

import pytest
import yaml

TRANSLATIONS_DIR = Path(__file__).resolve().parents[2] / "translations"
TRANSLATION_FILES = sorted(TRANSLATIONS_DIR.glob("addarr.*.yml"))


def _this_delete(path: Path) -> str:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    (locale_data,) = data.values()  # one top-level key: the locale code
    return locale_data["messages"]["ThisDelete"]


def test_all_translation_files_are_found():
    """Nine locales and the template. An empty glob must not pass silently."""
    assert len(TRANSLATION_FILES) == 10


@pytest.mark.parametrize("path", TRANSLATION_FILES, ids=lambda p: p.name)
def test_this_delete_has_title_placeholder(path):
    assert "%{title}" in _this_delete(path)


def test_en_us_this_delete_says_files_are_deleted():
    text = _this_delete(TRANSLATIONS_DIR / "addarr.en-us.yml")
    assert "files on disk" in text
