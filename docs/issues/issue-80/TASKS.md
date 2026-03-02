# Issue #80: Add Tests for Files Excluded from Coverage Measurement

## Summary

Close the coverage gap by adding tests for 5 files currently excluded from `.coveragerc`, gap-filling 2 existing test files, and removing the exclusions. ~140 new tests across 4 new + 2 existing test files.

---

### Phase 1: Simple Utility Tests (2 tasks)

**Goal:** Cover the two simplest source files — pure display functions and a YAML file handler.

- [x] **1.1** Test splash screen utilities (`splash.py`)
    - **Context:**
        - **Why:** `src/utils/splash.py` (134 lines, 5 functions) is excluded from coverage with zero tests. All functions are pure display — print to stdout or return strings. Simplest starting point.
        - **Architecture:** Functions use `colorama` for formatting and `config.get()` for reading settings. Config is already mocked via conftest's `MockConfig` injection into `sys.modules["src.config.settings"]`.
        - **Key refs:** `src/utils/splash.py:16-134` — five functions: `get_splash_screen()`, `show_splash_screen()`, `show_version()`, `show_welcome_screen()`, `show_token_help()`
        - **Watch out:** `show_welcome_screen()` reads three config values (`logging.debug`, `security.enableAdmin`, `language`) — test both enabled and disabled branches. Use `capsys` not `mock_open` for stdout capture. Patch `platform.python_version()` and `platform.platform()` for deterministic output.
    - **Scope:** Create `tests/test_utils/test_splash.py` covering all 5 functions, both branches of config-dependent output
    - **Touches:** `tests/test_utils/test_splash.py` (new)
    - **Action items:**
        - [RED] Write tests for `get_splash_screen` return value (non-empty, contains REFRESH EDITION)
        - [RED] Write tests for `show_splash_screen` stdout output (capsys)
        - [RED] Write tests for `show_version` output (version string, repo URL)
        - [RED] Write tests for `show_welcome_screen` — default config (debug disabled, admin disabled, language en-us), enabled variants, platform info, CLI commands, Telegram commands, resource URLs
        - [RED] Write tests for `show_token_help` — BotFather instructions, config example, wiki URL
        - [GREEN] All tests should pass immediately against existing source — verify 100% coverage
    - **Success:** `pytest tests/test_utils/test_splash.py --cov=src/utils/splash --cov-report=term-missing --no-cov-on-fail -q` shows 100%, ~17 tests pass
    - **Completed:** 2026-03-02
    - **Learnings:**
        - Coverage CLI needs a temp .coveragerc to verify files currently in the omit list — the default `.coveragerc` omits `splash.py`, so `--cov=src/utils/splash` reports 0%. Used `/tmp/coveragerc_splash` with explicit `source`/`include` to confirm 100%.
        - All 5 functions are pure display (return string or print to stdout), so no mocking needed beyond `platform.*` and `config` for deterministic output.
        - Flake8 E741 catches `l` as ambiguous variable name in list comprehensions — use `line` instead.
    - **Key Changes:**
        - Created `tests/test_utils/test_splash.py` — 29 tests across 5 test classes
        - Covers: `get_splash_screen`, `show_splash_screen`, `show_version`, `show_welcome_screen` (default config, debug enabled, admin enabled, custom language, CLI commands, Telegram commands, resource URLs), `show_token_help`
    - **Notes:** Coverage verification for omitted files requires temp .coveragerc until task 4.3 removes the omit entries

- [x] **1.2** Test config handler utilities (`config_handler.py`)
    - **Context:**
        - **Why:** `src/utils/config_handler.py` (118 lines) is excluded from coverage with zero tests. `ConfigHandler` manages YAML config file operations — used by `PreRunChecker` and `SetupWizard`.
        - **Architecture:** Class-based with `__init__(colors)` accepting a colors object (colorama or dummy). Uses `ruamel.yaml` for YAML, `shutil.copy2` for file ops, `os.makedirs` for backup dir. Global `config_handler = ConfigHandler(None)` instance at module level.
        - **Key refs:** `src/utils/config_handler.py:26-117` — `ConfigHandler` class with 6 methods: `__init__`, `create_from_example`, `create_backup`, `load_config`, `save_config`, `update_value`
        - **Watch out:** Use `tmp_path` for real file I/O instead of mocking file operations — tests are more reliable with actual files. Mock `datetime.now()` for deterministic backup timestamps. The `colors` param can be `None` (global instance) — test that error paths still work with a mock colors object.
    - **Scope:** Create `tests/test_utils/test_config_handler.py` covering all methods + global instance
    - **Touches:** `tests/test_utils/test_config_handler.py` (new)
    - **Action items:**
        - [RED] Write tests for `__init__` — sets paths correctly
        - [RED] Write tests for `create_from_example` — copies file, backs up existing, handles errors
        - [RED] Write tests for `create_backup` — timestamped backup, creates dir, returns "" when no config
        - [RED] Write tests for `load_config` — valid YAML returns dict, errors return {}
        - [RED] Write tests for `save_config` — backs up then writes, error returns False
        - [RED] Write tests for `update_value` — single key, nested keys, creates intermediate keys
        - [RED] Write tests for global `config_handler` instance
        - [GREEN] All tests pass against existing source — verify 100% coverage
    - **Success:** `pytest tests/test_utils/test_config_handler.py --cov=src/utils/config_handler --cov-report=term-missing --no-cov-on-fail -q` shows 100%, ~22 tests pass
    - **Completed:** 2026-03-02
    - **Learnings:**
        - `tmp_path` fixture makes file I/O tests clean — no mocking of `open`/`shutil` needed, just wire handler paths to tmp_path
        - `update_value` is a static-like method (only uses `config` param, not `self`) — can call with `None` as self for isolated testing
        - `ruamel.yaml` YAML() preserves comments/formatting — `load_config` returns CommentedMap (dict-compatible), not plain dict
    - **Key Changes:**
        - Created `tests/test_utils/test_config_handler.py` — 25 tests across 7 test classes
        - Covers: `__init__`, `create_from_example` (copy, backup existing, error), `create_backup` (timestamp, dir creation, no config, content preservation), `load_config` (valid, missing, invalid YAML), `save_config` (write, backup, error), `update_value` (single key, nested, intermediate creation, sibling preservation), global instance
    - **Notes:** The `colors` mock uses empty strings for Fore attributes — production uses colorama Fore constants

---

### Phase 2: PreRunChecker Tests (1 task)

**Goal:** Cover the pre-run dependency and config checking module.

- [x] **2.1** Test PreRunChecker and ColorHandler (`prerun.py`)
    - **Context:**
        - **Why:** `src/utils/prerun.py` (209 lines) is excluded from coverage with zero tests. Contains `ColorHandler` (colorama fallback) and `PreRunChecker` (dependency checking, config existence, user prompts). Most complex utility module due to subprocess calls and interactive input loops.
        - **Architecture:** `ColorHandler` tries `from colorama import Fore, Style, init` and falls back to `DummyFore`/`DummyStyle` on ImportError. `PreRunChecker` lazy-imports `config_handler` and `SetupWizard` inside methods. Uses `subprocess.run` for `pip list` and `subprocess.check_call` for `pip install`. User prompts via `builtins.input()`.
        - **Key refs:** `src/utils/prerun.py:18-47` (ColorHandler), `src/utils/prerun.py:50-204` (PreRunChecker), `src/utils/prerun.py:207-208` (global instance)
        - **Watch out:** `check_config_exists` lazy-imports `config_handler` from `.config_handler` (relative) and `SetupWizard` from `src.setup` — must patch at those import paths. The `while True` input loops need `side_effect` sequences with invalid inputs followed by valid ones to test the loop. `parse_requirements` reads a real file path — use `tmp_path` to create test requirements files. `get_installed_packages` calls `subprocess.run` — mock to avoid real pip calls.
    - **Scope:** Create `tests/test_utils/test_prerun.py` covering ColorHandler, PreRunChecker (all 5 methods), and global instance
    - **Touches:** `tests/test_utils/test_prerun.py` (new)
    - **Action items:**
        - [RED] Write tests for `ColorHandler.__init__` — with colorama (real import), with ImportError (DummyFore/DummyStyle)
        - [RED] Write tests for `ColorHandler.reload` — successful reload, ImportError no-op
        - [RED] Write tests for `DummyFore`/`DummyStyle` attributes are empty strings
        - [RED] Write tests for `PreRunChecker.__init__` — colors, root_dir, config_path
        - [RED] Write tests for `parse_requirements` — reads file, strips versions (`>=`, `<=`, `==`), strips comments, skips blanks, lowercases, FileNotFoundError returns core_deps, merges with core deps
        - [RED] Write tests for `get_installed_packages` — parses JSON, normalizes names (hyphen/underscore), subprocess error returns empty set
        - [RED] Write tests for `check_dependencies` — all installed, missing+install, missing+decline, install failure, colorama reload trigger, empty requirements, invalid input loop
        - [RED] Write tests for `check_config_exists` — config exists, missing+wizard, missing+create_from_example fails, missing+decline, invalid input loop, sets config_handler.colors
        - [RED] Write tests for `run_checks` — both pass, deps fail, config fail
        - [RED] Write test for global `prerun_checker` instance
        - [GREEN] All tests pass against existing source — verify 100% coverage
    - **Success:** `pytest tests/test_utils/test_prerun.py --cov=src/utils/prerun --cov-report=term-missing --no-cov-on-fail -q` shows 100%, ~35 tests pass
    - **Completed:** 2026-03-02
    - **Learnings:**
        - `patch.dict("sys.modules", {"colorama": None})` forces ImportError on `from colorama import ...` — cleaner than patching builtins.__import__
        - Lazy imports inside methods (`from .config_handler import config_handler`) must be patched at the source module (`src.utils.config_handler.config_handler`), not at the caller
        - `while True` input loops need `side_effect` lists with invalid entries followed by a valid terminator (`["invalid", "x", "n"]`) to test the re-prompt path
        - `subprocess.CalledProcessError(1, "pip")` requires both returncode and cmd args
    - **Key Changes:**
        - Created `tests/test_utils/test_prerun.py` — 41 tests across 10 test classes
        - Covers: DummyFore/DummyStyle, ColorHandler init/reload (with and without colorama), PreRunChecker init, parse_requirements (versions, comments, blanks, lowercase, core deps merge, dedup, FileNotFoundError), get_installed_packages (JSON parse, normalization, errors), check_dependencies (all installed, install yes/no, failure, colorama reload, invalid input, hyphen/underscore matching), check_config_exists (exists, wizard, create_from_example fail, decline, invalid input), run_checks (all combos), global instance
    - **Notes:** `check_config_exists` patches `os.path.exists` globally — safe because only the checker's config_path is checked in the function

---

### Phase 3: AddarrBot Tests (1 task)

**Goal:** Cover the main bot application module — the most complex target.

- [x] **3.1** Test AddarrBot class and entry points (`main.py`)
    - **Context:**
        - **Why:** `src/main.py` (258 lines) is excluded from coverage with zero tests. Contains `AddarrBot` class (init, initialize, _add_handlers, start, stop), `main()` async entry point, and `run_bot()` sync wrapper. Heaviest mock surface area due to 11 handler classes and Application builder chain.
        - **Architecture:** `AddarrBot.initialize()` calls `show_welcome_screen`, `check_config`, health checks, builds `Application` via builder pattern, adds handlers, then `application.initialize()`. Error handling: `InvalidToken` triggers `os.execl` restart (MUST patch), `NetworkError` and generic exceptions use error handler functions. `_add_handlers()` conditionally registers Transmission/SABnzbd based on `config.get("transmission/sabnzbd", {}).get("enable", False)`. `start()` has a `while self._running` loop — break by setting `_running=False` via `asyncio.sleep` side_effect. `main()` registers signal handlers with Windows fallback (`NotImplementedError`).
        - **Key refs:** `src/main.py:46-204` (AddarrBot class), `src/main.py:206-242` (main), `src/main.py:245-257` (run_bot)
        - **Watch out:** `os.execl` replaces the process — MUST be patched. `asyncio.run` cannot nest inside pytest-asyncio — test `run_bot()` by patching `asyncio.run`. The `while self._running` loop in `start()` needs a side_effect on `asyncio.sleep` that sets `_running=False` after first call. `main()` uses `asyncio.get_running_loop()` which returns the pytest event loop — mock the loop object. Signal handler registration uses `loop.add_signal_handler` which raises `NotImplementedError` on Windows — test both paths.
    - **Scope:** Create `tests/test_main.py` covering AddarrBot lifecycle, handler registration, error paths, main(), run_bot()
    - **Touches:** `tests/test_main.py` (new)
    - **Action items:**
        - [RED] Write tests for `AddarrBot.__init__` — application None, _running False, health_checker is health_service
        - [RED] Write tests for `initialize()` — happy path (full lifecycle), health checks fail (continues), missing token (ValueError), InvalidToken+restart (os.execl), InvalidToken+re-raise, NetworkError, generic exception, outer exception logging
        - [RED] Write tests for `_add_handlers()` — all 9 always-on handlers registered, Transmission disabled/enabled, SABnzbd disabled/enabled, both enabled, handler error re-raises
        - [RED] Write tests for `start()` — starts app+polling+health checker, sets _running, while-loop breaks, error re-raises
        - [RED] Write tests for `stop()` — full shutdown, application is None, updater not running, error swallowed
        - [RED] Write tests for `main()` — start_bot error path (stop+sys.exit), signal handler registration, Windows fallback (NotImplementedError), KeyboardInterrupt, generic exception
        - [RED] Write tests for `run_bot()` — calls asyncio.run, KeyboardInterrupt, generic exception
        - [GREEN] All tests pass against existing source — verify 100% coverage
    - **Success:** `pytest tests/test_main.py --cov=src/main --cov-report=term-missing --no-cov-on-fail -q` shows 100%, ~50 tests pass
    - **Completed:** 2026-03-02
    - **Learnings:**
        - `patch.multiple("src.main", **dict)` requires SHORT attribute names (`StartHandler`), not dotted paths (`src.main.StartHandler`) — the module target is already the first arg
        - Breaking `while self._running` loops in tests: use `asyncio.sleep` side_effect that sets `_running=False` on first call
        - `os.execl` replaces the process entirely — when mocked, execution continues past it so the outer `except` may catch unexpected flow; use `try/except` wrapper in test
        - For `main()` signal handler tests, mock `asyncio.get_running_loop` to return a mock loop and verify `add_signal_handler` calls; simulate Windows with `NotImplementedError` side_effect
        - Line 213 (`await bot.start()`) required a separate test where `initialize` succeeds but `start` fails to reach that line
    - **Key Changes:**
        - Created `tests/test_main.py` — 31 tests across 8 test classes
        - Covers: `AddarrBot.__init__`, `initialize()` (happy path, health fail, missing token, InvalidToken+restart, InvalidToken+reraise, NetworkError, generic exception), `_add_handlers()` (9 always-on, transmission/sabnzbd enabled/disabled, both enabled, handler error), `start()` (app+polling, running flag, error), `stop()` (full shutdown, None app, updater not running, error swallowed), `main()` (start_bot init error, start error, signal registration, Windows fallback, KeyboardInterrupt, generic exception), `run_bot()` (asyncio.run, KeyboardInterrupt, generic exception)
    - **Notes:** The `HANDLER_PATCHES` dict is reused across test classes via `patch.multiple` — if new handlers are added to main.py, add them to this dict

---

### Phase 4: Gap-Fill + Coverage Config (3 tasks)

**Goal:** Fill remaining coverage gaps in existing test files and remove `.coveragerc` exclusions.

- [x] **4.1** Gap-fill wizard tests (`test_wizard.py`)
    - **Context:**
        - **Why:** `src/setup/wizard.py` is at ~68% coverage — existing tests cover `__init__`, `run`, `_async_setup`, partial `_reset_config`, partial `configure_services`, and `main()`. Missing: `_update_config_value`, `_create_directories`, `_configure_service`, `_configure_required_value`, `_backup_config`, `_reset_config` success/example-missing/exception paths, `configure_services` Transmission auth + SABnzbd branches.
        - **Architecture:** All wizard methods follow the same pattern as existing tests — `@patch("src.setup.wizard.config_handler")` for init, mock questionary for user input, `AsyncMock` for async service config functions.
        - **Key refs:** `src/setup/wizard.py:64-66` (_update_config_value), `src/setup/wizard.py:126-134` (_create_directories), `src/setup/wizard.py:136-159` (_configure_service), `src/setup/wizard.py:161-168` (_configure_required_value), `src/setup/wizard.py:170-177` (_backup_config), `src/setup/wizard.py:206-227` (_reset_config success/error paths), `src/setup/wizard.py:258-289` (configure_services Transmission auth + SABnzbd)
        - **Watch out:** `_reset_config` success path calls `self.run()` recursively — mock it to prevent infinite loop. `_configure_service` line 146 `if enabled:` is always True (enabled is hardcoded to True on line 141) but the except block on line 154 catches config errors and sets `enable=False`. `configure_services` Transmission auth needs 7 sequential `questionary.confirm.ask()` calls — use `side_effect` list carefully.
    - **Scope:** Add ~15 tests to existing `tests/test_setup/test_wizard.py`
    - **Touches:** `tests/test_setup/test_wizard.py` (append)
    - **Action items:**
        - [RED] Write tests for `_update_config_value` — delegates to config_handler.update_value
        - [RED] Write tests for `_create_directories` — creates log dir and translations dir
        - [RED] Write tests for `_configure_service` — arr service (enables + features), non-arr (no features), exception (sets enable=False)
        - [RED] Write tests for `_configure_required_value` — arr service passes default_config, non-arr passes None
        - [RED] Write tests for `_backup_config` — delegates to create_backup
        - [RED] Write tests for `_reset_config` — success (loads example, saves, calls run), missing example (sys.exit(1)), generic exception (sys.exit(1))
        - [RED] Write tests for `configure_services` — Transmission with auth (username/password), SABnzbd config
        - [GREEN] All tests pass — verify 100% coverage of wizard.py
    - **Success:** `pytest tests/test_setup/test_wizard.py --cov=src/setup/wizard --cov-report=term-missing --no-cov-on-fail -q` shows 100%, ~15 new tests pass
    - **Completed:** 2026-03-02
    - **Learnings:**
        - `_configure_required_value` passes `self.config` (the current dict) to `configure_required_value`, then assigns the return value back — can't assert exact first arg since it's the mutable dict at call time; verify via `call_args` instead
        - `_reset_config` success path calls `self.run()` recursively — MUST mock `wizard.run` to prevent infinite loop
        - For Transmission auth in `configure_services`, `questionary.confirm` returns the same mock each time — use `ask.side_effect` list to sequence Yes/No answers across all 6 confirm calls
        - `_create_directories` can be verified by mocking `Path` since actual dir creation isn't needed in tests
    - **Key Changes:**
        - Added 12 tests to `tests/test_setup/test_wizard.py` across 6 new test classes
        - Covers: `_update_config_value`, `_create_directories`, `_configure_service` (arr/non-arr/exception), `_configure_required_value` (arr/non-arr), `_reset_config` success/missing-example/exception, `configure_services` Transmission auth + SABnzbd
    - **Notes:** wizard.py now at 100% coverage (was 69%)

- [x] **4.2** Gap-fill service_config tests (`test_service_config.py`)
    - **Context:**
        - **Why:** `src/setup/service_config.py` is at ~98% — missing line 174: the SABnzbd skip-validation return path (when connection fails and user declines retry for SABnzbd).
        - **Architecture:** Same mock pattern as existing `test_retry_then_skip` (line 162-180 of existing tests) but with `service="sabnzbd"` instead of `"radarr"`.
        - **Key refs:** `src/setup/service_config.py:174-189` — SABnzbd branch inside the `if not retry:` block, returns config with `enable: False` and `onlyAdmin: True`
        - **Watch out:** The existing `test_retry_then_skip` only tests with `"radarr"` (hits the else branch on line 190). Need to test `"sabnzbd"` which hits the if branch on line 174.
    - **Scope:** Add 1-2 tests to existing `tests/test_setup/test_service_config.py`
    - **Touches:** `tests/test_setup/test_service_config.py` (append)
    - **Action items:**
        - [RED] Write `test_sabnzbd_retry_then_skip` — validation fails, retry=False, returns SABnzbd config with `enable: False`, `onlyAdmin: True`
        - [GREEN] Test passes — verify 100% coverage of service_config.py
    - **Success:** `pytest tests/test_setup/test_service_config.py --cov=src/setup/service_config --cov-report=term-missing --no-cov-on-fail -q` shows 100%
    - **Completed:** 2026-03-02
    - **Learnings:**
        - Statement coverage was already 100% but branch coverage was 96% — two missing branches: `83->86` (unknown service fallthrough in `get_default_service_config`) and `172->95` (retry=True loop back in `get_valid_service_config`)
        - Branch coverage reveals gaps that statement coverage misses — always check with `--cov-branch`
        - For retry loop testing, side_effect lists must account for all questionary calls across all iterations (e.g., 3 confirm calls: ssl1, retry, ssl2)
    - **Key Changes:**
        - Added `test_unknown_service_fallthrough` to `TestGetDefaultServiceConfig` — covers `83->86` branch
        - Added `test_sabnzbd_retry_then_skip` to `TestGetValidServiceConfig` — covers SABnzbd skip-validation path
        - Added `test_validation_fail_retry_then_succeed` to `TestGetValidServiceConfig` — covers `172->95` retry loop branch
    - **Notes:** 21 tests total (was 18), 100% statement + branch coverage (52 stmts, 22 branches, 0 missing)

- [x] **4.3** Update `.coveragerc` and verify full suite
    - **Context:**
        - **Why:** With all tests in place, remove the 5 file exclusions from `.coveragerc` so coverage measurement includes them. The `fail_under = 100` setting will enforce they stay covered.
        - **Architecture:** Simple config edit — remove 5 lines from the `omit` list. Keep `src/__init__.py` (empty) and `src/config/settings.py` (reads from disk, mocked at sys.modules level).
        - **Key refs:** `.coveragerc:3-13` — current omit list
        - **Watch out:** Run full test suite AFTER the edit — if any line is uncovered, `fail_under = 100` will fail the run. This is the final verification gate.
    - **Scope:** Edit `.coveragerc`, run full suite
    - **Touches:** `.coveragerc`
    - **Action items:**
        - [GREEN] Remove `src/main.py`, `src/setup/wizard.py`, `src/utils/config_handler.py`, `src/utils/prerun.py`, `src/utils/splash.py` from the omit list
        - [GREEN] Run `pytest --cov=src --cov-report=term-missing --tb=short` — must show 100% coverage, all tests pass
        - [GREEN] Run `flake8 .` — no lint errors
    - **Success:** Full test suite passes with 100% coverage, no regressions, no lint errors
    - **Completed:** 2026-03-02
    - **Learnings:**
        - Removing 5 files from omit exposed 568 additional statements to coverage measurement — all already at 100% from tasks 1.1-4.2
        - `fail_under = 100` in `.coveragerc` acts as an enforcement gate — any regression will fail CI
    - **Key Changes:**
        - Removed 5 file exclusions from `.coveragerc` omit list: `src/main.py`, `src/setup/wizard.py`, `src/utils/config_handler.py`, `src/utils/prerun.py`, `src/utils/splash.py`
        - Kept `src/__init__.py` (empty) and `src/config/settings.py` (sys.modules-level mock)
    - **Notes:** Full suite: 1380 tests, 4723 statements, 100% coverage, 0 lint errors, 12s runtime
