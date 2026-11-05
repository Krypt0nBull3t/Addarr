# Issue #214: TASKS

Plan: `docs/issues/issue-214/plan.md`. Branch `fix/214-pin-deps-docker-publish`. The developer approved the plan and the `.github/workflows/docker-hub-push.yml` edit exactly as in plan Task 4 step 3. No other `.github/` change. No edit to `requirements.txt`.

### Phase 1: Pin the build and fix the publish pipeline (4 tasks)

**Goal:** The help replies stop using the deprecated argument, the image installs the pinned requirements and holds only what the bot needs, and the publish workflow pushes a version tag next to `:latest`.

**Phase Context:**

- Why NOT change `requirements.txt`: it already has exact `==` pins (`python-telegram-bot[job-queue]==22.8`, `aiohttp==3.14.5`). They are stricter than the issue's `~=22.8` and `<4`, and CLAUDE.md § Requirement pins requires them.
- Why NOT a git-tag version source: the repo has no git tags. The version comes from `__version__` in `src/__init__.py`.

- [x] **1.1** Replace the deprecated help argument (F151)
    - **Context:**
        - **Why:** `src/bot/handlers/help.py` passes `disable_web_page_preview=True` at lines 92 (`edit_text`) and 99 (`reply_text`). PTB 22.8 deprecates it in favor of `link_preview_options`.
        - **Architecture:** Plain handler change. `LinkPreviewOptions` comes from `telegram`.
        - **Key refs:** `src/bot/handlers/help.py:92`, `:99`; `tests/test_handlers/test_help_handler.py` (`_help_patches`, `_make_handler`, `test_show_help_callback`)
        - **Watch out:** Two code paths: the `/help` command (`reply_text`) and the callback (`edit_text`). Test both. An integration test may assert the old argument; run `tests/integration`.
    - **Scope:** Both help replies pass `link_preview_options=LinkPreviewOptions(is_disabled=True)` and no `disable_web_page_preview`.
    - **Touches:** `src/bot/handlers/help.py`, `tests/test_handlers/test_help_handler.py`
    - **Action items:**
        - [RED] Write `test_show_help_command_disables_link_preview`: `reply_text` kwargs hold `link_preview_options` with `is_disabled is True` and no `disable_web_page_preview`
        - [RED] Write `test_show_help_callback_disables_link_preview`: same for `edit_text` on the callback path
        - [GREEN] Replace the argument at both calls and import `LinkPreviewOptions`
    - **Success:** the two new tests fail first, then pass; `scripts/test_runner.py handlers --coverage` and `tests/integration` pass; flake8 and mypy clean
    - **Completed:** 2026-11-05
    - **Learnings:**
        - Both new tests failed first with `KeyError: 'link_preview_options'`, so they test the real kwargs.
        - The post-edit flake8 hook runs after each single Edit: add the import before the code that uses it, or expect a transient F821.
    - **Key Changes:**
        - `src/bot/handlers/help.py`: `show_help` passes `link_preview_options=LinkPreviewOptions(is_disabled=True)` in `edit_text` and `reply_text`; imports `LinkPreviewOptions`.
        - `tests/test_handlers/test_help_handler.py`: two new link-preview tests.
    - **Notes:** Handlers run: 759 passed, 100% coverage. Integration: 105 passed. No integration test asserted the old argument.

- [x] **1.2** Install requirements without `--upgrade` and pin the pip upgrade (F151, F153)
    - **Context:**
        - **Why:** `Dockerfile:16` runs `pip install --no-cache-dir -r requirements.txt --upgrade`, which can lift a pinned package. The pip upgrade (`pip>=26.2`, lines 14-15) is already committed, with no test.
        - **Architecture:** Text tests on the `Dockerfile`, in the style of `tests/test_dockerfile.py`.
        - **Key refs:** `Dockerfile:13-16`; `tests/test_dockerfile.py` (`dockerfile_lines`, `_healthcheck_command` joins continuation lines)
        - **Watch out:** Keep the first `pip install --upgrade "pip>=26.2"`. Only the requirements install loses `--upgrade`. Join `\` continuation lines before you search.
    - **Scope:** One word removed from `Dockerfile`; a `TestDockerfileReproducibleBuild` class.
    - **Touches:** `Dockerfile`, `tests/test_dockerfile.py`
    - **Action items:**
        - [RED] Write `test_requirements_install_has_no_upgrade`
        - [RED] Write `test_pip_is_upgraded_before_requirements` (passes today; it pins F153)
        - [GREEN] Remove ` --upgrade` from the requirements install
    - **Success:** the first test fails first, then both pass; `pytest tests/test_dockerfile.py` passes
    - **Completed:** 2026-11-05
    - **Learnings:**
        - `test_requirements_install_has_no_upgrade` failed first on the `--upgrade` assertion; `test_pip_is_upgraded_before_requirements` passed at once because F153 was already committed.
        - Splitting the joined Dockerfile text on `&&` isolates the requirements install from the pip upgrade.
    - **Key Changes:**
        - `Dockerfile`: the requirements install no longer has `--upgrade`; the `pip>=26.2` upgrade stays.
        - `tests/test_dockerfile.py`: new class `TestDockerfileReproducibleBuild` with two tests.
    - **Notes:** `tests/test_dockerfile.py` 10 passed; `tests/test_architecture` 158 passed.

- [x] **1.3** Keep dev-only folders out of the image (F152)
    - **Context:**
        - **Why:** `.dockerignore` lacks `graphify-out/` (20 MB), `tests/`, `docs/` and `.claude/`, so the image carries them.
        - **Architecture:** Entries in `.dockerignore`, text tests in `tests/test_dockerfile.py` (`TestDockerignore`, fixture `dockerignore_entries`).
        - **Key refs:** `.dockerignore:38-43`; `tests/test_utils/test_backup.py::test_dockerignore_lists_backup_dir` (the existing style)
        - **Watch out:** The bot needs `src/`, `translations/`, `run.py`, `config_example.yaml` and `requirements.txt` in the image. Test that none of them is ignored. `docker` may not be installed: run the manual `docker build` checks only when it is, and report either way.
    - **Scope:** Four entries under a new comment, and two tests.
    - **Touches:** `.dockerignore`, `tests/test_dockerfile.py`
    - **Action items:**
        - [RED] Write `test_dockerignore_excludes_dev_folders`
        - [RED] Write `test_dockerignore_keeps_runtime_files` (passes today)
        - [GREEN] Add the four entries
        - [GREEN] Manual: `docker build -t addarr-214 .`, then `ls /app` and `pip --version` in the image (pip 26.2 or newer)
    - **Success:** the first test fails first, then both pass; `tests/test_utils/test_backup.py` still passes; the manual result is reported
    - **Completed:** 2026-11-05
    - **Learnings:**
        - The four dev-folder tests failed first; the runtime-file tests passed at once, as planned.
        - Manual check on a local `docker build`: `/app` has no `graphify-out`, `tests`, `docs` or `.claude`; pip is 26.3; the image holds python-telegram-bot 22.8 and aiohttp 3.14.5.
        - `/app` still holds `.github`, `AGENTS.md`, `CLAUDE.md`, `mypy.ini`, `pytest.ini`, `pyrightconfig.json`, `.coveragerc`, `scripts`, `requirements-test.txt`. The issue does not list them.
    - **Key Changes:**
        - `.dockerignore`: four entries under `# Development files the bot does not need`.
        - `tests/test_dockerfile.py`: `dockerignore_entries` fixture and class `TestDockerignore` (11 parametrized cases).
    - **Notes:** Follow-up for the PR body: the extra files above could join `.dockerignore` (issue #121 covers image improvements). I did not add them: out of scope.

- [x] **1.4** Push a version tag next to `:latest` (F150, developer approved)
    - **Context:**
        - **Why:** `docker-hub-push.yml:44` pushes only `${{env.REPO}}:latest`. CLAUDE.md says images are published, and the owner decided a version tag goes next to `latest`.
        - **Architecture:** A `Read version` step sets `VERSION` from `__version__` in `src/__init__.py` via `sed`; `tags` becomes two lines. A new test parses the YAML and runs the step's script.
        - **Key refs:** `.github/workflows/docker-hub-push.yml:26-47`; `src/__init__.py` (`__version__ = "0.9.0"`); `tests/test_version.py` (reads `src/__init__.py` with `ast`, never imports it: `tests/conftest.py` injects the value)
        - **Watch out:** The approved edit is exactly plan Task 4 step 3; change nothing else in `.github/`. The step must fail on an empty version (`test -n`). Skip the two script tests when `bash` is missing. The login test must still find both secrets. The Docker Hub secrets are a developer action, not part of this task.
    - **Scope:** One workflow step, a two-line `tags`, a new test file, one clause in `CLAUDE.md`.
    - **Touches:** `.github/workflows/docker-hub-push.yml`, `tests/test_docker_publish_workflow.py` (new), `CLAUDE.md`
    - **Action items:**
        - [RED] Write `test_tags_hold_latest_and_version_tag`
        - [RED] Write `test_version_step_runs_before_build`
        - [RED] Write `test_version_step_writes_version_from_init`
        - [RED] Write `test_version_step_fails_without_version`
        - [RED] Write `test_login_still_uses_both_secrets` (passes today)
        - [GREEN] Add the `Read version` step and the two-line `tags`
        - [GREEN] Name the two tags in the CLAUDE.md Docker section; keep the publish claim
    - **Success:** the tag, step and script tests fail first, then all pass; `tests/test_architecture` passes (docs drift)
    - **Completed:** 2026-11-05
    - **Learnings:**
        - Before the edit: the tag test failed and the three step tests errored (no `Read version` step); the login test passed.
        - The runner runs `run:` scripts with `bash -e`; a plain `bash -c` ignores `test -n ""`. The script tests use `bash -e`.
        - Compare the `tags` block with `splitlines()`, not `split()`: the YAML expressions hold spaces.
    - **Key Changes:**
        - `.github/workflows/docker-hub-push.yml`: step `Read version` and a two-line `tags` (`:latest` and `:${{ env.VERSION }}`), as the developer approved.
        - `tests/test_docker_publish_workflow.py` (new): five tests.
        - `CLAUDE.md`: Docker section names the two tags.
    - **Notes:** The developer added `DOCKER_HUB_USERNAME` and `DOCKER_HUB_ACCESS_TOKEN` on 2026-11-05; the first real publish test is the next push to `main`. The version tag is mutable: each push to `main` re-tags the same `:<version>` until `__version__` changes. The workflow itself cannot run locally; the `Read version` script is tested with `bash -e`.
