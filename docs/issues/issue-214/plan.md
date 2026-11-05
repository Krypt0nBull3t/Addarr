# Issue #214: Pin dependencies and fix the Docker image publish pipeline

**Goal:** The help replies stop using the deprecated `disable_web_page_preview`, the image build installs the pinned requirements without `--upgrade` and holds only what the bot needs, and the publish workflow pushes a version tag next to `:latest`.

**Architecture:** Four small, independent edits, each with a test. The help handler passes `LinkPreviewOptions(is_disabled=True)`. A test reads the `Dockerfile` and `.dockerignore`. The publish workflow gets one step that reads `__version__` from `src/__init__.py` into `VERSION`, and a second tag. A test parses the workflow YAML and runs that step's script.

**Tech Stack:** Python 3.10+, `python-telegram-bot[job-queue]==22.8` (already pinned), PyYAML (already pinned), pytest.

**Spec:** GitHub issue #214 (findings F150, F151, F152, F153 in `docs/issues/audit-2026-10-28/FINDINGS.md`). Decisions from the orchestrator (step 3c): no pin edit, because `requirements.txt` already has exact `==` pins and CLAUDE.md requires them; the version source is `__version__` in `src/__init__.py`, since no git tags exist; the Docker Hub secrets are a developer action.

## Findings against the current code

The issue text is partly stale. Checked on `origin/development` at `8699324`:

- **F151, pins:** met. `requirements.txt` has `python-telegram-bot[job-queue]==22.8` and `aiohttp==3.14.5`. These are stricter than `~=22.8` and `<4`. No edit.
- **F151, rest:** `Dockerfile:16` still runs `pip install --no-cache-dir -r requirements.txt --upgrade`. `src/bot/handlers/help.py:92` (`edit_text`) and `:99` (`reply_text`) pass `disable_web_page_preview=True`. PTB 22.8 accepts `link_preview_options` on both.
- **F152:** `.dockerignore` has none of `graphify-out/`, `tests/`, `docs/`, `.claude/`.
- **F153:** the pip upgrade is committed (`Dockerfile:14-15`, `pip>=26.2`). Only a test that pins it is missing.
- **F150:** `gh run list` shows 16 of 16 runs failed. `gh secret list` shows only `GROQ_API_KEY` and `REVIEWER_BOT_TOKEN`, so the login step has no Docker Hub secrets. The only tag is `${{env.REPO}}:latest` (`docker-hub-push.yml:44`). The runs' logs are gone (HTTP 410), so the exact failing step is not confirmed; the missing secrets are the stated cause in the issue.

## Global Constraints

- Branch `fix/214-pin-deps-docker-publish`, PR targets `development`.
- Do not edit `requirements.txt` or `requirements-test.txt`. Exact `==` pins stay (CLAUDE.md § Requirement pins).
- Do not edit any `.github/` file before the developer approves this plan (step 4b). Task 4 is the only task that touches `.github/`.
- Use `Optional[str]` style, flake8 max line length 88, no `config["key"]` access.
- `pytest` with the 100% coverage gate, `flake8`, `mypy src/` and `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` pass.
- Every test, gate and `git push` runs through the suite lock.

## Review Focus

- The `/help` command (`reply_text`) and the Help back button (`edit_text`) are two code paths. Expected: both pass `link_preview_options` and neither passes `disable_web_page_preview`. Task 1 tests both.
- `.dockerignore` must not hide something the bot needs at runtime. Expected: `src/`, `translations/`, `run.py`, `config_example.yaml` and `requirements.txt` are not ignored. Task 3 tests it.
- `src/__init__.py` has no parsable `__version__`. Expected: the version step fails the job; it never pushes an image tagged `:`. Task 4 tests it.
- The version tag is mutable: every push to `main` re-tags the same `:0.9.0` until the version is bumped. Expected: say so in the PR body; no code change.
- The Docker Hub secrets were missing at planning time. Update: the developer added both on 2026-11-05. Expected: the first real publish test is the next push to `main`.

## Tasks

### Task 1: F151, replace the deprecated help argument

**Files:**
- Modify: `src/bot/handlers/help.py:92` and `:99`, plus the `telegram` import
- Test: `tests/test_handlers/test_help_handler.py`

**Interfaces:**
- Produces: both help replies pass `link_preview_options=LinkPreviewOptions(is_disabled=True)` and no `disable_web_page_preview`.

- [ ] **Step 1: Write the failing tests** in `tests/test_handlers/test_help_handler.py`, using the file's `_help_patches` and `_make_handler`:
  - `test_show_help_command_disables_link_preview`: call `show_help` on a `/help` message update. Read `update.message.reply_text.call_args.kwargs`. Assert `kwargs["link_preview_options"].is_disabled is True` and `"disable_web_page_preview" not in kwargs`.
  - `test_show_help_callback_disables_link_preview`: same for the callback path, reading `update.callback_query.message.edit_text.call_args.kwargs`. Build the update the way the existing `test_show_help_callback` does.
- [ ] **Step 2: Run them and see them fail.** Run: `<lock> .venv/bin/python -m pytest tests/test_handlers/test_help_handler.py -k link_preview -v`. Expected: both FAIL on `KeyError: 'link_preview_options'`.
- [ ] **Step 3: Replace the argument in `src/bot/handlers/help.py`** at both calls with `link_preview_options=LinkPreviewOptions(is_disabled=True)`. Import `LinkPreviewOptions` from `telegram` next to the existing `telegram` import.
- [ ] **Step 4: Run the help tests.** Run: `<lock> .venv/bin/python scripts/test_runner.py handlers --coverage`. Expected: PASS. Also run `<lock> .venv/bin/python -m pytest tests/integration --tb=short -v`; the help flow may have an integration test that asserts the old argument. Fix it if so.
- [ ] **Step 5: Commit** `fix: use link_preview_options in the help replies (#214, task 1)`.

### Task 2: F151 and F153, drop `--upgrade` from the requirements install and pin the pip upgrade

**Files:**
- Modify: `Dockerfile:16`
- Test: `tests/test_dockerfile.py`

**Interfaces:**
- Consumes: the `dockerfile_lines` fixture in `tests/test_dockerfile.py`.
- Produces: a `TestDockerfileReproducibleBuild` class.

- [ ] **Step 1: Write the failing test** in a new class `TestDockerfileReproducibleBuild`:
  - `test_requirements_install_has_no_upgrade`: join the lines (continuations folded as in `_healthcheck_command`), find the command that contains `-r requirements.txt`, and assert it does not contain `--upgrade`.
  - `test_pip_is_upgraded_before_requirements`: assert the Dockerfile text contains `"pip>=26.2"` and that this text comes before `-r requirements.txt`. This test passes today; it pins the already committed F153 change.
- [ ] **Step 2: Run them.** Run: `<lock> .venv/bin/python -m pytest tests/test_dockerfile.py -k Reproducible -v`. Expected: the first FAILS, the second PASSES.
- [ ] **Step 3: Remove ` --upgrade`** from the second `pip install` in `Dockerfile:16`. Keep the first `pip install --upgrade "pip>=26.2"` as is.
- [ ] **Step 4: Run** `<lock> .venv/bin/python -m pytest tests/test_dockerfile.py -v`. Expected: PASS.
- [ ] **Step 5: Commit** `fix: install pinned requirements without --upgrade (#214, task 2)`.

### Task 3: F152, keep dev-only folders out of the image

**Files:**
- Modify: `.dockerignore`
- Test: `tests/test_dockerfile.py`

**Interfaces:**
- Produces: a `TestDockerignore` class with a `dockerignore_entries` fixture (the non-blank, non-comment lines of `.dockerignore`).

- [ ] **Step 1: Write the failing tests:**
  - `test_dockerignore_excludes_dev_folders`: assert `graphify-out/`, `tests/`, `docs/` and `.claude/` are in the entries.
  - `test_dockerignore_keeps_runtime_files`: assert none of `src`, `src/`, `translations`, `translations/`, `run.py`, `config_example.yaml`, `requirements.txt` is in the entries.
- [ ] **Step 2: Run them.** Run: `<lock> .venv/bin/python -m pytest tests/test_dockerfile.py -k dockerignore -v`. Expected: the first FAILS, the second PASSES.
- [ ] **Step 3: Add the four entries** to `.dockerignore`, in a new group after the `local/` line, under the comment `# Development files the bot does not need`.
- [ ] **Step 4: Run** `<lock> .venv/bin/python -m pytest tests/test_dockerfile.py tests/test_utils/test_backup.py -v`. Expected: PASS. If `docker` is installed, also run `docker build -t addarr-214 .` and `docker run --rm --entrypoint ls addarr-214 /app`: no `graphify-out`, `tests`, `docs`, `.claude`. Run `docker run --rm --entrypoint pip addarr-214 --version`: pip 26.2 or newer. Report the result; skip with a note when `docker` is missing.
- [ ] **Step 5: Commit** `fix: add dev folders to .dockerignore (#214, task 3)`.

### Task 4: F150, push a version tag next to `:latest` (needs developer approval)

**Files:**
- Modify: `.github/workflows/docker-hub-push.yml`, `CLAUDE.md` (the Docker section, one clause)
- Create: `tests/test_docker_publish_workflow.py`

**Interfaces:**
- Produces: a workflow step named `Read version` before `Build and push`, and a `tags` value with two lines.

- [ ] **Step 1: Write the failing tests** in `tests/test_docker_publish_workflow.py`. Load the workflow with `yaml.safe_load` from `.github/workflows/docker-hub-push.yml` (path built from `__file__`, as `tests/test_dockerfile.py` does). Pick the step whose `uses` starts with `docker/build-push-action`.
  - `test_tags_hold_latest_and_version_tag`: split `with.tags` into lines. Assert one line ends with `:latest` and one line ends with `:${{ env.VERSION }}`, and both start with `${{ env.REPO }}`.
  - `test_version_step_runs_before_build`: assert the step named `Read version` exists and sits before the build step.
  - `test_version_step_writes_version_from_init`: run the step's `run` script with `bash -c`, `cwd` set to the repo root and `GITHUB_ENV` set to a `tmp_path` file. Read `__version__` from `src/__init__.py` with `ast` (the `tests/test_version.py` way). Assert the file holds `VERSION=<that value>`.
  - `test_version_step_fails_without_version`: run the same script with `cwd` set to an empty `tmp_path`. Assert a non-zero exit code and an empty `GITHUB_ENV` file.
  - `test_login_still_uses_both_secrets`: assert the login step references `secrets.DOCKER_HUB_USERNAME` and `secrets.DOCKER_HUB_ACCESS_TOKEN`.
  - Skip the two script tests with `pytest.mark.skipif(shutil.which("bash") is None, ...)`.
- [ ] **Step 2: Run them and see them fail.** Run: `<lock> .venv/bin/python -m pytest tests/test_docker_publish_workflow.py -v`. Expected: the tag, step and script tests FAIL; the login test PASSES.
- [ ] **Step 3: Edit the workflow.** Exact change, after the `downcase REPO` step and before `Build and push`:

```yaml
      - name: Read version
        run: |
          VERSION=$(sed -n 's/^__version__ = "\(.*\)"$/\1/p' src/__init__.py)
          test -n "$VERSION"
          echo "VERSION=${VERSION}" >>"${GITHUB_ENV}"
```

  and replace `tags: ${{env.REPO}}:latest` with:

```yaml
          tags: |
            ${{ env.REPO }}:latest
            ${{ env.REPO }}:${{ env.VERSION }}
```

- [ ] **Step 4: Edit `CLAUDE.md`.** In the Docker section, change "Images are automatically published to Docker Hub via the `docker-hub-push.yml` workflow." to also say that every push to `main` pushes `:latest` and `:<version>` (the `__version__` in `src/__init__.py`). Keep the publish claim.
- [ ] **Step 5: Run** `<lock> .venv/bin/python -m pytest tests/test_docker_publish_workflow.py tests/test_architecture --tb=short -v`. Expected: PASS.
- [ ] **Step 6: Commit** `fix: push a version tag next to :latest (#214, task 4)`.

## Verification

- Preflight (`/addarr pr` step 5): flake8, mypy, translation check, unit tests with the 100% gate, integration tests, architecture tests.
- Acceptance criteria map: F151 help test (task 1), F151 pins (met by the existing pins, no task), F150 workflow test (task 4), F152 and F153 checks (tasks 3 and 2, plus the manual `docker` commands in task 3 step 4).

## Developer actions (list in the PR body)

- F150: add the repo secrets `DOCKER_HUB_USERNAME` and `DOCKER_HUB_ACCESS_TOKEN`. Done by the developer on 2026-11-05.
- F150 (manual check): after the secrets exist, a push to `main` runs the workflow green and pushes `:latest` and `:0.9.0`.
- F151 pin item: met by the existing exact pins. State this in the PR body.

## Out of scope (list in the PR body as follow-ups)

- The version tag is mutable: each push to `main` re-tags the same `:<version>` until `__version__` is bumped.
- The workflow builds `linux/arm` with QEMU. The issue does not ask to change platforms.
- Related open issue #121 (Docker image improvements) stays open.
