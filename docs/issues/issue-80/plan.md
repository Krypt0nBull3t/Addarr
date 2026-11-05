# Add Tests for Files Excluded from Coverage Measurement (#80)

## Context

The project reports 100% test coverage, but 7 files are excluded from `.coveragerc`'s `omit` list. Issue #79 added setup module tests, but `wizard.py` is still excluded at ~68% coverage. Four files have zero tests. This work closes the gap so the 100% metric reflects actual full coverage.

**Files currently omitted from coverage** (`.coveragerc`):
- `src/__init__.py` — empty init, keep excluded
- `src/config/settings.py` — reads from disk at import time, keep excluded
- `src/main.py` — 258 lines, zero tests ← **add tests**
- `src/setup/wizard.py` — ~68% covered ← **gap-fill**
- `src/utils/config_handler.py` — 118 lines, zero tests ← **add tests**
- `src/utils/prerun.py` — 209 lines, zero tests ← **add tests**
- `src/utils/splash.py` — 134 lines, zero tests ← **add tests**

## Scope

**New test files (4):**
| Test file | Source file | Lines |
|---|---|---|
| `tests/test_utils/test_splash.py` | `src/utils/splash.py` | 134 |
| `tests/test_utils/test_config_handler.py` | `src/utils/config_handler.py` | 118 |
| `tests/test_utils/test_prerun.py` | `src/utils/prerun.py` | 209 |
| `tests/test_main.py` | `src/main.py` | 258 |

**Gap-fill existing tests (2):**
| Test file | Current coverage | Target |
|---|---|---|
| `tests/test_setup/test_wizard.py` | ~68% | 100% |
| `tests/test_setup/test_service_config.py` | ~98% | 100% |

**Config update (1):**
- `.coveragerc` — remove 5 files from omit list

## Approach

Four phases ordered by complexity. Since we're testing existing code, tests should pass on first run — we verify each file reaches 100% coverage before moving on.

---

## Phase 1 — Simple Utility Tests (`splash.py`, `config_handler.py`)

### Task 1.1: `tests/test_utils/test_splash.py`

**Source analysis** (`src/utils/splash.py` — 134 lines, 5 functions):
- `get_splash_screen()` → returns f-string with colorama codes
- `show_splash_screen()` → prints `get_splash_screen()`
- `show_version()` → prints version info with colorama formatting
- `show_welcome_screen()` → reads `config.get("logging")`, `config.get("security")`, `config.get("language")` — prints system info and commands
- `show_token_help()` → prints BotFather instructions

**Mock strategy:**
- `capsys` for stdout capture
- `config` already mocked via conftest (uses `config.get("logging", {})`, etc.)
- `patch("src.utils.splash.platform")` for deterministic Python version / OS strings

**Tests (~17):**
- `get_splash_screen` returns non-empty string containing "ADDARR" and "REFRESH EDITION"
- `show_splash_screen` prints splash to stdout (capsys)
- `show_version` output contains "1.0.0", repo URL
- `show_welcome_screen` — debug disabled shows "Disabled", admin disabled shows "Disabled", language shows "en-us"
- `show_welcome_screen` — debug enabled shows "Enabled" (override config)
- `show_welcome_screen` — admin enabled shows "Enabled" (override config)
- `show_welcome_screen` — custom language shows correct value
- `show_welcome_screen` — platform info appears in output
- `show_welcome_screen` — all CLI commands listed
- `show_welcome_screen` — all Telegram commands listed
- `show_welcome_screen` — resource URLs listed
- `show_token_help` — contains "Invalid Telegram Bot Token"
- `show_token_help` — contains BotFather instructions
- `show_token_help` — contains config.yaml example
- `show_token_help` — contains setup wizard suggestion
- `show_token_help` — contains wiki URL

### Task 1.2: `tests/test_utils/test_config_handler.py`

**Source analysis** (`src/utils/config_handler.py` — 118 lines):
- `ConfigHandler.__init__(colors)` — sets paths relative to root_dir
- `create_from_example()` → copies example, creates backup if exists, returns bool
- `create_backup()` → timestamped backup in `backup/` dir, returns path or ""
- `load_config()` → reads YAML from config_path, returns dict or {} on error
- `save_config(config)` → backup then write, returns bool
- `update_value(config, path, value)` → nested dict traversal with setdefault
- `config_handler` — global instance with `colors=None`

**Mock strategy:**
- `tmp_path` for real file I/O (create actual YAML files, verify copies/backups)
- Mock `colors` object with `Fore.GREEN`, `Fore.RED`, `Fore.YELLOW` attributes
- `patch("src.utils.config_handler.datetime")` for deterministic backup timestamps

**Tests (~22):**
- `__init__` sets `config_path`, `config_example_path`, `root_dir` correctly
- `create_from_example` — no existing config: copies example, returns True
- `create_from_example` — existing config: creates backup first, then copies
- `create_from_example` — missing example: catches exception, returns False
- `create_backup` — config exists: creates timestamped backup, returns path
- `create_backup` — creates backup dir if missing
- `create_backup` — config doesn't exist: returns ""
- `create_backup` — timestamp format matches `%Y%m%d_%H%M%S`
- `load_config` — valid YAML: returns dict
- `load_config` — file not found: returns {}
- `load_config` — invalid YAML: returns {}
- `save_config` — creates backup then writes, returns True
- `save_config` — write error: returns False
- `update_value` — single key path
- `update_value` — nested key path (2 levels)
- `update_value` — deeply nested path (3+ levels)
- `update_value` — creates missing intermediate keys via setdefault
- Global `config_handler` is a `ConfigHandler` instance
- Global `config_handler` has `colors=None`

---

## Phase 2 — PreRunChecker Tests (`prerun.py`)

### Task 2.1: `tests/test_utils/test_prerun.py`

**Source analysis** (`src/utils/prerun.py` — 209 lines):

*ColorHandler (lines 18-47):*
- `__init__` — tries `from colorama import Fore, Style, init`; on ImportError uses DummyFore/DummyStyle
- `reload()` — same logic, re-imports colorama

*PreRunChecker (lines 50-204):*
- `__init__` — creates ColorHandler, sets root_dir and config_path
- `check_config_exists()` — lazy imports `config_handler`, checks `os.path.exists`, prompts user, optionally launches SetupWizard
- `parse_requirements(filename)` — reads requirements.txt, strips versions, merges with core_deps
- `get_installed_packages()` — calls `subprocess.run` with `pip list --format=json`, normalizes names
- `check_dependencies()` — compares required vs installed, prompts install if missing
- `run_checks()` — calls check_dependencies then check_config_exists

*Global: `prerun_checker = PreRunChecker()`*

**Mock strategy:**
- `patch("src.utils.prerun.subprocess")` for pip calls
- `patch("builtins.input")` for user prompts
- `tmp_path` or `mock_open` for requirements.txt
- `patch("src.utils.prerun.os.path.exists")` for config file checks
- Lazy import patches for `config_handler` and `SetupWizard`

**Tests (~35):**

*ColorHandler:*
- `__init__` with colorama available — `Fore` and `Style` are real colorama objects
- `__init__` with colorama ImportError — uses DummyFore, DummyStyle
- DummyFore attributes are empty strings
- DummyStyle.RESET_ALL is empty string
- `reload()` with colorama available — reloads successfully
- `reload()` with ImportError — no-op (doesn't crash)

*PreRunChecker.__init__:*
- Sets `colors` to a ColorHandler instance
- Sets `root_dir` and `config_path` correctly

*parse_requirements:*
- Reads requirements.txt, returns package list
- Strips `>=`, `<=`, `==` version specifiers
- Strips inline `#` comments
- Skips empty lines and comment lines
- Converts to lowercase
- FileNotFoundError returns core_deps
- Merges with core deps and deduplicates

*get_installed_packages:*
- Parses JSON pip output into set
- Normalizes: adds both hyphen and underscore variants
- subprocess error returns empty set

*check_dependencies:*
- All installed → returns True
- Missing packages, user says "y" → installs via subprocess, returns True
- Missing packages, user says "n" → returns False
- Install failure (CalledProcessError) → returns False
- Missing includes colorama → calls `self.colors.reload()`
- Empty requirements → returns False
- Invalid input loops until y/n

*check_config_exists:*
- Config exists → returns True
- Config missing, user says "y", wizard succeeds → returns True
- Config missing, user says "y", create_from_example fails → returns False
- Config missing, user says "n" → returns False
- Invalid input loops until y/n
- Sets config_handler.colors

*run_checks:*
- Both pass → returns True
- Dependencies fail → returns False (doesn't call check_config_exists)
- Config fail → returns False

*Global:*
- `prerun_checker` is a PreRunChecker instance

---

## Phase 3 — AddarrBot Tests (`main.py`)

### Task 3.1: `tests/test_main.py`

**Source analysis** (`src/main.py` — 258 lines):

*AddarrBot class:*
- `__init__` — sets `application=None`, `_running=False`, `health_checker=health_service`
- `initialize()` — show_welcome_screen, check_config, health checks, get token, build Application, add_handlers, application.initialize(), handles InvalidToken (os.execl restart), NetworkError, generic exceptions
- `_add_handlers()` — instantiates 11 handler classes, conditionally adds Transmission/SABnzbd based on config
- `start()` — start application, set _running=True, create health check task, start polling, while _running loop
- `stop()` — set _running=False, stop health checker, stop updater, stop + shutdown application

*main() async:*
- Creates bot, defines start_bot inner function, gets/creates event loop, adds signal handlers (with Windows fallback), runs start_bot, handles KeyboardInterrupt + generic exceptions

*run_bot() sync:*
- Calls asyncio.run(main()), handles KeyboardInterrupt + generic exceptions

**Mock strategy:**
- `patch("src.main.Application")` — mock builder chain: `Application.builder().token().build()` returns mock app
- Patch all 11 handler classes via `@patch("src.main.StartHandler")` etc.
- `patch("src.main.health_service")` and `patch("src.main.display_health_status")`
- `patch("src.main.show_welcome_screen")`, `patch("src.main.check_config")`
- `patch("src.main.handle_token_error")`, `patch("src.main.handle_missing_token_error")`, etc.
- `patch("src.main.config")` for token/service enable overrides
- `patch("os.execl")` — MUST patch to avoid process replacement
- `patch("sys.exit")` for fatal error paths
- For `start()` while-loop: set `_running = False` via side_effect on `asyncio.sleep`

**Tests (~50):**

*AddarrBot.__init__:*
- application is None, _running is False, health_checker is health_service

*AddarrBot.initialize():*
- Happy path: calls show_welcome_screen, check_config, health checks, builds app, adds handlers, initializes
- Health checks fail → logs warning but continues
- Missing token → calls handle_missing_token_error, raises ValueError
- InvalidToken + handle_token_error returns True → calls os.execl (patched)
- InvalidToken + handle_token_error returns False → re-raises
- NetworkError → calls handle_network_error, re-raises
- Generic exception in app.initialize → calls handle_initialization_error, re-raises
- Outer exception → logs and re-raises

*AddarrBot._add_handlers():*
- All handlers registered (11 handler classes instantiated)
- Transmission disabled → TransmissionHandler not instantiated
- Transmission enabled → TransmissionHandler registered
- SABnzbd disabled → SabnzbdHandler not instantiated
- SABnzbd enabled → SabnzbdHandler registered
- Both Transmission and SABnzbd enabled
- Handler error → logs and re-raises

*AddarrBot.start():*
- Starts application, sets _running, starts health checker, starts polling
- Error during start → logs and re-raises
- While loop breaks when _running set to False

*AddarrBot.stop():*
- Happy path: stops health checker, updater, application, shutdown
- application is None → no-op
- updater not running → skips updater.stop
- Error during shutdown → logs debug, doesn't re-raise

*main():*
- Creates bot, calls initialize and start
- start_bot exception → calls bot.stop, sys.exit(1)
- Signal handlers registered (SIGINT, SIGTERM)
- Windows fallback when add_signal_handler raises NotImplementedError
- KeyboardInterrupt → calls bot.stop
- Generic exception → sys.exit(1)

*run_bot():*
- Calls asyncio.run(main())
- KeyboardInterrupt → logs shutdown
- Generic exception → sys.exit(1)

---

## Phase 4 — Gap-Fill + Coverage Config

### Task 4.1: Gap-fill `tests/test_setup/test_wizard.py`

**Missing coverage** (wizard.py lines not covered by existing tests):

- `_update_config_value` (line 66) — delegates to config_handler.update_value
- `_create_directories` (lines 127-134) — creates log dir and translations dir
- `_configure_service` (lines 136-159) — enables service, calls get_valid_service_config, handles arr features, catches exceptions
- `_configure_required_value` (lines 161-168) — gets default config for arr services, calls configure_required_value
- `_backup_config` (line 177) — delegates to create_backup
- `_reset_config` success path (lines 206-223) — loads example, saves, calls self.run()
- `_reset_config` missing example_path (lines 208-210) — sys.exit(1)
- `_reset_config` generic exception (lines 225-227) — sys.exit(1)
- `configure_services` Transmission auth branch (lines 264-269) — questionary for username/password
- `configure_services` SABnzbd branch (lines 272-279) — enables and configures SABnzbd

**Tests (~15):**
- `_update_config_value` delegates to config_handler.update_value
- `_create_directories` creates both directories
- `_configure_service` happy path: enables, gets valid config, configures features for arr
- `_configure_service` non-arr service: skips arr features
- `_configure_service` exception: prints error, sets enable=False
- `_configure_required_value` for arr service: passes default_config
- `_configure_required_value` for non-arr service: default_config=None
- `_backup_config` delegates to create_backup
- `_reset_config` success: loads example, saves, calls run()
- `_reset_config` missing example: sys.exit(1)
- `_reset_config` generic exception: sys.exit(1)
- `configure_services` Transmission with auth: sets username/password
- `configure_services` SABnzbd: enables and configures
- `configure_services` no services selected: just saves

### Task 4.2: Gap-fill `tests/test_setup/test_service_config.py`

**Missing coverage** (service_config.py line 174):
- SABnzbd skip-validation return path — when validation fails and user declines retry for SABnzbd service

**Tests (~2):**
- `test_sabnzbd_retry_then_skip` — validation fails, retry=False → returns SABnzbd config with `enable: False`
- `test_sabnzbd_skip_has_only_admin` — verify skipped SABnzbd config includes `onlyAdmin: True`

### Task 4.3: Update `.coveragerc`

Remove from omit:
- `src/main.py`
- `src/setup/wizard.py`
- `src/utils/config_handler.py`
- `src/utils/prerun.py`
- `src/utils/splash.py`

Keep omitted:
- `src/__init__.py` — empty init
- `src/config/settings.py` — reads from disk at import time, mocked via conftest

---

## Verification

After each task:
```bash
pytest tests/<new-test-file> --cov=src/<target> --cov-report=term-missing --no-cov-on-fail -q
```

Final verification (after Task 4.3):
```bash
pytest --cov=src --cov-report=term-missing --tb=short
# Must show: 100% coverage, all tests pass, no regressions
flake8 .
```

## Estimated Total: ~140 new tests
