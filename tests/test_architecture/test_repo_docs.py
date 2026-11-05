"""
Repository docs drift tests.

CLAUDE.md is the agents' map of the repo. These checks fail when it names a
path, CI job or test that does not exist, or leaves out a CI job or an
architecture test file. They also check that AGENTS.md (the rules for the
automated PR reviewer) names only paths that exist, and the GitHub issue forms.
"""

import glob
import os
import re

import pytest
import yaml

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

# Paths CLAUDE.md names on purpose although they do not exist.
ABSENT_ON_PURPOSE = {"docs/plans/"}

# A code span that holds a repo path; spans with placeholders are skipped.
REPO_PATH = re.compile(
    r"`((?:src|tests|scripts|docs|translations|\.github|\.claude)/[^`<>*\s]*)`"
)


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


def missing_paths(rel_path):
    """Repo paths the doc names in code spans that do not exist."""
    # Drop `:line` and `:func()` suffixes.
    paths = {p.split(":")[0] for p in REPO_PATH.findall(read_text(rel_path))}
    return sorted(
        p for p in paths - ABSENT_ON_PURPOSE
        if not os.path.exists(os.path.join(PROJECT_ROOT, p))
    )


def test_claude_md_paths_exist():
    assert missing_paths("CLAUDE.md") == []


def test_agents_md_paths_exist():
    assert missing_paths("AGENTS.md") == []


def test_agents_md_has_reviewer_rules():
    body = section(read_text("AGENTS.md"), "Reviewing a pull request")
    assert "pulls/{number}/comments" in body
    assert "CLAUDE.md" in body


def test_claude_md_names_agents_md():
    assert "AGENTS.md" in section(read_text("CLAUDE.md"), "Agents")


def test_claude_md_names_every_ci_job():
    ci = section(read_text("CLAUDE.md"), "CI/CD")
    jobs = yaml.safe_load(read_text(".github/workflows/ci.yml"))["jobs"]
    # A job without `name:` shows as its id on GitHub. Drop the matrix
    # suffix: "Compatibility (${{ matrix.python-version }})".
    names = [
        re.sub(r" \(.*\)$", "", job.get("name", job_id))
        for job_id, job in jobs.items()
    ]
    assert [name for name in names if name not in ci] == []


def test_claude_md_names_every_architecture_test_file():
    testing = section(read_text("CLAUDE.md"), "Testing")
    files = sorted(glob.glob("test_*.py", root_dir=os.path.dirname(__file__)))
    assert [f for f in files if f not in testing] == []


def test_claude_md_test_names_exist():
    named = set(re.findall(r"`(test_\w+)`", read_text("CLAUDE.md")))
    defined = set()
    for path in glob.glob("tests/**/test_*.py", root_dir=PROJECT_ROOT, recursive=True):
        defined.update(re.findall(r"^\s*(?:async )?def (test_\w+)", read_text(path), re.M))
    assert sorted(named - defined) == []


def test_auto_approve_binds_approval_to_ci_commit():
    """The bot approval must name the commit CI checked (issue #246)."""
    workflow = yaml.safe_load(read_text(".github/workflows/auto-approve.yml"))
    steps = workflow["jobs"]["review"]["steps"]
    approve = next(s for s in steps if s.get("name") == "Approve PR")
    assert (
        "commit_id: context.payload.workflow_run.head_sha"
        in approve["with"]["script"]
    )


# Field labels per issue form, in order: the sections the audit issues use.
ISSUE_FORMS = {
    "bug_report.yml": [
        "Bug", "Steps to reproduce", "Expected behavior",
        "Fix", "Acceptance criteria", "Notes",
    ],
    "feature_request.yml": ["Problem", "Fix", "Acceptance criteria", "Notes"],
}
FIELD_TYPES = {"textarea", "input", "dropdown", "checkboxes"}


@pytest.mark.parametrize("name", sorted(ISSUE_FORMS))
def test_issue_form_is_valid(name):
    form = yaml.safe_load(read_text(f".github/ISSUE_TEMPLATE/{name}"))
    assert form["name"] and form["description"]
    fields = [item for item in form["body"] if item["type"] != "markdown"]
    assert {item["type"] for item in fields} <= FIELD_TYPES
    ids = [item["id"] for item in fields]
    assert len(set(ids)) == len(ids)
    assert all(re.fullmatch(r"[A-Za-z0-9_-]+", i) for i in ids)
    assert [item["attributes"]["label"] for item in fields] == ISSUE_FORMS[name]
