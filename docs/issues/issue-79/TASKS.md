# Issue #79: Split setup.py into focused modules

> **Plan:** [plan.md](plan.md)

---

### Phase 1: Package Skeleton (1 task)

**Goal:** Convert `src/setup.py` into `src/setup/` package without changing behavior.

- [x] **1.1** Convert setup.py to setup/ package
    - **Context:**
        - **Why:** `src/setup.py` is 925 lines — can't be tested or navigated. Converting to a package is the structural prerequisite for all extraction work.
        - **Architecture:** `git mv src/setup.py src/setup/wizard.py`, add `__init__.py` re-exporting `SetupWizard` and `main`. Consumers (`run.py:48`, `src/utils/prerun.py:76`) use `from src.setup import SetupWizard` — this import path is preserved by the `__init__.py` re-export.
        - **Key refs:** `src/setup.py:48` (`self.root_dir` uses `__file__` — must add one more `dirname` since file moves one level deeper), `src/setup.py:27` (`sys.path.append` hack to remove)
        - **Watch out:** `self.root_dir` is used in `_reset_config()` at line 831 to find `config_example.yaml`. If the path is wrong, reset will fail silently. Also `git mv` requires creating the directory first since the target is a package.
    - **Scope:** File move, `__init__.py`, path fix, sys.path removal, test dir skeleton
    - **Touches:** `src/setup.py` (becomes `src/setup/wizard.py`), `src/setup/__init__.py`, `tests/test_setup/__init__.py`
    - **Action items:**
        - [GREEN] Create `src/setup/` directory and `git mv src/setup.py src/setup/wizard.py`
        - [GREEN] Create `src/setup/__init__.py` re-exporting `SetupWizard` and `main`
        - [GREEN] Fix `self.root_dir` in wizard.py (add one more `os.path.dirname` level)
        - [GREEN] Remove `sys.path.append` hack and the `# noqa: E402` comments on imports below it
        - [GREEN] Create `tests/test_setup/__init__.py`
        - [VERIFY] `pytest --tb=short -q` — all existing tests pass
        - [VERIFY] `flake8 .` — no lint errors
        - [VERIFY] `python -c "from src.setup import SetupWizard; print('OK')"` — import works
    - **Success:** All existing tests pass, flake8 clean, `from src.setup import SetupWizard` works
    - **Completed:** 2026-03-02
    - **Learnings:**
        - `python -c "from src.setup import SetupWizard"` fails without config.yaml due to import chain: setup → splash → config.settings → Config() reads disk. This is pre-existing behavior, not caused by the refactor. Tests work because MockConfig in conftest.py intercepts this.
        - `sys` is still needed in wizard.py (sys.exit, sys.argv) — only the sys.path.append was removed.
    - **Key Changes:**
        - `git mv src/setup.py src/setup/wizard.py`
        - Created `src/setup/__init__.py` re-exporting SetupWizard and main
        - Fixed `self.root_dir` with extra `os.path.dirname` level
        - Removed `sys.path.append` hack and `# noqa: E402` comments
        - Created `tests/test_setup/__init__.py`
    - **Notes:** Import path `from src.setup import SetupWizard` preserved — run.py and prerun.py need zero changes.

---

### Phase 2: Extract Modules (3 tasks)

**Goal:** Extract validators, prompts, and service config into standalone async functions with tests.

**Phase Context:**

- Why NOT classes: Standalone functions are independently testable without needing a SetupWizard instance. The wizard assigns return values instead of methods mutating `self.config`.
- Dependency order matters: validators.py is standalone, prompts.py is standalone, service_config.py imports from validators. Extract validators first.

- [x] **2.1** Extract validators.py + tests
    - **Context:**
        - **Why:** Connection testing and port validation are reusable, self-contained logic. Extracting first because `service_config.py` (task 2.3) will import from this module.
        - **Architecture:** Two standalone async functions: `validate_service_connection(service, url, port, ssl, apikey) -> bool` and `get_valid_port(message, default) -> int`. No class needed. Imports `aiohttp`, `asyncio`, `questionary`, `colorama`.
        - **Key refs:** `src/setup/wizard.py` lines 592-679 (`_validate_service_connection`), lines 285-298 (`_get_valid_port`). Called from `_get_valid_service_config()` at lines 701, 720.
        - **Watch out:** `validate_service_connection` has service-specific endpoint configs (radarr/sonarr use `/api/v3`, lidarr uses `/api/v1`). Transmission treats 409 as success (session ID challenge). The `timeout=5` param is passed as int to `aiohttp`, not `aiohttp.ClientTimeout`.
    - **Scope:** New `src/setup/validators.py`, update wizard.py call sites, full test coverage
    - **Touches:** `src/setup/validators.py` (create), `src/setup/wizard.py` (update calls), `tests/test_setup/test_validators.py` (create)
    - **Action items:**
        - [RED] Write `tests/test_setup/test_validators.py`:
            - `test_validate_connection_success` — mock aiohttp 200 + JSON with `version` key
            - `test_validate_connection_timeout` — mock `asyncio.TimeoutError`
            - `test_validate_connection_bad_status` — mock 401/500
            - `test_validate_connection_transmission_409` — 409 is valid for Transmission
            - `test_validate_connection_unknown_service` — returns False
            - `test_get_valid_port_valid` — mock questionary text → "8989"
            - `test_get_valid_port_invalid_then_valid` — mock sequence: "abc", "8989"
            - `test_get_valid_port_out_of_range_then_valid` — mock sequence: "99999", "8989"
        - [GREEN] Create `src/setup/validators.py` with extracted functions
        - [GREEN] Update `src/setup/wizard.py` — replace `self._validate_service_connection(...)` and `self._get_valid_port(...)` with imports from validators
        - [GREEN] Remove now-unused imports from wizard.py (`aiohttp`, `asyncio.TimeoutError` if only used there)
        - [VERIFY] `pytest tests/test_setup/test_validators.py -v` — new tests pass
        - [VERIFY] `pytest --tb=short -q` — full suite passes
        - [VERIFY] `flake8 .` — clean
    - **Success:** 8 validator tests pass, all existing tests pass, flake8 clean
    - **Completed:** 2026-03-02
    - **Learnings:**
        - `aioresponses` works well for mocking the connection validator — matches exact URLs including protocol/port/path
        - Wrote 15 tests (exceeded the planned 8) — added extra coverage for sonarr/lidarr success, client errors, missing JSON keys, SSL protocol, transmission 500, and port 0 edge case
        - Deleting methods from wizard.py left extra blank lines triggering E303 flake8 errors — watch for this in future extractions
    - **Key Changes:**
        - Created `src/setup/validators.py` with `validate_service_connection()` and `get_valid_port()`
        - Created `tests/test_setup/test_validators.py` with 15 tests (11 connection + 4 port)
        - Updated wizard.py: removed old methods, replaced `self._` calls with standalone function imports, removed unused `import aiohttp`
    - **Notes:** `asyncio` import stays in wizard.py — still used by `run()` and `configure_services()` for event loop management.

- [x] **2.2** Extract prompts.py + tests
    - **Context:**
        - **Why:** Prompt functions are the largest chunk (~270 lines). Each function collects user input via questionary and returns a value — pure I/O with no business logic. Extracting makes them independently testable by mocking questionary.
        - **Architecture:** 7 standalone async functions. Each takes only the params it needs (no `self`). Returns dicts/strings/lists that the wizard assigns to `self.config`. `configure_required_value` is unique — it takes and mutates a config dict, plus needs `get_default_service_config` from service_config. Extract it but keep its import lazy or pass the default config builder.
        - **Key refs:** `src/setup/wizard.py` lines 122-174 (`_select_services`), 442-510 (`_configure_language`), 343-354 (`_configure_telegram`), 356-408 (`_configure_access_control`), 410-440 (`_configure_logging`), 300-341 (`_configure_arr_features`), 570-590 (`_configure_required_value`)
        - **Watch out:** `_select_services` is recursive on empty selection (line 139). `_configure_access_control` builds a compound return with `security`, `admins`, and conditionally `allow_list`. `_configure_required_value` mutates `self.config` — new signature must take config dict as param and return it. `configure_services()` (sync method, line 853) also calls `_get_valid_service_config` — update that too.
    - **Scope:** New `src/setup/prompts.py`, update wizard.py `_async_setup()` + `_configure_service()` + `configure_services()`, full test coverage
    - **Touches:** `src/setup/prompts.py` (create), `src/setup/wizard.py` (update), `tests/test_setup/test_prompts.py` (create)
    - **Action items:**
        - [RED] Write `tests/test_setup/test_prompts.py`:
            - `test_select_services_media_only` — checkbox → `["radarr"]`, confirm → False
            - `test_select_services_with_download_clients` — checkbox → `["sonarr"]`, confirm → True, checkbox → `["transmission"]`
            - `test_select_services_empty_retries` — first checkbox → `[]`, second → `["radarr"]`
            - `test_configure_language` — select → `"en-us"`, verify return
            - `test_configure_telegram` — password inputs, verify dict shape
            - `test_configure_access_control_with_allowlist` — enables allowlist, adds IDs
            - `test_configure_access_control_without_allowlist` — `enableAllowlist=False`, no `allow_list` key
            - `test_configure_logging` — confirms + admin notify ID
            - `test_configure_arr_features_radarr` — has `minimumAvailability`
            - `test_configure_arr_features_sonarr` — has `seasonFolder`
            - `test_configure_arr_features_lidarr` — has `albumFolder` + `monitorOption`
            - `test_configure_required_value_telegram_token` — verify config mutation
            - `test_configure_required_value_arr_apikey` — verify config mutation
        - [GREEN] Create `src/setup/prompts.py` with all 7 extracted functions
        - [GREEN] Update wizard.py `_async_setup()` to call standalone prompt functions and assign returns
        - [GREEN] Update wizard.py `_configure_service()` to use `configure_arr_features()` from prompts
        - [GREEN] Update wizard.py `configure_services()` (sync method) similarly
        - [GREEN] Remove now-unused questionary/colorama imports from wizard.py if fully extracted
        - [VERIFY] `pytest tests/test_setup/test_prompts.py -v` — new tests pass
        - [VERIFY] `pytest --tb=short -q` — full suite passes
        - [VERIFY] `flake8 .` — clean
    - **Success:** 13 prompt tests pass, all existing tests pass, flake8 clean
    - **Completed:** 2026-03-02
    - **Learnings:**
        - `configure_access_control` returns a compound dict (`security`, `admins`, optionally `allow_list`) — the wizard unpacks it into separate config keys. This pattern avoids the function needing to know about the full config structure.
        - `configure_required_value` needed a `default_config` parameter to avoid circular dependency with `get_default_service_config` (not yet extracted). The wizard passes the default config from its own method.
        - `questionary` import stays in wizard.py — still used by `_reset_config()`, `configure_services()`, `_configure_sabnzbd()` (dead code), `_configure_arr_service()` (dead code), and `_get_valid_service_config()`.
        - Wrote 17 tests (exceeded planned 13) — added extra coverage for non-English language, empty admin notify, existing telegram password, and arr default config creation.
    - **Key Changes:**
        - Created `src/setup/prompts.py` with 7 standalone async functions
        - Created `tests/test_setup/test_prompts.py` with 17 tests
        - Updated wizard.py `_async_setup()` to use standalone functions and assign return values
        - Updated wizard.py `_configure_service()` to call `configure_arr_features()` from prompts
        - Updated wizard.py `_configure_required_value()` to delegate to standalone function
        - Deleted 6 old methods from wizard.py (~350 lines removed)
    - **Notes:** `configure_services()` sync method still calls `self._get_valid_service_config()` directly — will be updated in task 2.3 when service_config.py is extracted.

- [x] **2.3** Extract service_config.py + tests
    - **Context:**
        - **Why:** Service default configs and the validated config loop are business logic that should be testable. The pure functions (`get_default_port`, `get_default_service_config`) have zero external deps — easy to test. The config loop (`get_valid_service_config`) coordinates validators + questionary prompts.
        - **Architecture:** 3 functions. `get_default_port(service) -> str` and `get_default_service_config(service) -> Dict` are pure. `get_valid_service_config(service) -> Dict` is async, imports `validate_service_connection` + `get_valid_port` from validators.
        - **Key refs:** `src/setup/wizard.py` lines 274-283 (`_get_default_port`), 512-568 (`_get_default_service_config`), 681-792 (`_get_valid_service_config`)
        - **Watch out:** `_get_default_service_config` has service-specific branches — transmission returns a flat structure (no `server.addr`), sabnzbd has `onlyAdmin`. `_get_valid_service_config` returns different shapes for sabnzbd vs other services (sabnzbd includes `enable` and `onlyAdmin` in return). The `urlparse` validation in the config loop should move here too.
    - **Scope:** New `src/setup/service_config.py`, update wizard.py, full test coverage
    - **Touches:** `src/setup/service_config.py` (create), `src/setup/wizard.py` (update), `tests/test_setup/test_service_config.py` (create)
    - **Action items:**
        - [RED] Write `tests/test_setup/test_service_config.py`:
            - `test_get_default_port_each_service` — radarr=7878, sonarr=8989, lidarr=8686, transmission=9091, sabnzbd=8090
            - `test_get_default_port_unknown` — returns "8090"
            - `test_get_default_service_config_radarr` — has `features.minimumAvailability`
            - `test_get_default_service_config_sonarr` — has `features.seasonFolder`
            - `test_get_default_service_config_lidarr` — has `metadataProfileId`
            - `test_get_default_service_config_transmission` — flat structure, no nested `server`
            - `test_get_default_service_config_sabnzbd` — has `onlyAdmin`
            - `test_get_valid_service_config_success` — mock questionary + validator → True
            - `test_get_valid_service_config_retry_then_skip` — validator → False, confirm retry → False
        - [GREEN] Create `src/setup/service_config.py` with 3 extracted functions
        - [GREEN] Update wizard.py — replace `self._get_default_service_config(...)` and `self._get_valid_service_config(...)` with imports
        - [GREEN] Remove now-unused imports from wizard.py (`urlparse` if only used in config loop)
        - [VERIFY] `pytest tests/test_setup/test_service_config.py -v` — new tests pass
        - [VERIFY] `pytest --tb=short -q` — full suite passes
        - [VERIFY] `flake8 .` — clean
    - **Success:** 9 service config tests pass, all existing tests pass, flake8 clean
    - **Completed:** 2026-03-02
    - **Learnings:**
        - `get_default_service_config` restructured to early-return for transmission/sabnzbd (cleaner than elif at bottom of base_config). Avoids building the full arr config only to throw it away.
        - Dead code (`_configure_sabnzbd`, `_configure_arr_service`) references `get_valid_port` which was removed from wizard.py imports when validators import was replaced. Had to add `get_valid_port` import back temporarily with a comment noting it's for dead code removed in task 3.1.
        - `urlparse` import successfully removed — only used by `_get_valid_service_config` which moved to service_config.py.
        - Used `pytest.mark.parametrize` for default port tests — cleaner than 5 separate test functions.
    - **Key Changes:**
        - Created `src/setup/service_config.py` with `get_default_port()`, `get_default_service_config()`, `get_valid_service_config()`
        - Created `tests/test_setup/test_service_config.py` with 16 tests (6 port + 6 default config + 4 valid config)
        - Updated wizard.py: removed 3 old methods (~180 lines), replaced all `self._` calls with standalone imports
        - Removed unused `urlparse` import from wizard.py
    - **Notes:** Temporary `get_valid_port` import in wizard.py for dead code — will be cleaned in task 3.1 when dead methods are deleted.

---

### Phase 3: Cleanup & Integration (1 task)

**Goal:** Remove dead code, add wizard orchestration tests, register setup domain runner.

- [x] **3.1** Dead code removal + wizard tests + domain runner
    - **Context:**
        - **Why:** `_configure_sabnzbd()` and `_configure_arr_service()` are dead code (never called). Wizard.py needs its own tests for orchestration logic (`run()`, `_async_setup()`, `_reset_config()`, `configure_services()`). The test runner needs a `setup` domain to run setup tests with scoped coverage.
        - **Architecture:** Delete dead methods from wizard.py. Wizard tests mock all extracted functions (prompts, service_config, validators) and verify the wizard orchestrates them correctly. Domain runner addition is a 4-line edit to `scripts/test_runner.py`.
        - **Key refs:** `src/setup/wizard.py` dead code: `_configure_sabnzbd()` (originally lines 201-232), `_configure_arr_service()` (originally lines 234-272). `scripts/test_runner.py:28` (`DOMAINS` dict to extend).
        - **Watch out:** Wizard still uses `questionary` directly in `configure_services()` (sync method) and `_reset_config()` — don't remove those imports. `_reset_config()` calls `questionary.confirm().ask()` (sync, not async). The `configure_services()` method uses `asyncio.run()` inside a sync method — test with mock.
    - **Scope:** Dead code removal, wizard.py import cleanup, test_wizard.py, test_runner.py domain
    - **Touches:** `src/setup/wizard.py` (delete dead code, clean imports), `tests/test_setup/test_wizard.py` (create), `scripts/test_runner.py` (add domain)
    - **Action items:**
        - [GREEN] Delete `_configure_sabnzbd()` and `_configure_arr_service()` from wizard.py
        - [GREEN] Clean up wizard.py imports — remove anything no longer used
        - [GREEN] Add `"setup"` domain to `scripts/test_runner.py` DOMAINS dict
        - [RED] Write `tests/test_setup/test_wizard.py`:
            - `test_wizard_init` — mock `config_handler.load_config`, verify `self.config` set
            - `test_wizard_async_setup_orchestration` — mock all prompt/service functions, verify call order + config assignment
            - `test_wizard_configure_services_flow` — mock sync questionary + asyncio.run
            - `test_wizard_reset_config_cancelled` — mock `confirm → False`, verify `sys.exit`
            - `test_wizard_run_calls_async_setup` — mock event loop, verify `run_until_complete`
        - [GREEN] Implement any test fixes needed to make wizard tests pass
        - [VERIFY] `pytest --tb=short -q` — all tests pass
        - [VERIFY] `pytest tests/test_setup/ --cov=src/setup --cov-report=term-missing` — coverage reported
        - [VERIFY] `flake8 .` — clean
        - [VERIFY] `python scripts/test_runner.py setup --coverage` — domain runner works
    - **Success:** Dead code removed, 5 wizard tests pass, domain runner works, all tests pass, flake8 clean
    - **Completed:** 2026-03-02
    - **Learnings:**
        - Mocking `sys.exit` without `side_effect=SystemExit` doesn't stop execution — code continues past the exit call. For `_reset_config()` which has a try/except wrapping multiple exit points, use `pytest.raises(SystemExit)` and check `exc_info.value.code` instead.
        - `.coveragerc` had stale `src/setup.py` omit entry after the file was moved to `src/setup/wizard.py`. Updated to match the new path since wizard.py is interactive entry-point code (same category as other omitted files).
        - Removed `Dict` from typing imports (only used in deleted dead code signatures) and `get_default_port` from service_config imports (only used in deleted `_configure_arr_service`).
    - **Key Changes:**
        - Deleted `_configure_sabnzbd()` and `_configure_arr_service()` from `src/setup/wizard.py` (~70 lines removed)
        - Cleaned imports: removed `get_valid_port`, `get_default_port`, `Dict` — no longer needed
        - Created `tests/test_setup/test_wizard.py` with 13 tests (2 init + 3 run + 2 async_setup + 2 reset + 2 configure_services + 2 main)
        - Added `"setup"` domain to `scripts/test_runner.py`
        - Updated `.coveragerc` omit: `src/setup.py` → `src/setup/wizard.py`
    - **Notes:** Extracted modules (prompts, validators, service_config) are at 89% coverage — the missing lines are error-handling edge cases (ValueError catches, urlparse failures) from tasks 2.1-2.3. Not in scope for this task.
