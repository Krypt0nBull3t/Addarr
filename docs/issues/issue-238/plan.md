# Plan: Issue #238: Fix CLAUDE.md drift and add repo hygiene files

> **For agentic workers:** convert this plan to `docs/issues/issue-238/TASKS.md` with `/task-writer`, then run the `addarr-workflow` Execution Loop. Steps use checkbox (`- [ ]`) syntax.

**Goal:** `CLAUDE.md` matches the code (D1-D5), the repo has a PR template, two issue forms and `CODEOWNERS` (D6), and the rules already in force are recorded as ADRs in `docs/adr/` (D7).

**Architecture:** Documentation only, plus one new architecture test, `tests/test_architecture/test_repo_docs.py`. The test fails when `CLAUDE.md` names a repo path, CI job or test that does not exist, leaves out a CI job or an architecture test file, or when an issue form is malformed. Every task makes that test red first, then edits the docs until it is green.

**Tech Stack:** Markdown, GitHub issue-form YAML, pytest + PyYAML (already in `requirements-test.txt` / used by `test_agent_tooling.py`).

**Spec:** `gh issue view 238 --repo Krypt0nBull3t/Addarr`. Source reports (agent output, verified below): `docs-auditor.md`, `harness-audit.md` of the 2026-11-04 skill audit.

## Global Constraints

- Owned files only: `CLAUDE.md`, `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/**`, `.github/CODEOWNERS`, `docs/adr/**`, plus the new `tests/test_architecture/test_repo_docs.py` (no other issue owns it) and this plan folder.
- Do not touch the files of #236 (`.claude/settings.json`, `scripts/cloud-setup.sh`, `.claude/skills/graphify/**`, `.claude/agents/**`, `.claude/skills/review-external-pr/**`, `.gitignore`, `requirements-test.txt`, `tests/test_architecture/test_agent_tooling.py`) or of #237 (`.claude/skills/**`, `.claude/commands/**`, `.claude/issues/**`, `tests/test_handlers/conftest.py`).
- Keep these `CLAUDE.md` strings byte-for-byte; `test_agent_tooling.py` asserts them: the `## Untrusted Input` sentence (`DATA_RULE`), and no `Do not flag it as churn` / `committed graphify-out/graph.json`.
- In every changed `CLAUDE.md` section, write repo paths in full (`src/bot/handlers/delete.py`, not `delete.py`) so the path test checks them.
- Acceptance: every path, job name and test name in the changed `CLAUDE.md` sections exists; issue forms are valid GitHub issue-form YAML; `pytest`, `flake8 .`, `mypy src/`, `python run.py --validate-i18n` pass.
- Write no `TODO`/`FIXME` and no `print(` in added lines; `auto-approve.yml` flags them.

## Verified findings (2026-11-04, `origin/development` @ 5cd3a74)

| ID | Claim | Verified |
|-|-|-|
| D1 | `CLAUDE.md:146` names `src/utils/prerun_checker.py` | File is `src/utils/prerun.py` (`PreRunChecker`). `prerun_checker` is a real name: the instance `src/utils/__init__.py` exports and `run.py:14` imports. The fix names both. |
| D2 | `ci.yml` has 9 jobs, `CLAUDE.md:163` lists 5 | Job names: Lint, Type Check, Validate Translations, Unit Tests, Integration Tests, Architecture Tests, Compatibility (3.10/3.12/3.13/3.14), Dependency Audit (`continue-on-error`), Docker Build (`needs` the 4 test jobs). Branch protection on `development` requires all except Dependency Audit, by these exact names. |
| D3 | Architecture section misses tests | Confirmed: `test_agent_tooling.py` unnamed; `test_conventions.py` also has `test_handler_entry_points_have_require_auth` (`AUTH_ALLOWLIST`), `test_singleton_reset_coverage` (`reset_singletons` in `tests/conftest.py:234`), `test_media_config_dispatch_integrity`, `test_media_state_constants_in_sync`, `test_config_calls_exist_on_real_config`. |
| D4 | Keyboards and states | `InlineKeyboardButton`/`Markup` built in 9 handler files besides `keyboards.py` (audit named 3 of them). `ALBUM_SELECT = 5` exists; QUALITY_SELECT returns SEASON_SELECT for TV and ALBUM_SELECT for a music artist (`media/handler.py:578`, `:592`). |
| D5 | No agents section | `.claude/agents/arr-api-contract-checker.md` exists on `development`. `untrusted-pr-reviewer.md` and `review-external-pr` do not exist yet; #236 creates them. |
| D6 | No PR template, issue forms, CODEOWNERS | Confirmed. `create-pr.md` defines no PR-body sections (step 5: "generate from commits and issue context"); recent PR bodies are one line (`Fixes #N. ...`). `require_code_owner_reviews` is false on `development`, so CODEOWNERS blocks no merge. |
| D7 | No ADRs | Confirmed; `docs/` holds only `issues/`. |

A probe of today's `CLAUDE.md` with the Task 1 rules: paths fail only on `src/utils/prerun_checker.py` and `docs/plans/` (named on purpose as "never write here"); 8 of 9 job names miss from the CI/CD section; no backticked test names.

## Decisions (defaults below; the user can override)

1. **PR template sections.** `create-pr.md` has no body sections to mirror. Default: derive them from the create-pr steps: `Summary` (with `Fixes #`), `Changes`, `Checks` (checklist of the preflight + coverage gates), `Notes`. #237 owns `create-pr.md` and should point step 5 at the template (cross-issue need 2).
2. **Issue-form fields.** Default: exactly the audit-issue sections. Bug: Bug, Steps to reproduce, Expected behavior, Fix, Acceptance criteria, Notes. Feature: Problem, Fix, Acceptance criteria, Notes. Only Bug, Steps to reproduce, Expected behavior and Problem are required; outside reporters cannot fill Fix or Acceptance criteria. No Service dropdown or version field (the harness report suggested them; YAGNI until bug reports lack them).
3. **Drift test is permanent.** Default: new `tests/test_architecture/test_repo_docs.py`, runs in the Architecture Tests and Compatibility jobs. Alternative: a one-off script check, no new file.
4. **D5 waits for #236.** The section names `.claude/agents/untrusted-pr-reviewer.md` and `.claude/skills/review-external-pr/SKILL.md`. Default: do Task 4 last, after #236 is merged into `development` and this branch is rebased; the path test is red until then.
5. **ADR form.** Default: Nygard headings (Status, Context, Decision, Consequences), ~20 lines each, no index file; `CLAUDE.md` links each ADR next to the rule it records. The ADR holds the why; `CLAUDE.md` keeps the how-to.
6. **D3 scope.** Default: name all 5 extra convention tests, not only the 2 the issue lists; the test-name check guards them.

## Review Focus

1. A path in a code span that is a placeholder or example (`docs/issues/issue-<N>/`, `src.the_module`): the regex skips spans with `<`, `>`, `*` or whitespace and only matches slash paths with a known top-level prefix; check no false MISS appears.
2. A path with a `:line` or `:func()` suffix (`src/main.py:run_bot()`): the test strips everything from the first `:`.
3. A matrix job name (`Compatibility (${{ matrix.python-version }})`): the test strips the ` (...)` suffix before matching.
4. A job name that also appears elsewhere in `CLAUDE.md` ("Type Checking" heading): the test matches only inside the `## CI/CD` section, case-sensitive.
5. An issue form whose YAML loads but GitHub rejects (duplicate `id`, field without `label`, unknown `type`): `test_issue_form_is_valid` checks these.

## Running checks in the worktree

The worktree has no `.venv`. The worktree guard refused `"/home/mark/Documents/Bot Projects/Addarr/.venv/bin/pytest"` (quoted path with a space). Run checks from a venv inside the worktree (`.venv/bin/pytest`, `.venv/bin/flake8`, `.venv/bin/mypy`, `.venv/bin/python`), or ask the user how to run them. Do not route around the guard.

---

### Task 1: Drift test + CLAUDE.md D1-D4

**Files:**
- Create: `tests/test_architecture/test_repo_docs.py`
- Modify: `CLAUDE.md` (§ Testing, § Architecture Tests, § Key Patterns, § Entry Point Flow, § CI/CD)

**Interfaces:**
- Produces: `read_text(rel_path) -> str`, `section(text: str, heading: str) -> str`, `ABSENT_ON_PURPOSE: set[str]`, `REPO_PATH: re.Pattern`. Task 3 adds `ISSUE_FORMS` and `test_issue_form_is_valid` to the same file.

- [ ] **Step 1: Write the failing tests** in `tests/test_architecture/test_repo_docs.py`

```python
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
# Paths CLAUDE.md names on purpose although they do not exist.
ABSENT_ON_PURPOSE = {"docs/plans/"}
REPO_PATH = re.compile(r"`((?:src|tests|scripts|docs|\.github|\.claude)/[^`<>*\s]*)`")

def section(text, heading):
    """Text under `## heading` up to the next `## ` heading."""
    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    assert match, heading
    return match.group(1)

def test_claude_md_paths_exist():
    paths = {p.split(":")[0] for p in REPO_PATH.findall(read_text("CLAUDE.md"))}
    missing = sorted(p for p in paths - ABSENT_ON_PURPOSE
                     if not os.path.exists(os.path.join(PROJECT_ROOT, p)))
    assert missing == []

def test_claude_md_names_every_ci_job():
    ci = section(read_text("CLAUDE.md"), "CI/CD")
    jobs = yaml.safe_load(read_text(".github/workflows/ci.yml"))["jobs"]
    names = [re.sub(r" \(.*\)$", "", job["name"]) for job in jobs.values()]
    assert [n for n in names if n not in ci] == []

def test_claude_md_names_every_architecture_test_file():
    testing = section(read_text("CLAUDE.md"), "Testing")
    files = sorted(os.path.basename(p) for p in glob.glob(
        os.path.join(PROJECT_ROOT, "tests", "test_architecture", "test_*.py")))
    assert [f for f in files if f not in testing] == []

def test_claude_md_test_names_exist():
    named = set(re.findall(r"`(test_\w+)`", read_text("CLAUDE.md")))
    # collect `^\s*(?:async )?def (test_\w+)` from every tests/**/test_*.py
    assert sorted(named - defined) == []
```

Module docstring: one line saying `CLAUDE.md` is the agents' map of the repo and these checks fail when it names something that does not exist.

- [ ] **Step 2: Run, expect red**

Run: `.venv/bin/pytest tests/test_architecture/test_repo_docs.py -v`
Expected: `test_claude_md_paths_exist` FAIL on `src/utils/prerun_checker.py`; `test_claude_md_names_every_ci_job` FAIL on 8 names (all but Compatibility); `test_claude_md_names_every_architecture_test_file` FAIL on `test_agent_tooling.py`, `test_repo_docs.py`. `test_claude_md_test_names_exist` passes (no names yet). Plant `` `test_does_not_exist` `` in `CLAUDE.md`, see it fail, remove it.

- [ ] **Step 3: Edit `CLAUDE.md`**

D1, § Entry Point Flow: replace `` (`src/utils/prerun_checker.py`) `` with `` (`src/utils/prerun.py`: `PreRunChecker`, exported as the instance `prerun_checker` from `src/utils/__init__.py`) ``.

D2, § CI/CD, replace the `ci.yml` bullet with:

> - **`ci.yml`**: Runs on PRs to `main`/`development`. Jobs, by their `name:`: Lint (`flake8 .`), Type Check (`mypy src/`), Validate Translations (`--validate-i18n`), Unit Tests (`tests/` without `tests/integration` and `tests/test_architecture`, `--cov-fail-under=100`), Integration Tests (`tests/integration`), Architecture Tests (`tests/test_architecture`), Compatibility (whole suite on Python 3.10, 3.12, 3.13 and 3.14), Dependency Audit (`pip-audit`, `continue-on-error`) and Docker Build (after the four test jobs). Branch protection on `development` requires every job except Dependency Audit by these names, so renaming a job blocks merges until the rule is updated.

D3, § Testing: the "Singleton reset" bullet names the fixture: `` `reset_singletons` in `tests/conftest.py` ``. § Architecture Tests: keep the two bullets; append to "Structural conventions" one sentence each for `test_handler_entry_points_have_require_auth` (entry points need `@require_auth` unless in `AUTH_ALLOWLIST`), `test_singleton_reset_coverage` (`SINGLETON_CLASSES` and `reset_singletons` list the same classes), `test_media_config_dispatch_integrity` (every `MEDIA_CONFIG` method in `src/bot/handlers/media/dispatch.py` exists on `MediaService`), `test_media_state_constants_in_sync` (media states in `dispatch.py` equal `States`), `test_config_calls_exist_on_real_config` (`src/` calls only methods the real `Config` defines, not `MockConfig` helpers). Add two bullets:

> - **Agent tooling** (`test_agent_tooling.py`): Claude Code safety rules: the `.claude/settings.json` deny rules, the guarded graphify skill and its version pin, the untrusted-text rule in this file, and pinned requirements.
> - **Docs drift** (`test_repo_docs.py`): every repo path, CI job and test name this file names exists, and the issue forms in `.github/ISSUE_TEMPLATE/` are valid.

Replace "When adding new services" with: add the class to `SINGLETON_CLASSES` in `tests/test_architecture/test_conventions.py` **and** reset its `_instance` in `reset_singletons` in `tests/conftest.py`.

D4, § Key Patterns: state machine bullet becomes `` `SEARCHING → SELECTING → QUALITY_SELECT`, then `SEASON_SELECT` (TV) or `ALBUM_SELECT` (music artist), then `END` (states in `src/bot/states.py`, mirrored in `src/bot/handlers/media/dispatch.py`) ``. Keyboard bullet becomes: **Keyboards**: shared inline keyboard builders live in `src/bot/keyboards.py`; use one when it fits. Flow-specific keyboards are built in the handler, e.g. `src/bot/handlers/media/formatters.py` (result navigation), `src/bot/handlers/media/season_picker.py` (seasons) and `src/bot/handlers/delete.py`.

The `.github/ISSUE_TEMPLATE/` path in the Docs drift bullet does not exist until Task 3: write that bullet without the path now (`the issue forms`) and add the path in Task 3, or keep Task 1 red on it until Task 3. Default: add it in Task 3.

- [ ] **Step 4: Run, expect green**

Run: `.venv/bin/pytest tests/test_architecture/ -q`
Expected: all pass, including `test_claude_md_treats_external_text_as_data` and `test_claude_md_has_no_graph_churn_exemption`.

- [ ] **Step 5: Commit**: `docs: fix CLAUDE.md drift and add docs drift test (#238, task 1)`

### Task 2: ADRs for rules in force (D7)

**Files:**
- Create: `docs/adr/0001-singleton-services.md`, `docs/adr/0002-config-get-access.md`, `docs/adr/0003-handler-registration-order.md`, `docs/adr/0004-prs-target-development.md`
- Modify: `CLAUDE.md`

**Interfaces:** Consumes `test_claude_md_paths_exist` from Task 1.

- [ ] **Step 1: Link the ADRs from `CLAUDE.md` first** (red): § Layered Design services item gets `` (`docs/adr/0001-singleton-services.md`) ``; the Config access rule gets `` `docs/adr/0002-config-get-access.md` ``; § Handler Registration Order ends `` See `docs/adr/0003-handler-registration-order.md`. ``; § Git Branching ends `` See `docs/adr/0004-prs-target-development.md`. ``; § Planning & Task Conventions gets: **Architecture decisions:** rules in force are recorded in `docs/adr/` as `NNNN-<slug>.md` (Status, Context, Decision, Consequences). Add one when a decision changes a rule in this file.
- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_architecture/test_repo_docs.py::test_claude_md_paths_exist -v`. Expected: FAIL listing the 4 ADR paths and `docs/adr/`.
- [ ] **Step 3: Write the 4 ADRs.** Each: `# NNNN. <Title>`, `**Status:** Accepted (recorded 2026-11-04; in force before)`, then Context, Decision, Consequences. Use only facts from the code, tests and `CLAUDE.md`; do not invent history.
  - 0001 Singleton services: every class in `src/services/` overrides `__new__` with a class `_instance`. Enforced by `test_all_services_implement_singleton` (`SINGLETON_CLASSES`) and `test_singleton_reset_coverage`. Consequences: tests reset `_instance` in `reset_singletons`; mypy needs class-level annotations for attributes set in `__new__`/`_initialize`.
  - 0002 `config.get()` over `config["key"]`: bracket access raises `KeyError` with no fallback (docstring of `test_no_config_bracket_access_in_business_logic`, added 2026-03-03). Exclusions: `src/setup/`, `src/api/base.py`, `src/config/settings.py`. Related: `test_config_calls_exist_on_real_config`.
  - 0003 Handler registration order: Auth, Media, Settings, other feature handlers, Help, Preferences, System, Start last; PTB takes the first matching handler; Start's `menu_cancel` must not take a Cancel tap from an open conversation (fixed 2026-10-27, commit 3d03ea6). Pinned by `tests/integration/test_start_flow.py::test_menu_cancel_still_ends_media_search`.
  - 0004 PRs target `development`, merge commits: feature/fix PRs target `development`; only `development` → `main` release PRs target `main`; merge with `--merge`, never squash or rebase. `development` protection (2026-11-04): 1 approval, the CI job names as required checks.
- [ ] **Step 4: Run** the same test. Expected: PASS.
- [ ] **Step 5: Commit**: `docs: record rules in force as ADRs (#238, task 2)`

### Task 3: PR template, issue forms, CODEOWNERS (D6)

**Files:**
- Create: `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/bug_report.yml`, `.github/ISSUE_TEMPLATE/feature_request.yml`, `.github/CODEOWNERS`
- Modify: `tests/test_architecture/test_repo_docs.py`, `CLAUDE.md` (Docs drift bullet path)

**Interfaces:** Consumes `read_text` from Task 1.

- [ ] **Step 1: Write the failing test**

```python
ISSUE_FORMS = {
    "bug_report.yml": ["Bug", "Steps to reproduce", "Expected behavior",
                       "Fix", "Acceptance criteria", "Notes"],
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
```

- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_architecture/test_repo_docs.py -k issue_form -v`. Expected: 2 FAIL, `FileNotFoundError`.
- [ ] **Step 3: Write the files.**
  - Issue forms: all fields `type: textarea`; `validations: required: true` only on Bug, Steps to reproduce, Expected behavior (bug) and Problem (feature). `name: Bug report` / `Feature request`; `labels: [bug]` / `[enhancement]` (both labels exist by default on GitHub; check with `gh label list` and drop the key if missing). No `config.yml`; blank issues stay allowed.
  - `.github/PULL_REQUEST_TEMPLATE.md`, sections:
    ```markdown
    ## Summary
    Fixes #

    ## Changes
    -

    ## Checks
    - [ ] Base branch is `development` (only `development` → `main` release PRs target `main`)
    - [ ] `pytest` passes and changed `src/` code has 100% coverage (CI: `--cov-fail-under=100`)
    - [ ] `flake8 .` and `mypy src/` pass
    - [ ] `python run.py --validate-i18n` passes; new keys are in the template and all 9 locale files
    - [ ] A changed user-facing flow has an integration test in `tests/integration/`

    ## Notes
    ```
  - `.github/CODEOWNERS`: `* @Krypt0nBull3t`
  - `CLAUDE.md` Docs drift bullet: name `.github/ISSUE_TEMPLATE/`.
- [ ] **Step 4: Run** `.venv/bin/pytest tests/test_architecture/ -q`. Expected: all pass.
- [ ] **Step 5: Commit**: `chore: add PR template, issue forms and CODEOWNERS (#238, task 3)`

### Task 4: Agents section and fork-PR rule (D5): after #236 is merged

**Files:** Modify: `CLAUDE.md` (new `## Agents` section directly after `## Untrusted Input`)

**Interfaces:** Consumes `test_claude_md_paths_exist`; the agent and skill files #236 adds.

- [ ] **Step 1: Write the section first** (red on a branch without #236):

> ## Agents
>
> Project agents in `.claude/agents/`:
>
> - **`arr-api-contract-checker`** (`.claude/agents/arr-api-contract-checker.md`): checks Radarr, Sonarr and Lidarr requests in `src/api/` against the Servarr OpenAPI specs. Run it after adding or changing a request in `src/api/`, or when a test mocks a new *arr endpoint or response field.
> - **`untrusted-pr-reviewer`** (`.claude/agents/untrusted-pr-reviewer.md`): read-only review of a PR from a fork or outside contributor, from a plain-text export.
>
> **Fork and outside PRs:** never check out a fork's branch (`gh pr checkout`, `git checkout`) and never run its code, tests or hooks on this machine. Use the `review-external-pr` skill (`.claude/skills/review-external-pr/SKILL.md`): it exports the PR without a checkout and dispatches `untrusted-pr-reviewer`.

- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_architecture/test_repo_docs.py::test_claude_md_paths_exist -v`. Expected before rebase: FAIL on the two #236 paths.
- [ ] **Step 3: Rebase** on `origin/development` once #236 is merged. Re-read both agent files and the skill; align the wording above with what #236 shipped (agent trigger, export steps). Keep the `## Untrusted Input` sentence unchanged.
- [ ] **Step 4: Run** `.venv/bin/pytest tests/test_architecture/ -q`. Expected: all pass.
- [ ] **Step 5: Commit**: `docs: add agents section and fork-PR rule to CLAUDE.md (#238, task 4)`

### Task 5: Verification

- [ ] `.venv/bin/pytest --tb=short -q`, `.venv/bin/flake8 .`, `.venv/bin/mypy src/`, `PYTHONIOENCODING=utf-8 .venv/bin/python run.py --validate-i18n`: all pass.
- [ ] Re-run the D1-D5 claims by hand against the final `CLAUDE.md` (the test does not read prose: keyboard files, state flow, branch-protection sentence).
- [ ] After push (create-pr flow): `gh api "repos/Krypt0nBull3t/Addarr/codeowners/errors?ref=fix/238-claude-md-drift"` returns `{"errors":[]}`.

## Cross-issue needs

1. **#236 → #238:** merge #236 first; Task 4 names its files. If #236 wants text in `CLAUDE.md` (e.g. "never run `graphify claude install`" for S3, or a new `test_agent_tooling.py` assertion on a `CLAUDE.md` string), send the exact string to #238; #238 owns `CLAUDE.md`.
2. **#237:** `create-pr.md` step 5 should fill `.github/PULL_REQUEST_TEMPLATE.md` so the template and the skill do not drift. K4's agent wiring should use the same trigger as the Agents section ("after adding or changing a request in `src/api/`"). K3's `keyboards.md` fix should match the D4 wording.
3. **#237 acceptance grep is wrong for `prerun_checker`:** `grep -rn "prerun_checker" .claude tests` will always hit `tests/test_run.py` and `tests/test_utils/test_prerun.py`; `src.utils.prerun_checker` is a real exported instance. Scope that grep to `.claude` or to the path `prerun_checker.py`.

## Out of scope

`.github/copilot-instructions.md` (not in the issue), `.gitignore` (#236 S4), a `blank_issues_enabled` config, Service/version fields in the bug form.
