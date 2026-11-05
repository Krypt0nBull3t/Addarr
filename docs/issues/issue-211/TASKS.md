# Issue 211: Bot can die silently; startup checks and healthcheck are fragile

Plan: `plan.md` in this folder. Design and decisions: `design.md`.
Run every test and every `git push` through the suite lock:
`~/.local/share/agent-suite/with-suite-lock.sh addarr/$AO_SESSION_ID -- .venv/bin/python -m pytest ...`

### Phase 1: Nine fixes (8 tasks) and verification (1 task)

**Goal:** The bot exits when polling dies, Docker detects a dead loop, shutdown is clean, and the startup checks, logs and disk check are correct.

**Phase Context:**

- Why NOT only `not updater.running` for F140: PTB 22.8 keeps `updater.running` True when the polling task dies on InvalidToken or Conflict. The loop also checks that the polling task is done (decided at step 3b).
- Why NOT `close()` on `TransmissionService`: `TransmissionClient` opens a session per call.
- Task order puts F140 (6) before F142 (8): both change `stop()`/`start()` in `src/main.py`.

- [x] **1.1** F143: add the missing `f` to the shutdown log lines
    - **Context:**
        - **Why:** `logger.info("\n{Fore.YELLOW}Shutting down...")` prints the text `{Fore.YELLOW}` literally.
        - **Architecture:** `src/main.py` imports only `init` from colorama today; add `Fore`.
        - **Key refs:** `src/main.py:12`, `:322`, `:334`; `tests/test_main.py` `TestRunBot`, `TestMain` (`test_keyboard_interrupt_stops_bot`).
        - **Watch out:** Patch `src.main.logger` in the tests; the named logger may not propagate to `caplog`.
    - **Scope:** Two log lines and one import.
    - **Touches:** `src/main.py`, `tests/test_main.py`
    - **Action items:**
        - [RED] Write a test in `TestRunBot` that the `KeyboardInterrupt` path logs "Shutting down..." and no argument contains `{Fore.YELLOW}`.
        - [RED] Write the same test for the `KeyboardInterrupt` branch of `main()`.
        - [GREEN] Make both lines f-strings and import `Fore`.
    - **Success:** Both tests fail before and pass after; `tests/test_main.py` green; flake8 and mypy clean.
    - **Completed:** 2026-11-05
    - **Learnings:**
        - The post-edit hook runs flake8 after each edit, so a half-done change (import added, use not yet) shows F401 once; it clears after the next edit.
        - `patch("src.main.logger")` is needed: the tests read `logger.info` call arguments directly.
    - **Key Changes:**
        - `src/main.py`: import `Fore`; both `Shutting down...` log lines are f-strings.
        - `tests/test_main.py`: `TestMain` and `TestRunBot` `test_keyboard_interrupt_log_has_no_literal_fore`.
    - **Notes:** The f-string puts a real ANSI code in the log line, as the issue asks.

- [ ] **1.2** F146: health status goes through the logger
    - **Context:**
        - **Why:** `display_health_status` writes to stdout with `print()`, so the lines are not in the log file.
        - **Architecture:** `logger = get_logger("addarr.health")` already exists in `src/services/health.py`.
        - **Key refs:** `src/services/health.py:28-65`; `tests/test_services/test_health_service.py` `TestDisplayHealthStatus` (~line 31).
        - **Watch out:** The four old tests read `capsys`; rewrite them to patch `src.services.health.logger`. `main.py` uses the return value.
    - **Scope:** All 11 `print()` calls in `health.py`.
    - **Touches:** `src/services/health.py`, `tests/test_services/test_health_service.py`
    - **Action items:**
        - [RED] Rewrite the four display tests to assert logger calls and the return value.
        - [RED] Add `test_health_output_goes_to_logger_not_stdout` with `capsys` (`out == ""`), healthy and unhealthy.
        - [GREEN] Replace `print()` with `logger.info` / `warning` / `error`; drop colour codes; remove the `colorama` import if unused.
    - **Success:** New test fails before, passes after; `tests/test_services/test_health_service.py` green.

- [ ] **1.3** F144: disk check covers every enabled app
    - **Context:**
        - **Why:** `get_disk_space()` returns the first app's drives, so Sonarr and Lidarr drives get no warning in one-container-per-app setups.
        - **Architecture:** Same loop over radarr, sonarr, lidarr; collect all answers; dedupe by `path`, first app wins; a drive without `path` is kept.
        - **Key refs:** `src/services/health.py:451-475`; `src/bot/handlers/system.py:166` (docstring); `TestGetDiskSpace` in `tests/test_services/test_health_service.py`.
        - **Watch out:** Three old tests assume "first enabled only" (`..._from_first_enabled`, `..._skips_disabled_services` with `assert_called_once_with("sonarr")`, `..._falls_through_on_error` with `call_count == 2`). Update them. Keep `finally: await client.close()` per client.
    - **Scope:** `get_disk_space` and two docstrings.
    - **Touches:** `src/services/health.py`, `src/bot/handlers/system.py`, `tests/test_services/test_health_service.py`
    - **Action items:**
        - [RED] `test_returns_drives_of_every_enabled_app` (radarr `/movies`, sonarr `/tv`).
        - [RED] `test_shared_path_appears_once` and `test_drive_without_path_is_kept`.
        - [RED] Update the three old tests.
        - [GREEN] Rewrite `get_disk_space`; update docstrings.
    - **Success:** New tests fail before, pass after; health and `tests/test_handlers/test_system_handler.py` green.

- [ ] **1.4** F145: prerun works without pip
    - **Context:**
        - **Why:** In a uv venv `pip list` prints nothing, `json.loads` fails, every dependency counts as missing and startup stops. The install step opens `requirements.txt` relative to the cwd.
        - **Architecture:** `get_installed_packages()` reads `importlib.metadata.distributions()` and still returns a set of names with `-`/`_` variants, so `check_dependencies` is unchanged.
        - **Key refs:** `src/utils/prerun.py:86` (`parse_requirements`), `:112-134`, `:164`; `tests/test_utils/test_prerun.py` `TestGetInstalledPackages`, `TestCheckDependencies`.
        - **Watch out:** Skip a distribution whose `Name` is missing. Do not import `src.config.settings` here (ADR 0005). Keep `subprocess` for `check_call`. Rewrite the four old pip-JSON tests; the error test keeps the `"Error getting installed packages"` output check.
    - **Scope:** One method, one default argument, one install call.
    - **Touches:** `src/utils/prerun.py`, `tests/test_utils/test_prerun.py`
    - **Action items:**
        - [RED] `test_finds_packages_when_pip_list_is_empty` (patched `subprocess.run` returns `""`; `pytest` found).
        - [RED] `test_skips_distribution_without_name`.
        - [RED] `test_install_uses_absolute_requirements_path` (equals `os.path.join(checker.root_dir, "requirements.txt")`).
        - [RED] `test_parse_requirements_default_is_independent_of_cwd` (`monkeypatch.chdir(tmp_path)`).
        - [RED] Rewrite the four old pip-JSON tests against `metadata.distributions`.
        - [GREEN] Implement; remove `import json`.
    - **Success:** New tests fail before, pass after; `scripts/test_runner.py utils --coverage` shows no missed line in `prerun.py`.

- [ ] **1.5** F147 log cap and F148 README memory note
    - **Context:**
        - **Why:** Docker console logs grow without limit. The 256M limit is reached at about 7000 movies because `GET /movie` loads the library (`src/api/radarr.py:287`).
        - **Architecture:** Compose `logging:` with `json-file`. The limit stays 256M; only the README changes for F148 (decided 2026-10-28).
        - **Key refs:** `docker-compose.yml:7`, `:44`; `README.md` Docker Compose section (~line 377); `tests/test_docker_compose.py`; `tests/test_architecture/test_repo_docs.py`.
        - **Watch out:** `test_has_resource_limits` must still see `256M`. Check whether `test_repo_docs.py` pins README text.
    - **Scope:** One compose block, one README note.
    - **Touches:** `docker-compose.yml`, `README.md`, `tests/test_docker_compose.py`
    - **Action items:**
        - [RED] `test_logging_is_capped`: driver `json-file`, `max-size` `10m`, `max-file` `3`.
        - [GREEN] Add the `logging:` block.
        - [GREEN] Add the README note: about 7000+ movies need a memory limit above 256M.
    - **Success:** Test fails before, passes after; compose and architecture tests green.

- [ ] **1.6** F140: exit when Telegram polling stops
    - **Context:**
        - **Why:** After InvalidToken the polling task dies but `start()` keeps looping, so the bot idles forever.
        - **Architecture:** `_polling_stopped()` is true when `not updater.running` or the private polling task is done. `start()` raises `RuntimeError("Telegram polling stopped unexpectedly")`; `start_bot` stops the bot and runs `sys.exit(1)`; Docker restarts it.
        - **Key refs:** `src/main.py:258-260` (loop); `.venv` `telegram/ext/_updater.py:376` and `_utils/networkloop.py:182` (InvalidToken re-raised, `_running` untouched); `tests/test_main.py` `_make_mock_application`, `TestStart`.
        - **Watch out:** Read the task with `getattr(updater, "_Updater__polling_task", None)` and a one-line comment saying why (confirmed at step 3b). Add `app.updater._Updater__polling_task` with `done.return_value = False` to `_make_mock_application`, or every old test sees a truthy `MagicMock`. A normal stop sets `_stop_requested` first, so it is not a failure.
    - **Scope:** One helper and one check in the loop.
    - **Touches:** `src/main.py`, `tests/test_main.py`
    - **Action items:**
        - [RED] `test_loop_exits_when_updater_stops`, `test_loop_exits_when_polling_task_done`.
        - [RED] `test_stop_requested_is_not_a_polling_failure`.
        - [RED] `test_updater_keeps_private_polling_task_attribute` (real `Application.builder().token("123:abc").build()`).
        - [GREEN] Implement `_polling_stopped` and the loop check.
    - **Success:** First two tests fail before, pass after; `tests/test_main.py` green.

- [ ] **1.7** F141: heartbeat file and healthcheck
    - **Context:**
        - **Why:** `pgrep -f "python.*run.py"` matches PID 1, so the healthcheck never fails when the loop stops.
        - **Architecture:** `HEARTBEAT_FILE` in `src/definitions.py` (env `ADDARR_HEARTBEAT_FILE`, default `<tempdir>/addarr-heartbeat`). The loop touches it from loop entry and every 10 ticks (`HEARTBEAT_EVERY = 10`). Healthcheck: `test $(( $(date +%s) - $(stat -c %Y "${ADDARR_HEARTBEAT_FILE:-/tmp/addarr-heartbeat}") )) -lt 60`.
        - **Key refs:** `src/main.py` loop; `Dockerfile:29-31`; `docker-compose.yml:35-40`; `tests/test_dockerfile.py`, `tests/test_docker_compose.py`, `tests/test_definitions.py`.
        - **Watch out:** In compose use `CMD-SHELL` and write `$` as `$$`. A failed touch logs one warning (`self._heartbeat_warned`) and never stops the loop. Keep `interval`, `timeout`, `start_period`, `retries`. Dockerfile line 30 may hold the Dockerfile's own pip text; leave it.
    - **Scope:** One constant, one method, two healthcheck commands.
    - **Touches:** `src/definitions.py`, `src/main.py`, `Dockerfile`, `docker-compose.yml`, `tests/test_main.py`, `tests/test_definitions.py`, `tests/test_dockerfile.py`, `tests/test_docker_compose.py`
    - **Action items:**
        - [RED] `test_loop_touches_heartbeat_file`, `test_heartbeat_refreshed_every_ten_ticks`, `test_heartbeat_write_failure_warns_once`.
        - [RED] `test_heartbeat_file_default_and_env_override`.
        - [RED] `test_healthcheck_checks_heartbeat_age` in the Dockerfile and compose tests (`stat -c %Y`, `-lt 60`, no `pgrep`).
        - [GREEN] Implement constant, method, loop call and both commands.
        - [GREEN] Smoke-run the shell command with `sh`: fresh file exits 0; file touched 2 minutes ago and missing file exit non-zero.
    - **Success:** New tests fail before, pass after; the smoke check behaves as listed.

- [ ] **1.8** F142: clean shutdown on SIGTERM
    - **Context:**
        - **Why:** The SIGTERM handler runs `stop()` as a side task; `asyncio.run` cancels it before `application.shutdown()`, and the aiohttp sessions stay open. `Updater.stop()` also re-raises the InvalidToken of a dead polling task, which skips `application.stop()` and `shutdown()` today.
        - **Architecture:** `stop()` is idempotent (`asyncio.Lock`, `_stopped` set only when `application` exists) and runs each step on its own guard. `start_bot` awaits `bot.stop()` after `bot.start()` returns. `MediaService.close()` and `BazarrService.close()` close the long-lived `BaseApiClient` sessions.
        - **Key refs:** `src/main.py:266-287` (`stop`), `:294-301` (`start_bot`), `:314`; `src/services/media.py` `_radarr/_sonarr/_lidarr`; `src/services/bazarr.py` `_client`; `src/api/base.py:92` (`close`).
        - **Watch out:** Not `TransmissionService` (per-call session). Do not set `_stopped` when `application is None` (a signal during start-up). `test_error_swallowed` must still pass. No change to `SINGLETON_CLASSES` or `reset_singletons`.
    - **Scope:** `stop`, `start_bot`, two `close()` methods.
    - **Touches:** `src/main.py`, `src/services/media.py`, `src/services/bazarr.py`, `tests/test_main.py`, `tests/test_services/test_media_service.py`, `tests/test_services/test_bazarr_service.py`
    - **Action items:**
        - [RED] `test_stop_twice_shuts_down_once`, `test_shutdown_runs_when_updater_stop_raises`, `test_stop_before_application_does_not_set_stopped`.
        - [RED] `test_stop_closes_client_sessions`; `TestMain::test_sigterm_runs_shutdown_before_exit`.
        - [RED] `MediaService().close()` closes configured clients and skips `None`; `BazarrService().close()` closes the client.
        - [GREEN] Implement the guards, the lock, `start_bot` change and both `close()` methods.
    - **Success:** New tests fail before, pass after; `tests/test_main.py` and both service test files green.

- [ ] **1.9** Whole-issue verification
    - **Context:**
        - **Why:** The acceptance criteria end with `pytest`, `flake8` and `mypy src/` passing.
        - **Architecture:** `addarr-workflow` flow `preflight`, then the create-pr flow.
        - **Key refs:** `.claude/skills/addarr-workflow/references/preflight.md`.
        - **Watch out:** Every command runs under the suite lock. The coverage gate is 100%.
    - **Scope:** Verification only.
    - **Touches:** `docs/issues/issue-211/TASKS.md`
    - **Action items:**
        - [GREEN] Run the full preflight; fix findings.
        - [GREEN] Run `graphify update .`.
    - **Success:** Preflight passes; every box above is ticked with completion metadata.
