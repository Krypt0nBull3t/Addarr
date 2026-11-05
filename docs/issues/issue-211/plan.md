# Issue 211: Bot dies silently; startup checks and healthcheck are fragile: Implementation Plan

**Goal:** Fix audit findings F140 to F148 so the bot exits when polling dies, Docker detects a dead
loop, shutdown is clean, and the startup checks and logs are correct.

**Architecture:** Nine small fixes, one TDD task each, in the existing layers. No new module. One new
constant (`HEARTBEAT_FILE`) and two small `close()` methods.

**Tech Stack:** Python 3.11, python-telegram-bot 22.8, aiohttp, pytest, busybox sh (Alpine).

**Spec:** `docs/issues/issue-211/design.md`

## Conventions for every task

- `<py>` = `.venv/bin/python` of this worktree.
- `<lock>` = `~/.local/share/agent-suite/with-suite-lock.sh addarr/$AO_SESSION_ID --`.
  Every pytest run and every `git push` goes through it.
- Test run: `<lock> <py> -m pytest <path>::<test> -v`.
- A test must fail before its fix and pass after (Step 2 and Step 4 of each task).
- Commit message form: `fix: <what> (#211, task N)`. Stage only the task files and `TASKS.md`.

## Global Constraints

- `config["key"]` bracket access is banned in `src/` business logic: use `config.get()`.
- Flake8 max line 88 (E203, E501, W503 ignored); `mypy src/` passes; use `Optional[str]`, not `str | None`.
- `src/utils/prerun.py` must not import `src.config.settings` (ADR 0005).
- `docker-compose.yml` keeps `memory: 256M` (`tests/test_docker_compose.py::test_has_resource_limits`).
- Unit-test coverage gate stays at 100% (`ci.yml`); integration and architecture tests stay green.
- New singleton methods must not change `SINGLETON_CLASSES` or `reset_singletons`.

## Review Focus

- `stop()` called twice (signal task plus `start_bot`): the second call returns and does not shut down twice.
- `stop()` after the polling task died with `InvalidToken`: `application.shutdown()` still runs.
- `stop()` during start-up, before `application` exists: no error, no `_stopped` flag set.
- Heartbeat directory not writable: bot keeps running, one warning only.
- A drive without a `path` key in the `/diskspace` answer: kept, no crash.
- A broken distribution with no `Name` in its metadata: skipped in `get_installed_packages`.

## File Structure

- `src/main.py`: F140, F141 (loop), F142, F143.
- `src/definitions.py`: `HEARTBEAT_FILE` (F141).
- `src/utils/prerun.py`: F145.
- `src/services/health.py`: F144, F146. `src/bot/handlers/system.py`: docstring only.
- `src/services/media.py`, `src/services/bazarr.py`: `close()` (F142).
- `Dockerfile`, `docker-compose.yml`, `README.md`: F141, F147, F148.
- Tests: `tests/test_main.py`, `tests/test_utils/test_prerun.py`,
  `tests/test_services/test_health_service.py`, `tests/test_services/test_media_service.py`,
  `tests/test_services/test_bazarr_service.py`, `tests/test_dockerfile.py`,
  `tests/test_docker_compose.py`, `tests/test_definitions.py`, `tests/test_repo_docs.py` (if it pins README text).

---

### Task 1: F143 literal `{Fore.YELLOW}` in the shutdown log

**Files:**
- Modify: `src/main.py:12` (import), `:322`, `:334`
- Test: `tests/test_main.py` (`TestRunBot`, `TestMain`)

**Interfaces:** Produces `from colorama import Fore, init` in `src/main.py`.

- [ ] **Step 1: Write failing tests.**
  `TestRunBot::test_keyboard_interrupt_log_has_no_literal_fore` (patch `src.main.asyncio.run` with
  `side_effect=KeyboardInterrupt`, patch `src.main.logger`): assert no `logger.info` argument contains
  `"{Fore.YELLOW}"` and one contains `"Shutting down..."`.
  `TestMain::test_keyboard_interrupt_log_has_no_literal_fore`: same assertions for the
  `except KeyboardInterrupt` branch of `main()`, built like `test_keyboard_interrupt_stops_bot`.
- [ ] **Step 2: Run both; expect FAIL** (`"{Fore.YELLOW}"` found in the argument).
- [ ] **Step 3: Make both log lines f-strings** (`f"\n{Fore.YELLOW}Shutting down..."`) and import `Fore`.
- [ ] **Step 4: Run `tests/test_main.py`; expect PASS.**
- [ ] **Step 5: Commit** `fix: add missing f to shutdown log lines (#211, task 1)`.

### Task 2: F146 `print()` in `display_health_status`

**Files:**
- Modify: `src/services/health.py:28-65`
- Test: `tests/test_services/test_health_service.py` (`TestDisplayHealthStatus` at line ~31)

**Interfaces:** `display_health_status(results: Dict[str, List[Dict]]) -> bool` keeps signature and return value.

- [ ] **Step 1: Rewrite the four existing display tests and add one.** Patch `src.services.health.logger`.
  `test_all_healthy`: returns True, `logger.info` called, `logger.error` not called.
  `test_some_unhealthy`: returns False, `logger.error` called with a message containing
  `"Some services are not responding"`.
  New `test_health_output_goes_to_logger_not_stdout(capsys)`: `capsys.readouterr().out == ""` for a
  healthy and an unhealthy result.
- [ ] **Step 2: Run; expect FAIL** (output on stdout).
- [ ] **Step 3: Replace every `print()` in `health.py` with `logger.info`** (header, service lines,
  healthy summary), `logger.warning` for the unhealthy lines of a service, and `logger.error` for the
  "Some services are not responding" line. Drop the `Fore`/`Style` codes from these messages. Remove the
  `colorama` import if nothing else uses it.
- [ ] **Step 4: Run `tests/test_services/test_health_service.py`; expect PASS.**
- [ ] **Step 5: Commit** `fix: log health status through the logger (#211, task 2)`.

### Task 3: F144 disk check covers every enabled app

**Files:**
- Modify: `src/services/health.py:451-475`, docstring of `_handle_diskspace` in `src/bot/handlers/system.py:166`
- Test: `tests/test_services/test_health_service.py` (`TestGetDiskSpace`)

**Interfaces:** `HealthService.get_disk_space(self) -> List[Dict]`: drives of all enabled apps, one entry per `path`, first app wins.

- [ ] **Step 1: Write failing tests.**
  `test_returns_drives_of_every_enabled_app`: radarr returns `/movies`, sonarr returns `/tv`; result has both.
  `test_shared_path_appears_once`: radarr and sonarr both return `/data`; result has one `/data` entry.
  `test_drive_without_path_is_kept`: a drive dict with no `path` stays in the result.
  Update the three old tests: `..._from_first_enabled` (now every enabled app is queried and each client is
  closed), `..._skips_disabled_services` (`_get_api_client` called for sonarr and lidarr, not radarr),
  `..._falls_through_on_error` (radarr fails, sonarr and lidarr still answer).
- [ ] **Step 2: Run; expect FAIL.**
- [ ] **Step 3: Rewrite `get_disk_space`.** Loop over radarr, sonarr, lidarr; skip disabled or `None` client;
  collect each answer with `setdefault(path, drive)` when `path` is set, `append` otherwise; keep the
  `except` warning and the `finally: await client.close()`. Update the two docstrings.
- [ ] **Step 4: Run health and `tests/test_handlers/test_system_handler.py`; expect PASS.**
- [ ] **Step 5: Commit** `fix: report disk space of every enabled app (#211, task 3)`.

### Task 4: F145 prerun without pip

**Files:**
- Modify: `src/utils/prerun.py:11-15` (imports), `:86` (`parse_requirements` default), `:112-134`, `:164`
- Test: `tests/test_utils/test_prerun.py` (`TestGetInstalledPackages`, `TestCheckDependencies`, `TestParseRequirements`)

**Interfaces:**
- `get_installed_packages(self) -> Set[str]` now reads `importlib.metadata.distributions()`: lowercase name plus `-`/`_` variants; skips a distribution whose `Name` is missing.
- `parse_requirements(self, filename: Optional[str] = None)`: default `os.path.join(self.root_dir, "requirements.txt")`.

- [ ] **Step 1: Write failing tests.**
  `test_finds_packages_when_pip_list_is_empty`: patch `src.utils.prerun.subprocess.run` to return
  `stdout=""`; assert `"pytest" in checker.get_installed_packages()`.
  `test_skips_distribution_without_name`: patch `src.utils.prerun.metadata.distributions` to yield one
  object whose `metadata["Name"]` is `None` and one named `Flask`; result has `flask` and no `None`.
  `test_install_uses_absolute_requirements_path`: answer `y`, patch `subprocess.check_call`; last argument
  equals `os.path.join(checker.root_dir, "requirements.txt")` and `os.path.isabs` is true.
  `test_parse_requirements_default_is_independent_of_cwd`: `monkeypatch.chdir(tmp_path)`; result still
  holds `python-telegram-bot`.
  Rewrite the old pip-JSON tests (`test_parses_json_output`, `test_normalizes_hyphen_underscore`,
  `test_lowercases_names`, `test_subprocess_error_returns_empty_set`) against `metadata.distributions`;
  the error test patches it to raise and keeps the `"Error getting installed packages"` output check.
- [ ] **Step 2: Run; expect FAIL.**
- [ ] **Step 3: Implement.** `from importlib import metadata`; remove `import json`. Keep `subprocess`
  (still used by `check_call`). Keep the `except Exception` guard and its message.
- [ ] **Step 4: Run `tests/test_utils/test_prerun.py`; expect PASS.**
- [ ] **Step 5: Commit** `fix: prerun checks packages without pip, installs from absolute path (#211, task 4)`.

### Task 5: F147 log cap and F148 README memory note

**Files:**
- Modify: `docker-compose.yml:7` (add `logging:` under `addarr`), `README.md` (Docker section, after the file-permissions note near line 377)
- Test: `tests/test_docker_compose.py`

- [ ] **Step 1: Write failing test** `test_logging_is_capped`: `service["logging"]["driver"] == "json-file"`,
  `options["max-size"] == "10m"`, `options["max-file"] == "3"`.
- [ ] **Step 2: Run; expect FAIL** (`KeyError: 'logging'`).
- [ ] **Step 3: Add the `logging:` block.** Add a README note in the Docker Compose section: a Radarr
  library of about 7000+ movies needs a memory limit above 256M (the full-library `GET /movie` is loaded
  at once); raise `deploy.resources.limits.memory` in `docker-compose.yml`. Compose keeps `256M`.
- [ ] **Step 4: Run `tests/test_docker_compose.py` and `tests/test_architecture/test_repo_docs.py`; expect PASS.**
- [ ] **Step 5: Commit** `fix: cap Docker logs and document memory for large libraries (#211, task 5)`.

### Task 6: F140 exit when polling stops

**Files:**
- Modify: `src/main.py` (`start`, new `_polling_stopped`)
- Test: `tests/test_main.py` (`_make_mock_application`, `TestStart`)

**Interfaces:** `AddarrBot._polling_stopped(self) -> bool`: `True` when `not updater.running` or the
polling task is done. `start()` raises `RuntimeError("Telegram polling stopped unexpectedly")` from the loop.

- [ ] **Step 1: Write failing tests.**
  In `_make_mock_application` set `app.updater._Updater__polling_task` to a `MagicMock` whose
  `done.return_value` is `False`.
  `TestStart::test_loop_exits_when_updater_stops`: first sleep sets `app.updater.running = False`;
  `start()` raises `RuntimeError` matching `"polling stopped"`.
  `test_loop_exits_when_polling_task_done`: first sleep sets the task's `done.return_value = True`
  while `running` stays `True`; same assertion.
  `test_stop_requested_is_not_a_polling_failure`: set `_stop_requested = True` and `running = False`
  in the first sleep; `start()` returns without raising.
  `test_updater_keeps_private_polling_task_attribute`: build `Application.builder().token("123:abc").build()`
  and assert `hasattr(app.updater, "_Updater__polling_task")` (fails on a PTB bump that renames it).
- [ ] **Step 2: Run the first two; expect FAIL** (no `RuntimeError`, loop ends by `_running`).
- [ ] **Step 3: Implement `_polling_stopped` and the check at the top of each loop iteration**, after the
  `while` condition. Put the confirmed one-line comment above the `getattr`: PTB 22.8 keeps `updater.running`
  True when the polling task dies (InvalidToken, Conflict), the pin and a test make a rename visible.
- [ ] **Step 4: Run `tests/test_main.py`; expect PASS.**
- [ ] **Step 5: Commit** `fix: exit when Telegram polling stops (#211, task 6)`.

### Task 7: F141 heartbeat file and healthcheck

**Files:**
- Modify: `src/definitions.py` (add `HEARTBEAT_FILE`), `src/main.py` (loop, `_touch_heartbeat`),
  `Dockerfile:29-31`, `docker-compose.yml:35`
- Test: `tests/test_main.py`, `tests/test_definitions.py`, `tests/test_dockerfile.py`, `tests/test_docker_compose.py`

**Interfaces:**
- `src/definitions.py`: `HEARTBEAT_FILE: str = os.environ.get("ADDARR_HEARTBEAT_FILE", os.path.join(tempfile.gettempdir(), "addarr-heartbeat"))`.
- `src/main.py`: constant `HEARTBEAT_EVERY = 10`; `AddarrBot._touch_heartbeat(self) -> None` (touches
  `HEARTBEAT_FILE`; on `OSError` logs one warning, tracked by `self._heartbeat_warned`).
- Healthcheck command, same in both files (compose escapes `$` as `$$` and uses `CMD-SHELL`):
  `test $(( $(date +%s) - $(stat -c %Y "${ADDARR_HEARTBEAT_FILE:-/tmp/addarr-heartbeat}") )) -lt 60`

- [ ] **Step 1: Write failing tests.**
  `test_main.py::TestStart::test_loop_touches_heartbeat_file`: patch `src.main.HEARTBEAT_FILE` to a
  `tmp_path` file; run one loop iteration; assert the file exists.
  `test_heartbeat_refreshed_every_ten_ticks`: patch `Path.touch`-level helper or `os.utime` count over 21
  ticks equals 3.
  `test_heartbeat_write_failure_warns_once`: patch `HEARTBEAT_FILE` to a path inside a missing directory;
  run 21 ticks; `logger.warning` called once; the loop is not interrupted.
  `test_definitions.py::test_heartbeat_file_default_and_env_override` (reload with the env set).
  `test_dockerfile.py::test_healthcheck_checks_heartbeat_age`: the `HEALTHCHECK` command contains
  `stat -c %Y` and `-lt 60`, and does not contain `pgrep`.
  `test_docker_compose.py::test_healthcheck_checks_heartbeat_age`: `healthcheck["test"][0] == "CMD-SHELL"`,
  same content checks.
- [ ] **Step 2: Run; expect FAIL.**
- [ ] **Step 3: Implement** the constant, the method, the call every `HEARTBEAT_EVERY` ticks from loop
  entry, and the two healthcheck commands. Keep `interval`, `timeout`, `start_period`, `retries` as they are.
- [ ] **Step 4: Run the five test files; expect PASS.**
- [ ] **Step 5: Smoke check the shell command** in `sh`: it exits 0 for a fresh file, non-zero for a
  file touched 2 minutes ago (`touch -d`) and for a missing file.
- [ ] **Step 6: Commit** `fix: Docker healthcheck follows a heartbeat file (#211, task 7)`.

### Task 8: F142 clean shutdown on SIGTERM

**Files:**
- Modify: `src/main.py` (`__init__`, `stop`, new `_close_clients`, `start_bot`),
  `src/services/media.py` (`close`), `src/services/bazarr.py` (`close`)
- Test: `tests/test_main.py` (`TestStop`, `TestMain`), `tests/test_services/test_media_service.py`,
  `tests/test_services/test_bazarr_service.py`

**Interfaces:**
- `MediaService.close(self) -> None` (async): `await client.close()` for each non-`None` of `_radarr`, `_sonarr`, `_lidarr`.
- `BazarrService.close(self) -> None` (async): closes `_client` when set.
- `AddarrBot.stop()` keeps its name; it is idempotent and runs each step on its own guard:
  webhook stop, health stop, `updater.stop()` (only when `running`), `application.stop()`,
  `application.shutdown()`, `_close_clients()`.
- `start_bot` awaits `bot.stop()` after `bot.start()` returns.

- [ ] **Step 1: Write failing tests.**
  `TestStop::test_stop_twice_shuts_down_once`: two `await bot.stop()` calls; `shutdown` awaited once.
  `test_shutdown_runs_when_updater_stop_raises`: `updater.stop` raises `InvalidToken("x")`; `application.stop`
  and `application.shutdown` are still awaited.
  `test_stop_before_application_does_not_set_stopped`: `application = None`; after `stop()`, `bot._stopped`
  is `False`.
  `test_stop_closes_client_sessions`: patch `MediaService.close` and `BazarrService.close` as `AsyncMock`;
  both awaited.
  `TestMain::test_sigterm_runs_shutdown_before_exit`: `bot.start` returns after `_stop_requested` is set;
  assert `application.shutdown` awaited and the client `close` awaited before `main()` returns (the signal
  task is cancelled by `asyncio.run`, so `start_bot` must await `stop()` itself).
  Service tests: `MediaService().close()` awaits `close()` on each configured client and ignores `None`;
  `BazarrService().close()` closes the client.
- [ ] **Step 2: Run; expect FAIL.**
- [ ] **Step 3: Implement.** `self._stop_lock = asyncio.Lock()` and `self._stopped = False` in `__init__`.
  `stop()`: set `_stop_requested`; `async with self._stop_lock`; return if `_stopped` or no `application`;
  set `_stopped`; run each step through one helper that catches `Exception` and logs at debug (same message
  style as today). `start_bot`: call `await bot.stop()` after `await bot.start()`.
- [ ] **Step 4: Run `tests/test_main.py` and the two service test files; expect PASS.**
- [ ] **Step 5: Commit** `fix: await bot.stop() and close client sessions on shutdown (#211, task 8)`.

### Task 9: Whole-issue verification

- [ ] **Step 1:** Run the full preflight (`addarr-workflow` flow `preflight`, all commands under `<lock>`).
- [ ] **Step 2:** Run `graphify update .`.
- [ ] **Step 3:** Tick every box in `TASKS.md` with the required completion metadata.
