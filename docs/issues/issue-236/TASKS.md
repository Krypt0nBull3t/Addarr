# Tasks: Issue #236: Harden agent tooling security

Source: `docs/issues/issue-236/plan.md` (decisions D1-D7 are settled there). All tests go in `tests/test_architecture/test_agent_tooling.py`.

### Phase 1: Tooling hardening (5 tasks)

**Goal:** Close audit findings S1-S8. Each fix has a test that fails before it.

**Phase Context:**

- Why settings last: once the `ask` rule on `.claude/settings.json` exists, every later edit of that file prompts.
- Why not a PreToolUse guard hook now: `.claude/hooks/` is outside this issue (D3 follow-up).

- [x] **1.1** Repo hygiene: secrets ignored, flake8 pinned, gh uses GH_TOKEN, Dependabot rule
    - **Context:** See plan.md Task 1. Key refs: `src/definitions.py:24-28` (the runtime files live in `ROOT_DIR`), `scripts/cloud-setup.sh:18-22`, `.github/dependabot.yml:8-11`
    - **Watch out:** flake8 7.5.0 needs Python 3.11. Pin `7.4.1`. `git check-ignore` prints only the ignored paths, so `.env.example` must be missing from its output.
    - **Scope:** S2, S4, S5, D5
    - **Touches:** `.gitignore`, `requirements-test.txt`, `scripts/cloud-setup.sh`, `.github/dependabot.yml`, test file
    - **Action items:**
        - [RED] `test_runtime_secret_files_are_git_ignored`, `test_flake8_is_pinned_for_tests`, `test_cloud_setup_leaves_auth_to_gh_token`
        - [RED] Parametrize the Dependabot test over pytestarch `>=5` and flake8 `>=7.5`
        - [GREEN] Make the four file changes
    - **Success:** new tests pass. The pip dry-run on Python 3.10 resolves.
    - **Completed:** 2026-11-04
    - **Learnings:** flake8 7.5.0 declares `Requires-Python >=3.11`, so 7.4.1 is the newest pin the 3.10 CI job can install. `git check-ignore` with a negated path (`!.env.example`) prints only the ignored paths, so one call checks both directions.
    - **Key Changes:** `.gitignore` (block for `.env`, `.env.*`, `!.env.example`, root-anchored `chatid.txt`/`admin.txt`/`allowlist.txt`); `requirements-test.txt` (`flake8==7.4.1`); `scripts/cloud-setup.sh` (dropped the `gh auth login` block); `.github/dependabot.yml` (flake8 `>=7.5` ignore). Tests: `test_runtime_secret_files_are_git_ignored`, `test_flake8_is_pinned_for_tests`, `test_cloud_setup_leaves_auth_to_gh_token`. The Dependabot test is now parametrized as `test_dependabot_skips_versions_without_python_3_10`.
    - **Notes:** The CI lint job still runs `pip install flake8` unpinned (`ci.yml`, not owned here).

- [x] **1.2** graphify skill: validated interpreter, narrow trigger, no system-package install
    - **Context:** See plan.md Task 2. Key refs: `.claude/skills/graphify/SKILL.md:3,92-93,112,748-765`, `references/hooks.md:20-36`
    - **Watch out:** The existing graphify tests scan every bash block, so new text must not contain the placeholder words (`URL`, `MODE`, …) or `<x>` outside single quotes. The guard test runs the block with `sh` in `tmp_path`, which needs `git` and `python3`.
    - **Scope:** S3
    - **Touches:** `.claude/skills/graphify/SKILL.md`, `.claude/skills/graphify/references/hooks.md`, test file
    - **Action items:**
        - [RED] `test_graphify_guard_rejects_a_planted_interpreter` (cases: none, untracked, tracked)
        - [RED] `test_graphify_triggers_only_on_command_or_existing_graph`, `test_graphify_never_breaks_system_packages`, `test_graphify_warns_against_claude_install`
        - [GREEN] Make the guard always run, change the description, change the install fallback, add the hooks.md warning
    - **Success:** all graphify tests pass, old and new.
    - **Completed:** 2026-11-04
    - **Learnings:** The guard test runs the real SKILL.md block with `sh` in a throwaway folder, so it proves the behavior rather than the wording. Before the fix the planted relative path survived (`'graphify-out/evil'`). `git ls-files` outside a repo prints nothing, so `/graphify <non-repo path>` still works.
    - **Key Changes:** `SKILL.md`: new description (only `/graphify` or an existing `graphify-out/`, never an unasked install); the pip fallback exits with a `uv tool install` hint instead of `--break-system-packages`; the interpreter guard always runs, refuses a tracked `graphify-out/`, and re-resolves a relative or non-executable path; the Step 1 note points to the guard. `references/hooks.md`: the `graphify claude install` section is now a warning. Tests: `test_graphify_guard_rejects_a_planted_interpreter` (none, untracked, tracked), `..._triggers_only_on_command_or_existing_graph`, `..._never_breaks_system_packages`, `..._warns_against_claude_install`.
    - **Notes:** After a graphify upgrade, re-apply these changes along with the ones `CLAUDE.md:227` lists. The new tests flag any that are lost.

- [x] **1.3** Agents: untrusted PR reviewer committed and fixed, contract checker hardened
    - **Context:** See plan.md Task 3. Key refs: the main checkout's untracked `.claude/agents/untrusted-pr-reviewer.md`, `.claude/agents/arr-api-contract-checker.md:4,19`
    - **Watch out:** Keep the reviewer's tools exactly `Read, Grep, Glob`.
    - **Scope:** S6 (agent), S7
    - **Touches:** `.claude/agents/untrusted-pr-reviewer.md` (new in branch), `.claude/agents/arr-api-contract-checker.md`, test file
    - **Action items:**
        - [RED] `test_agents_have_only_the_tools_they_need` (2 cases), `test_contract_checker_fails_on_http_errors`
        - [GREEN] Copy and fix the reviewer: allowlist rule, secret list, trust-boundary rule, 80-char injection quote, `## Output`
        - [GREEN] Contract checker: drop WebFetch, add hard rules, `mktemp -d`, `curl -sfL`
    - **Success:** tests pass.
    - **Completed:** 2026-11-04
    - **Learnings:** Agent frontmatter `tools` parses as a plain comma string with `yaml.safe_load`, so an exact-match test catches any added tool. The reviewer's old rule 4 ("only paths the lead names") also blocked the `references/` of the skills it preloads. An allowlist that names them fixes both that and the incomplete secret list.
    - **Key Changes:** New `.claude/agents/untrusted-pr-reviewer.md`, copied from the untracked main-checkout file. It describes the export layout, has an allowlist read rule with the full secret list, an 80-char injection quote, a trust-boundary-first rule, numbered steps, and an `## Output` with a 2000-char cap. `arr-api-contract-checker.md`: no WebFetch, `## Hard rules` (specs are data, Bash limited to mktemp/curl/jq/read-only git, no secrets, no edits), `mktemp -d` directory, `curl -sfL`. Tests: `test_agents_have_only_the_tools_they_need`, `test_contract_checker_fails_on_http_errors`.
    - **Notes:** The read limits are still prompt rules. Task 1.5's settings Read denies enforce the main secret paths for every agent.

- [ ] **1.4** `review-external-pr` skill
    - **Context:** See plan.md Task 4. Key refs: `untrusted-pr-reviewer.md` (the export layout it expects: `pr.json`, `issue.json`, `diff.txt`, `head/`, `base/`)
    - **Watch out:** No `$()` in the typed commands. Stop on a symlink (mode `120000`) before extracting.
    - **Scope:** S6 (skill)
    - **Touches:** `.claude/skills/review-external-pr/SKILL.md` (new), test file
    - **Action items:**
        - [RED] `test_review_external_pr_never_runs_pr_code`
        - [GREEN] Write the skill
    - **Success:** test passes.

- [ ] **1.5** Settings: deny, Read/Edit deny, ask, superpowers plugin
    - **Context:** See plan.md Task 5 (the final rule list is there). Key refs: `.claude/settings.json:6-28,77-80`, `test_agent_tooling.py:26-32,97-163`
    - **Watch out:** Do not write `git push origin :b` as a rule: its `:*` ending means "deny every push". Never live-test with `gh auth status -t`, because it prints the token if the rule fails.
    - **Scope:** S1, S8, D1, D2, D7
    - **Touches:** `.claude/settings.json`, test file
    - **Action items:**
        - [RED] Extend the deny matrix and the allowed matrix. Update `DENY_PATTERNS`. Add the known-gaps comment.
        - [RED] `test_settings_deny_reading_secrets`, `test_settings_ask_before_editing_self_running_files`, `test_project_enables_superpowers`
        - [GREEN] Make one edit to settings.json
    - **Success:** all of `test_agent_tooling.py` passes. The JSON is valid.

### Phase 2: Verification (1 task)

- [ ] **2.1** Preflight and acceptance
    - **Context:** See plan.md Task 6
    - **Action items:**
        - [GREEN] Run pytest under the suite lock, then `flake8 .`, `mypy src/` and `--validate-i18n`
        - [GREEN] Run `git check-ignore` and the pip dry-run
    - **Success:** everything passes.
