"""
Repository docs drift tests.

CLAUDE.md is the agents' map of the repo. These checks fail when it names a
path, CI job or test that does not exist, or leaves out a CI job or an
architecture test file.
"""

import glob
import os
import re

import yaml

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

# Paths CLAUDE.md names on purpose although they do not exist.
ABSENT_ON_PURPOSE = {"docs/plans/"}

# A code span that holds a repo path; spans with placeholders are skipped.
REPO_PATH = re.compile(r"`((?:src|tests|scripts|docs|\.github|\.claude)/[^`<>*\s]*)`")


def read_text(rel_path):
    with open(os.path.join(PROJECT_ROOT, rel_path), encoding="utf-8") as f:
        return f.read()


def section(text, heading):
    """Text under `## heading` up to the next `## ` heading."""
    match = re.search(
        rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.S | re.M
    )
    assert match, heading
    return match.group(1)


def test_claude_md_paths_exist():
    # Drop `:line` and `:func()` suffixes.
    paths = {p.split(":")[0] for p in REPO_PATH.findall(read_text("CLAUDE.md"))}
    missing = sorted(
        p for p in paths - ABSENT_ON_PURPOSE
        if not os.path.exists(os.path.join(PROJECT_ROOT, p))
    )
    assert missing == []


def test_claude_md_names_every_ci_job():
    ci = section(read_text("CLAUDE.md"), "CI/CD")
    jobs = yaml.safe_load(read_text(".github/workflows/ci.yml"))["jobs"]
    # Drop the matrix suffix: "Compatibility (${{ matrix.python-version }})".
    names = [re.sub(r" \(.*\)$", "", job["name"]) for job in jobs.values()]
    assert [name for name in names if name not in ci] == []


def test_claude_md_names_every_architecture_test_file():
    testing = section(read_text("CLAUDE.md"), "Testing")
    pattern = os.path.join(PROJECT_ROOT, "tests", "test_architecture", "test_*.py")
    files = sorted(os.path.basename(p) for p in glob.glob(pattern))
    assert files
    assert [f for f in files if f not in testing] == []


def test_claude_md_test_names_exist():
    named = set(re.findall(r"`(test_\w+)`", read_text("CLAUDE.md")))
    pattern = os.path.join(PROJECT_ROOT, "tests", "**", "test_*.py")
    defined = set()
    for path in glob.glob(pattern, recursive=True):
        with open(path, encoding="utf-8") as f:
            defined.update(re.findall(r"^\s*(?:async )?def (test_\w+)", f.read(), re.M))
    assert sorted(named - defined) == []
