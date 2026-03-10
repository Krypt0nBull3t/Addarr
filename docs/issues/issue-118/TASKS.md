# Issue #118: Add mypy Type Checking to CI

## Summary

Add mypy as a blocking CI job. Create config with per-module overrides (lenient on handlers, strict elsewhere). Fix all genuine type errors so CI passes clean from day one.

**Baseline:** 494 errors in 42 files. Strategy: suppress handler union-attr/index noise via config, fix everything else.

---

### Phase 1: Add mypy to CI (3 tasks)

**Goal:** Blocking mypy CI job that passes clean on the entire `src/` tree.

- [x] **1.1** Infrastructure — mypy config, dependencies, CI job
    - **Context:** See plan.md Phase 1. No mypy.ini or pyproject.toml exists. CI is in `.github/workflows/ci.yml`. Test deps in `requirements-test.txt`.
    - **Watch out:** Per-module `[mypy-src.bot.handlers.*]` must use dotted module paths. `[mypy-src.setup.*]` should also be lenient (interactive wizard, not business logic). CI job should run between lint and unit-test.
    - **Scope:** Create `mypy.ini`, update `requirements-test.txt`, add `type-check` job to CI
    - **Touches:** `mypy.ini` (new), `requirements-test.txt`, `.github/workflows/ci.yml`
    - **Action items:**
        - [GREEN] Create `mypy.ini` with global defaults + per-module overrides for handlers and setup
        - [GREEN] Add `mypy>=1.8.0` and `types-PyYAML>=6.0.12` to `requirements-test.txt`
        - [GREEN] Add `type-check` job to CI workflow (blocking, between lint and unit-test)
        - [CHECK] Run `python -m mypy src/` locally — note remaining error count (should drop significantly from 494)
    - **Success:** mypy runs, per-module config suppresses handler/setup noise, CI job defined
    - **Completed:** 2026-03-10
    - **Learnings:**
        - Handler files need union-attr, index, arg-type, attr-defined, assignment, AND var-annotated suppressed (mixin pattern + Telegram Optional types)
        - `ignore_errors = True` for setup module is cleaner than listing all error codes
    - **Key Changes:**
        - Created `mypy.ini` with global defaults + per-module overrides
        - Added mypy + types-PyYAML to `requirements-test.txt`
        - Added `type-check` CI job to `.github/workflows/ci.yml`
    - **Notes:** Error count dropped from 494 to 84 just from config + stubs

- [x] **1.2** Fix type errors in services and API layer
    - **Context:** See plan.md Phases 2-4. Main error categories: implicit Optional (`param: str = None` → `Optional[str]`), attr-defined on singletons (missing class-level annotations), wrong arg types.
    - **Watch out:** Singleton `__new__` sets instance attrs in `if not hasattr` block — mypy needs class-level declarations. `Optional` import may already exist in some files. Don't change function behavior, only type annotations.
    - **Scope:** Fix all mypy errors in `src/services/`, `src/api/`, `src/utils/`, `src/config/`
    - **Touches:** `src/services/sabnzbd.py`, `src/services/scheduler.py`, `src/services/media.py`, `src/services/rate_limit.py`, `src/services/translation.py`, `src/api/base.py`, `src/api/sabnzbd.py`, `src/api/lidarr.py`, `src/utils/validate_translations.py`, `src/utils/logger.py`, `src/utils/helpers.py`, `src/utils/validation.py`
    - **Action items:**
        - [GREEN] Fix implicit Optional in `src/api/base.py` (title, timeout, max_retries params) and missing return
        - [GREEN] Fix implicit Optional in `src/api/sabnzbd.py` (nzbname, category)
        - [GREEN] Add class-level type annotations to `src/services/sabnzbd.py` + fix implicit Optional
        - [GREEN] Add class-level type annotations to `src/services/scheduler.py`
        - [GREEN] Add class-level type annotations to `src/services/media.py`
        - [GREEN] Fix type annotation on `src/services/rate_limit.py` (_records)
        - [GREEN] Fix implicit Optional in `src/services/translation.py`
        - [GREEN] Fix implicit Optional in `src/utils/logger.py`
        - [GREEN] Fix type errors in `src/utils/validate_translations.py`, `src/utils/helpers.py`, `src/utils/validation.py`
        - [CHECK] Run `python -m mypy src/` — verify services/API/utils layers are clean
        - [CHECK] Run `python -m pytest --tb=short -q` — no test regressions
    - **Success:** Zero mypy errors in services, API, and utils layers. All tests pass.
    - **Completed:** 2026-03-10
    - **Learnings:**
        - Singleton `__new__` pattern needs class-level type annotations for mypy to see instance attrs
        - `asyncio.gather(return_exceptions=True)` returns `Any | BaseException` — use `isinstance(result, BaseException)` not `Exception`
        - aiohttp `timeout` param needs `aiohttp.ClientTimeout(total=N)` not bare `int`
        - SABnzbdService `api_key`/`base_url` changed from `Optional[str]` to `str` (empty string default) to avoid params dict typing issues
        - `AddarrError` doesn't store `.message` — use `str(e)` instead
    - **Key Changes:**
        - Fixed implicit Optional in 13 files (api/base, api/sabnzbd, api/sonarr, api/radarr, api/lidarr, services/sabnzbd, services/media, services/translation, utils/logger, utils/validate_translations, bot/keyboards)
        - Added class-level type annotations to 6 singletons (SABnzbdService, JobScheduler, NotificationService, TransmissionService, RateLimitService, HealthService)
        - Fixed return types on MediaService.add_movie/add_series/add_music
        - Fixed aiohttp timeout types in HealthService
    - **Notes:** All 84 non-handler errors resolved. 1869 tests pass, flake8 clean.

- [x] **1.3** Fix remaining errors (keyboards, bot modules) and final verification
    - **Context:** See plan.md Phase 4-5. `src/bot/keyboards.py` has ~9 union-attr errors from Telegram types. May need targeted fixes or per-module config. Any other stragglers outside handler/setup layers.
    - **Watch out:** `keyboards.py` is not under `handlers/` so it doesn't get the per-module suppression. Check if `src/bot/commands.py` or `src/bot/states.py` have errors too. Don't add unnecessary `# type: ignore` — prefer config or real fixes.
    - **Scope:** Fix all remaining mypy errors, ensure clean pass, run full verification suite
    - **Touches:** `src/bot/keyboards.py`, possibly `src/bot/commands.py`, `src/main.py`
    - **Action items:**
        - [GREEN] Fix or suppress remaining errors in `src/bot/keyboards.py`
        - [GREEN] Fix any other non-handler bot module errors
        - [CHECK] Run `python -m mypy src/` — must show **0 errors**
        - [CHECK] Run `python -m pytest --tb=short -q` — all tests pass
        - [CHECK] Run `python -m flake8 .` — no lint failures
    - **Success:** `mypy src/` passes clean. Full test suite passes. Flake8 clean.
    - **Completed:** 2026-03-10
    - **Learnings:** keyboards.py errors were just implicit Optional, same as services
    - **Key Changes:** Merged into task 1.2 — all fixes done in one pass
    - **Notes:** N/A — tasks 1.2 and 1.3 completed together since scope overlapped

- [ ] **1.4** Create follow-up GitHub issues for suppressed type errors
    - **Context:** Per-module config in `mypy.ini` suppresses union-attr/index in handlers and disables checking in setup. These are tech debt that should be tracked.
    - **Watch out:** Split handler errors into logical batches (not one mega-issue). Reference #118 as parent. Include specific error codes and affected files per issue.
    - **Scope:** Create 2-3 GitHub issues to track gradual strictness improvements
    - **Action items:**
        - [GREEN] Run `python -m mypy src/` with handler/setup suppressions removed to get exact error counts per file
        - [GREEN] Create issue for handler layer type fixes (union-attr/index in `src/bot/handlers/`)
        - [GREEN] Create issue for setup module type fixes (`src/setup/`)
    - **Success:** Follow-up issues created on GitHub with clear scope, error counts, and file lists
