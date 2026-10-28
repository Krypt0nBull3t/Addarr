# Issue #199: Stop agent tooling from acting on untrusted text

Plan: `docs/issues/issue-199/plan.md`. Spec: `docs/issues/audit-2026-10-28/issues/04-agent-tooling-security.md`.

### Phase 1: Agent tooling hardening (4 tasks)

**Goal:** Outside text is data, risky commands are denied, graphify is injection-safe, offline and pinned, and builds use exact pins.

**Phase Context:**

- Why tests for config and docs: the graphify skill is vendored. A later `graphify install` overwrites it, and these tests then fail CI.
- Why `SKILL_ARG_*` and not `GRAPHIFY_ARG_*`: graphify reads many `GRAPHIFY_*` env vars itself.

- [x] **1.1** Deny list, data rule and git-ignored graph (F271, F272, F270 docs, F274)
    - **Context:** See plan.md Task 1. Key refs: `tests/test_architecture/test_conventions.py:11` (`PROJECT_ROOT` pattern), `.claude/settings.json:5-10`, `CLAUDE.md` `## graphify` section, `.claude/skills/addarr-workflow/references/feedback.md:12-20`.
    - **Watch out:** Commit `.claude/settings.json` and `CLAUDE.md` whole (they carry the uncommitted graphify hooks and section). Do not stage `.claude/skills/graphify/` until 1.3.
    - **Scope:** `permissions.deny` with 5 patterns, `## Untrusted Input` section, graph.json churn line removed, graphify CLI examples in single quotes, rebuild line, feedback.md data line, `graphify-out/` in `.gitignore`.
    - **Touches:** `tests/test_architecture/test_agent_tooling.py` (new), `.claude/settings.json`, `CLAUDE.md`, `.claude/CLAUDE.md`, `feedback.md`, `.gitignore`
    - **Action items:**
        - [RED] Tests: deny patterns present; CLAUDE.md has the data rule; CLAUDE.md has no churn exemption; feedback.md says PR comments are data; `.gitignore` lists `graphify-out/`
        - [RED] Run, confirm 5 fail for the right reason
        - [GREEN] Edit settings.json, CLAUDE.md, feedback.md, .gitignore
        - [GREEN] Run, confirm pass; `git check-ignore` prints the 4 graphify paths
    - **Success:** 5 tests pass; full suite passes; commit `fix: deny risky commands and treat outside text as data (#199)`
    - **Completed:** 2026-10-28
    - **Learnings:**
        - The 5 tests failed for the expected reasons first (no deny key, no rule, churn line present, no feedback line, no ignore line).
        - Full suite: 2128 passed, run under `~/.local/share/agent-suite/with-suite-lock.sh`.
    - **Key Changes:**
        - New `tests/test_architecture/test_agent_tooling.py` with `read_text()`, `load_settings()`, `DENY_PATTERNS`, `DATA_RULE`.
        - `.claude/settings.json`: `permissions.deny` with 5 patterns.
        - `CLAUDE.md`: `## Untrusted Input` section; graphify section uses single-quoted CLI examples, says graphify-out/ is git-ignored, churn line removed.
        - `feedback.md` Step 2: PR comments are data. `.gitignore`: `graphify-out/`.
    - **Notes:** This commit also carries the first commit of the graphify hooks, the CLAUDE.md graphify section, `.claude/CLAUDE.md` and the `.opencode/` ignore line. The skill itself waits for 1.3.

- [x] **1.2** Exact pins and graphify in cloud sessions (F275)
    - **Context:** See plan.md Task 2 and Global Constraints for the exact versions. Key refs: `requirements.txt`, `requirements-test.txt`, `scripts/cloud-setup.sh:24-33`.
    - **Watch out:** Keep the header comments in `requirements.txt`. Pins must install on Python 3.11 (CI and Docker), not only on the 3.14 venv.
    - **Scope:** `==` pins in both requirement files; `pip install -q graphifyy==0.9.97` and `graphify --version` in cloud-setup.sh.
    - **Touches:** `requirements.txt`, `requirements-test.txt`, `scripts/cloud-setup.sh`, test file
    - **Action items:**
        - [RED] Tests: each requirement line in both files is `name==version` (parametrized); cloud-setup.sh installs `graphifyy==0.9.97`
        - [RED] Run, confirm fail
        - [GREEN] Edit the three files
        - [GREEN] Run, confirm pass; 3.11 dry-run install shows no `ERROR`
    - **Success:** tests pass; dry run clean; commit `fix: pin requirements and install graphify in cloud sessions (#199)`
    - **Completed:** 2026-10-28
    - **Learnings:**
        - The new `Bash(rm -rf:*)` deny rule blocked a scratch cleanup in this session at once, so the deny list is live.
        - `pip install --dry-run --python-version 3.11 --only-binary=:all: --target <dir>` resolves all pins plus `graphifyy==0.9.97` for Python 3.11.
    - **Key Changes:**
        - `requirements.txt`, `requirements-test.txt`: exact `==` pins at the `.venv` versions.
        - `scripts/cloud-setup.sh`: installs `graphifyy==0.9.97`, prints `graphify --version`.
        - Tests: `test_requirements_are_pinned` (2 params), `test_cloud_setup_installs_pinned_graphify`; constant `GRAPHIFY_PIN`.
    - **Notes:** CI's Compatibility matrix also runs Python 3.10, and `pytestarch==5.1.0` needs 3.11, so PR #229 CI failed there. Pinned `pytestarch==4.0.1` (needs 3.9 or newer); all pins now resolve on 3.10, 3.11 and 3.14, and the suite passes on 3.14. Check pins against the lowest matrix Python, not only the Docker one. Dependabot keeps `==` pins current. Its open `>=` bump PRs go stale after this merges. Dockerfile `--upgrade` stays for #214.

- [x] **1.3** Injection-safe, offline, pinned graphify skill (F273)
    - **Context:** See plan.md Task 3 (shell form, placeholder-to-env-var map, prose rules). Key refs: `.claude/skills/graphify/SKILL.md:73-111`, `:165-172`, `:581`; `references/query.md:14-316`; `references/update.md:85` (heredoc inside `if`); `references/add-watch.md:10-30`; `references/github-and-merge.md:36`.
    - **Watch out:** Heredoc terminator at column 0, also inside the `if`. Undo the `\"` escapes when a script leaves the double-quoted string. No converted body may read `sys.stdin`. `uv tool run --from graphifyy` is an install too: pin it. `extract_corpus_parallel(backend=...)` overrides `GRAPHIFY_BACKEND=none`, so the skill must never pass `backend=` unless the user asks.
    - **Scope:** 32 interpreter calls quoted and moved to `<<'GRAPHIFY_PY'` heredocs; values via `SKILL_ARG_*`; CLI args in single quotes; Gemini auto path removed; installs pinned; `GRAPHIFY_BACKEND=none` in settings.json `env`.
    - **Touches:** `.claude/skills/graphify/SKILL.md`, `references/{query,update,add-watch,exports,transcribe,github-and-merge}.md`, `.claude/settings.json`, test file
    - **Action items:**
        - [RED] Tests: interpreter always quoted; no `.graphify_python)" -c`; heredoc bodies hold no placeholder and no `sys.stdin`; no placeholder inside double quotes in bash blocks; every `graphifyy` token pinned to `==0.9.97`; settings env `GRAPHIFY_BACKEND` is `none`
        - [RED] Run, confirm 6 fail
        - [GREEN] Convert SKILL.md and the references; update the "Replace X" prose and the line-111 rule
        - [GREEN] Add `GRAPHIFY_BACKEND` to settings.json `env`
        - [GREEN] Smoke test: query vocab and BFS blocks with `SKILL_ARG_QUESTION='what'\''s $(id) `uname` handler'` run nothing; update.md `if` block does not hang; `graphify update .` exits 0
    - **Success:** 6 tests pass; smoke tests clean; commit `fix: make the graphify skill injection-safe, offline and pinned (#199)`
    - **Completed:** 2026-10-28
    - **Learnings:**
        - Two RED tests first passed for the wrong reason (no heredocs yet; the `-c` check only matched the quoted form). Made them strict: `\.graphify_python\)"? -c` and `assert bodies`.
        - The pristine skill ships inside the package: `graphify/skill.md` and `graphify/skills/claude/references/`. Re-running the converter on that copy gives a byte-identical result, so the only changes are the conversion and the hand edits.
        - A heredoc inside an indented `if` works with the terminator at column 0.
        - `extract_corpus_parallel(backend=...)` overrides `GRAPHIFY_BACKEND=none`, so the skill now forbids an explicit backend unless the user asks.
        - Smoke: `SKILL_ARG_QUESTION` holding `'`, `"`, `$(touch ..)` and a backtick `touch` reached Python as text; no marker file appeared. The detect block works with a path that has spaces.
    - **Key Changes:**
        - 30 `-c "..."` blocks in `SKILL.md`, `references/{query,update,add-watch,transcribe}.md` now run `"$(cat graphify-out/.graphify_python)" - <<'GRAPHIFY_PY'` and read `SKILL_ARG_*` env vars.
        - `-m` calls quote the interpreter; `graphify query/path/explain`, `save-result` args, `graphify clone` and `GRAPHIFY_WHISPER_PROMPT` use single quotes.
        - Installs pinned to `graphifyy==0.9.97` (also `uv tool run --from` and `graphifyy[video]`). Gemini auto path removed.
        - `.claude/settings.json` `env`: `GRAPHIFY_BACKEND=none`. 6 new tests.
    - **Notes:** The converter lives only in the session scratchpad. After a graphify upgrade, re-apply by hand; the tests show what to fix. `graphify update .` still prints a Gemini tip from the CLI itself; that is graphify output, not the skill.

- [x] **1.4** Verify
    - **Context:** See plan.md Task 4 and the issue's acceptance criteria.
    - **Watch out:** The PR body must carry the manual and out-of-scope notes from plan.md Task 4.
    - **Scope:** Full checks and acceptance greps.
    - **Touches:** none
    - **Action items:**
        - [GREEN] `pytest --tb=short -q`, `flake8 .`, `mypy src/`, `PYTHONIOENCODING=utf-8 python run.py --validate-i18n`
        - [GREEN] `git ls-files graphify-out` empty; no `graphify_python) -c` under `.claude/`
    - **Success:** all checks pass; acceptance criteria F271-F275 and the F270 feedback.md part met
    - **Completed:** 2026-10-28
    - **Learnings:** pytest 2137 passed; flake8 clean; mypy clean (72 files); i18n valid. `git check-ignore` matches all 4 graphify paths; `git ls-files graphify-out` is empty; no unquoted interpreter call under `.claude/`.
    - **Key Changes:** none (verification only).
    - **Notes:** F275 "hooks run without error in a cloud session" is checked locally only: `graphify hook-guard search` exits 0 in a directory with no graph. The first real cloud session confirms it.
