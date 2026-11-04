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

### Phase 2: PR #229 review feedback (7 tasks)

**Goal:** Close the gaps the 2026-11-04 audit of PR #229 found. The PR's bot reviews had no actionable items (only a "large file" warning for the vendored skill).

**Phase Context:**

- Source: audit findings 1-8 on PR #229. The user chose to address all of them.
- Every new or changed test is shown red first: on the current code, or on a violation planted by hand and removed after.

- [x] **2.1** [should-fix] Guard the graphify PreToolUse hooks (audit 1)
    - **Context:** `.claude/settings.json` runs `graphify hook-guard search|read` on every Bash/Grep/Read/Glob call. A machine without graphify gets a hook error per call (plan.md Review Focus 5).
    - **Scope:** Prefix each hook command with `command -v graphify >/dev/null 2>&1 || exit 0;`.
    - **Touches:** `.claude/settings.json`, `tests/test_architecture/test_agent_tooling.py`
    - **Action items:**
        - [RED] Test: run each graphify hook command with a `PATH` that has no graphify; it exits 0 with empty stderr
        - [GREEN] Add the guard
    - **Completed:** 2026-11-04
    - **Learnings:**
        - Red first: without the guard the hook exits 127 with `graphify: not found`.
        - `command -v` and `exit` are shell builtins, so the guard works with an empty `PATH`.
    - **Key Changes:**
        - `.claude/settings.json`: both PreToolUse graphify hooks start with `command -v graphify >/dev/null 2>&1 || exit 0;`.
        - New test `test_graphify_hooks_pass_on_a_machine_without_graphify` runs each hook in `sh -c` with a `PATH` that holds no graphify.
    - **Notes:** The test skips where no `sh` exists (Windows without Git Bash).

- [x] **2.2** [should-fix] Deny the force-push and `rm` variants (audit 2)
    - **Context:** `git -C . push --force`, `git push origin main --force`, `rm -fr`, `rm -r -f` and `rm -Rf` pass the 5 prefix rules. Claude Code docs (code.claude.com/docs/en/permissions, read 2026-11-04): `*` may stand anywhere and matches spaces; `:*` is a trailing ` *`; a trailing ` *` also matches the bare command; deny rules apply to each subcommand of `&&`, `;`, `|`; matching is case-sensitive; argument patterns are not a security boundary.
    - **Scope:** Keep the 5 issue patterns; add wildcard rules for git options before `push`, `--force`/`-f` after other arguments, `+refspec`, and the `rm` flag orders and cases.
    - **Touches:** `.claude/settings.json`, test file
    - **Action items:**
        - [RED] Test: a small matcher with the documented semantics; every bypass variant is denied; safe commands (`git push origin feature`, `rm -f report.txt`) are not
        - [GREEN] Add the rules
    - **Completed:** 2026-11-04
    - **Learnings:**
        - Red first: 13 of the 19 variants passed the 5 prefix rules (all 5 audit bypasses plus `-f` after the remote, `--force-with-lease`, `+main` and the other `rm` flag orders).
        - Three wildcard rules (`git *push* --force*`, `git *push* -f*`, `git *push* +*`) cover git options before `push` and force flags after other arguments. A space before `-f` keeps `git push origin feature-fix` allowed.
        - The `rm` rules stay prefix rules, one per flag order and case. A wildcard such as `rm -*f*r*` would also deny `rm -f readme.txt`.
    - **Key Changes:**
        - `.claude/settings.json` `permissions.deny`: 10 new rules next to the 5 from the issue.
        - Test file: `is_denied()` matcher, `test_deny_rules_block_force_push_and_recursive_force_rm` (19 commands), `test_deny_rules_allow_ordinary_push_and_rm` (6 commands).
    - **Notes:** Known limits (docs: a deny rule "isn't a security boundary"): `rm` with an option before the flags (`rm -v -rf`), long options (`--recursive --force`), `/bin/rm`, `bash -c '...'`, `env git push --force`, and wrapper scripts such as `with-suite-lock.sh ... -- git push --force` are not matched. The rules can also deny a harmless command that contains `push` and ` -f`, such as a `git commit -m` message; write such messages with `-F <file>`.

- [x] **2.3** [should-fix] Make the heredoc and quoting tests strict (audit 3)
    - **Context:** Three planted violations passed: an unquoted `<<GRAPHIFY_PY` heredoc with `QUESTION`, a `<<'EOF'` script with `QUESTION`, and unquoted `graphify query <question>` / `SKILL_ARG_QUESTION=QUESTION`.
    - **Scope:** Every heredoc delimiter is single-quoted; every heredoc body (any delimiter) holds no placeholder; outside heredoc bodies, every placeholder in a bash block sits inside single quotes. Convert the `GRAPHIFY_ROOT_EOF` data heredoc in `SKILL.md` Step 1 to `SKILL_ARG_INPUT_PATH`.
    - **Touches:** test file, `.claude/skills/graphify/` files the new tests flag
    - **Action items:**
        - [RED] Plant each of the 3 violations; confirm a test fails on each; remove the plants
        - [GREEN] Fix what the strict tests flag in the skill
    - **Completed:** 2026-11-04
    - **Learnings:**
        - On the real skill the strict tests failed twice: the `GRAPHIFY_ROOT_EOF` heredoc body was the `INPUT_PATH` value itself, and `github-and-merge.md` had unquoted `<owner1>/<repo1>` paths and a `--backend <name>` comment.
        - Planted in a temporary `references/zz-plant.md` (removed after): `<<GRAPHIFY_PY` with `QUESTION` failed the delimiter test and the body test; `<<'EOF'` with `QUESTION` failed the body test; `graphify query <question>` and `SKILL_ARG_QUESTION=QUESTION` each failed the single-quote test.
        - Removing single-quoted strings and backslash escapes, but keeping double-quoted ones, matches how bash quotes: what is left is text the shell can still expand.
        - The body test also checks that every `<<` has a matching terminator, so a heredoc the regex cannot parse fails instead of being skipped.
        - Smoke: the new scan-root block with the path `it's $(touch MARK) \`touch MARK2\` dir` wrote that path verbatim to `.graphify_root` and created no marker file.
    - **Key Changes:**
        - Test file: `HEREDOC`, `SHELL_QUOTING`, `bash_blocks()`; `test_graphify_heredocs_quote_their_delimiter`, `test_graphify_heredoc_bodies_hold_no_value` (any delimiter) and `test_graphify_bash_values_sit_in_single_quotes` replace the `GRAPHIFY_PY`-only body test and the double-quote test.
        - `SKILL.md` Step 1: the scan root is set through `SKILL_ARG_INPUT_PATH` and a `<<'GRAPHIFY_PY'` script instead of a data heredoc read from stdin.
        - `github-and-merge.md`: merge paths are the single-quoted paths `graphify clone` printed; `--backend '<name>'`.
    - **Notes:** Shell comments in bash blocks are scanned too, on purpose: agents copy commented commands. A `'` in a comment would start a fake quote and could hide a value; none of the current blocks has one.

- [x] **2.4** [should-fix] Pass save-result values through a file (audit 4)
    - **Context:** `query.md` puts the answer text and node labels in single-quoted shell arguments. One `'` in that prose reopens injection. `--nodes` also lets a label that starts with `--` act as an option.
    - **Scope:** The agent writes `graphify-out/.save_result.json` with the Write tool; a `<<'GRAPHIFY_PY'` script reads it and calls `graphify.ingest.save_query_result`. The path and explain flows reuse that block.
    - **Touches:** `.claude/skills/graphify/references/query.md`, test file
    - **Action items:**
        - [RED] Test: no bash block runs `save-result` in shell or holds `ANSWER`, `ORIGINAL_QUESTION`, `NODE1`, `NODE2`
        - [GREEN] Rewrite the three save-result steps and the `--correction` prose
    - **Completed:** 2026-11-04
    - **Learnings:**
        - Red first: `query.md` failed on the shell `save-result --question 'ORIGINAL_QUESTION' ...` line.
        - `graphify save-result` has `--answer-file` but no file option for the question or the nodes, so the script calls `graphify.ingest.save_query_result` directly. That also removes argv injection: a node label such as `--memory-dir=/tmp/evil` stays a label.
        - Smoke: a JSON file with `'`, `$(touch ..)`, a backtick `touch`, `'; touch MARK3; echo '` and a `--memory-dir=` label saved one memory file with the text verbatim, created no marker file and no `/tmp/evil`, and deleted the request file.
    - **Key Changes:**
        - `references/query.md`: new "Save the result" step (Write tool writes `graphify-out/.save_result.json`; a `<<'GRAPHIFY_PY'` script saves it with `out_path('memory')`); `outcome`/`correction` are JSON keys; the path and explain flows point to it.
        - Test file: `test_graphify_save_result_reads_text_from_a_file`.
    - **Notes:** After a graphify upgrade, check that `save_query_result` keeps its keyword arguments; the save script calls it directly.

- [x] **2.5** [consider] Check the ignore rule with `git check-ignore` (audit 5)
    - **Scope:** `test_graphify_out_is_git_ignored` runs `git check-ignore` on the 4 graphify paths (acceptance criterion F274).
    - **Touches:** test file
    - **Completed:** 2026-11-04
    - **Learnings:** Red on a planted `.gitignore` line `graphify-out/graph.json` (instead of `graphify-out/`): `git check-ignore` printed only one of the 4 paths. Restored the line after.
    - **Key Changes:** `test_graphify_out_is_git_ignored` runs `git check-ignore` from `PROJECT_ROOT` and compares the printed paths.
    - **Notes:** The test needs a git checkout; CI and local runs have one.

- [x] **2.6** [consider] Keep Dependabot off pytestarch 5 (audit 6)
    - **Context:** pytestarch 5.x needs Python 3.11; the CI Compatibility matrix runs 3.10. Dependabot PR #182 fails for this reason.
    - **Scope:** `ignore` entry for `pytestarch` versions `>=5` in the pip update; a test that reads it.
    - **Touches:** `.github/dependabot.yml`, test file
    - **Completed:** 2026-11-04
    - **Learnings:** Red first: the pip update had no `ignore` list.
    - **Key Changes:** `.github/dependabot.yml` pip update: `ignore` `pytestarch` `>=5` with a comment that says why. Test `test_dependabot_skips_pytestarch_5` reads it with `yaml.safe_load`.
    - **Notes:** Remove the rule when CI drops Python 3.10. Dependabot PR #182 stays open until someone closes it; this PR does not touch it.

- [ ] **2.7** [consider] Known limits and retrospective (audit 7, 8)
    - **Scope:** PR body and this file name the hook-guard node-label injection (F273 part) as a known limit and the new deny-list limits; F275 note says it was verified locally only; "check pins on the lowest matrix Python" goes into CLAUDE.md `## CI/CD` (retrospective category: new convention).
    - **Touches:** `docs/issues/issue-199/TASKS.md`, `CLAUDE.md`, PR #229 body
