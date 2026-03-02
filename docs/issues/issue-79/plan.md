# Split setup.py into focused modules (#79)

## Context

`src/setup.py` is 925 lines with mixed responsibilities: CLI prompts, validation,
service configuration, and file I/O. This makes it untestable (excluded from coverage)
and hard to navigate. Splitting into a `src/setup/` package with focused modules enables
testing and reduces cognitive load.

**Consumers** (only 2 files — both use `from src.setup import SetupWizard`):
- `run.py:48` — `.run()`, `.configure_services()`
- `src/utils/prerun.py:76` — `.run()`

**Dead code to remove**: `_configure_sabnzbd()` (201-232) and `_configure_arr_service()`
(234-272) — never called anywhere.

## Target Structure

```
src/setup/
├── __init__.py          (~10 lines)  Re-exports SetupWizard, main
├── wizard.py            (~180 lines) Orchestrator class + entry points
├── prompts.py           (~270 lines) All questionary-based user prompts
├── service_config.py    (~180 lines) Service defaults + validated config loop
└── validators.py        (~105 lines) Connection testing + port validation
```

**Dependency flow** (no circular deps):
```
__init__.py → wizard.py → prompts.py          (standalone)
                        → service_config.py → validators.py (standalone)
```

## Design Decision: Functions, not classes

Extracted methods become **standalone async functions** that return values instead of
mutating `self.config`. The wizard assigns return values. This makes each function
independently testable without needing a SetupWizard instance.

---

## Phase 0 — Create package skeleton

**Goal**: Convert `src/setup.py` → `src/setup/` package without changing behavior.

### Steps

1. `git mv src/setup.py src/setup/wizard.py` (create `src/setup/` dir first)
2. Create `src/setup/__init__.py`:
   ```python
   from src.setup.wizard import SetupWizard, main

   __all__ = ["SetupWizard", "main"]
   ```
3. Fix `self.root_dir` in wizard.py — file is now one level deeper:
   ```python
   # Before (setup.py was in src/):
   self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
   # After (wizard.py is in src/setup/):
   self.root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
   ```
4. Remove `sys.path.append` hack (line 27) — unnecessary when imported as package
5. Create `tests/test_setup/__init__.py` (empty)
6. **Verify**: `pytest --tb=short -q` passes, `flake8 .` passes

---

## Phase 1 — Extract `validators.py`

**Goal**: Move connection testing and port validation to standalone functions.

### Move from wizard.py → `src/setup/validators.py`

| Original method (wizard.py) | New function (validators.py) |
|---|---|
| `_validate_service_connection()` (592-679) | `validate_service_connection(service, url, port, ssl, apikey)` → `bool` |
| `_get_valid_port()` (285-298) | `get_valid_port(message, default)` → `int` |

Both become standalone async functions. `validate_service_connection` takes the same
params minus `self`. `get_valid_port` takes `message` and `default` strings.

### Update wizard.py

Replace `self._validate_service_connection(...)` → `validate_service_connection(...)`
and `self._get_valid_port(...)` → `get_valid_port(...)` (3 call sites).

### Tests — `tests/test_setup/test_validators.py`

- `test_validate_connection_success` — mock aiohttp → 200 with expected JSON keys
- `test_validate_connection_timeout` — mock → `asyncio.TimeoutError`
- `test_validate_connection_bad_status` — mock → 401/500
- `test_validate_connection_transmission_409_success` — 409 is valid for Transmission
- `test_validate_connection_unknown_service` — returns False
- `test_get_valid_port_valid_input` — mock questionary → "8989"
- `test_get_valid_port_invalid_then_valid` — mock sequence: "abc", "8989"
- `test_get_valid_port_out_of_range_then_valid` — mock sequence: "99999", "8989"

### Verify

```bash
pytest tests/test_setup/test_validators.py -v
pytest --tb=short -q  # Full suite still passes
flake8 .
```

---

## Phase 2 — Extract `prompts.py`

**Goal**: Move all questionary-based user interaction to standalone async functions.

### Move from wizard.py → `src/setup/prompts.py`

| Original method | New function | Returns |
|---|---|---|
| `_select_services()` (122-174) | `select_services()` | `List[str]` |
| `_configure_language()` (442-510) | `configure_language()` | `str` |
| `_configure_telegram()` (343-354) | `configure_telegram()` | `Dict` |
| `_configure_access_control()` (356-408) | `configure_access_control()` | `Dict` (keys: `security`, `admins`, `allow_list`) |
| `_configure_logging()` (410-440) | `configure_logging()` | `Dict` |
| `_configure_arr_features()` (300-341) | `configure_arr_features(service)` | `Dict` |
| `_configure_required_value()` (570-590) | `configure_required_value(config, service, value)` | `Dict` (mutated config) |

Each function only imports `questionary` and `colorama` — no wizard dependency.

### Update wizard.py `_async_setup()`

```python
from src.setup.prompts import (
    select_services, configure_language, configure_telegram,
    configure_access_control, configure_logging,
)

async def _async_setup(self):
    self.config["language"] = await configure_language()
    services = await select_services()
    for service in services:
        await self._configure_service(service)
    telegram_config = await configure_telegram()
    self.config["telegram"] = telegram_config
    access_config = await configure_access_control()
    self.config["security"] = access_config["security"]
    self.config["admins"] = access_config["admins"]
    if "allow_list" in access_config:
        self.config["allow_list"] = access_config["allow_list"]
    self.config["logging"] = await configure_logging()
    self._save_config()
```

Also update `_configure_service()` to call `configure_arr_features(service)` from prompts,
and update `configure_services()` (sync method) similarly.

### Tests — `tests/test_setup/test_prompts.py`

- `test_select_services_media_only` — mock checkbox → ["radarr"], confirm → False
- `test_select_services_with_download_clients` — mock checkbox → ["sonarr"], confirm → True, checkbox → ["transmission"]
- `test_select_services_empty_retries` — first checkbox → [], second → ["radarr"]
- `test_configure_language` — mock select → "en-us", verify return value
- `test_configure_telegram` — mock password inputs, verify dict shape
- `test_configure_access_control_with_allowlist` — mock confirms + text inputs
- `test_configure_access_control_without_allowlist` — enableAllowlist=False
- `test_configure_logging` — mock confirms + text input
- `test_configure_arr_features_radarr` — has minimumAvailability
- `test_configure_arr_features_sonarr` — has seasonFolder
- `test_configure_arr_features_lidarr` — has albumFolder + monitorOption
- `test_configure_required_value_telegram_token` — verify config mutation
- `test_configure_required_value_arr_apikey` — verify config mutation

### Verify

```bash
pytest tests/test_setup/test_prompts.py -v
pytest --tb=short -q
flake8 .
```

---

## Phase 3 — Extract `service_config.py`

**Goal**: Move service default configs and the validated config loop.

### Move from wizard.py → `src/setup/service_config.py`

| Original method | New function | Notes |
|---|---|---|
| `_get_default_port()` (274-283) | `get_default_port(service)` → `str` | Pure function, no deps |
| `_get_default_service_config()` (512-568) | `get_default_service_config(service)` → `Dict` | Calls `get_default_port` |
| `_get_valid_service_config()` (681-792) | `get_valid_service_config(service)` → `Dict` | Imports `validate_service_connection`, `get_valid_port` from validators |

### Update wizard.py

Replace `self._get_default_service_config(...)` → `get_default_service_config(...)` and
`self._get_valid_service_config(...)` → `get_valid_service_config(...)`.

### Tests — `tests/test_setup/test_service_config.py`

- `test_get_default_port_each_service` — radarr=7878, sonarr=8989, lidarr=8686, etc.
- `test_get_default_port_unknown_service` — returns "8090"
- `test_get_default_service_config_radarr` — has features.minimumAvailability
- `test_get_default_service_config_sonarr` — has features.seasonFolder
- `test_get_default_service_config_lidarr` — has metadataProfileId
- `test_get_default_service_config_transmission` — flat structure (no server.addr)
- `test_get_default_service_config_sabnzbd` — has onlyAdmin
- `test_get_valid_service_config_success` — mock questionary + validator → True
- `test_get_valid_service_config_retry_then_skip` — validator → False, confirm retry → False

### Verify

```bash
pytest tests/test_setup/test_service_config.py -v
pytest --tb=short -q
flake8 .
```

---

## Phase 4 — Cleanup + wizard tests

**Goal**: Remove dead code, add wizard orchestration tests, register domain runner.

### Steps

1. **Delete dead code** from wizard.py:
   - `_configure_sabnzbd()` (lines 201-232) — never called
   - `_configure_arr_service()` (lines 234-272) — never called
2. **Clean up imports** in wizard.py — remove anything no longer needed
   (e.g., `aiohttp`, `urlparse`, `questionary` if fully extracted)
3. **Add `"setup"` domain** to `scripts/test_runner.py`:
   ```python
   "setup": {
       "test_path": "tests/test_setup/",
       "cov_source": "src/setup/",
   },
   ```
4. **Write `tests/test_setup/test_wizard.py`**:
   - `test_wizard_init` — mock config_handler.load_config, verify self.config set
   - `test_wizard_async_setup_orchestration` — mock all prompt/service functions,
     verify call order and config assignment
   - `test_wizard_configure_services_flow` — mock sync questionary + async calls
   - `test_wizard_reset_config_cancelled` — mock confirm → False, verify sys.exit
   - `test_wizard_run_calls_async_setup` — mock loop, verify run_until_complete called
5. **Final verify**:
   ```bash
   pytest --tb=short -q                              # All tests pass
   pytest tests/test_setup/ --cov=src/setup --cov-report=term-missing  # Coverage
   flake8 .                                          # No lint errors
   python scripts/test_runner.py setup --coverage    # Domain runner works
   ```

---

## File-by-file summary

| File | Action | Lines (approx) |
|---|---|---|
| `src/setup.py` | Delete (becomes package) | 0 |
| `src/setup/__init__.py` | Create | ~10 |
| `src/setup/wizard.py` | Create (from setup.py, methods extracted) | ~180 |
| `src/setup/prompts.py` | Create (extracted prompt functions) | ~270 |
| `src/setup/service_config.py` | Create (defaults + config loop) | ~180 |
| `src/setup/validators.py` | Create (connection test + port) | ~105 |
| `tests/test_setup/__init__.py` | Create | 0 |
| `tests/test_setup/test_validators.py` | Create | ~120 |
| `tests/test_setup/test_prompts.py` | Create | ~200 |
| `tests/test_setup/test_service_config.py` | Create | ~150 |
| `tests/test_setup/test_wizard.py` | Create | ~100 |
| `scripts/test_runner.py` | Edit (add setup domain) | +4 |
| `run.py` | No changes needed (import path preserved) | 0 |
| `src/utils/prerun.py` | No changes needed (import path preserved) | 0 |

## Verification checklist

```bash
pytest --tb=short -q                              # All existing tests still pass
pytest tests/test_setup/ --cov=src/setup --cov-report=term-missing  # New coverage
flake8 .                                          # No lint errors
python scripts/test_runner.py setup --coverage    # Domain runner works
python -c "from src.setup import SetupWizard"     # Import works
```

Manual: `python run.py --setup` launches wizard identically to before.
