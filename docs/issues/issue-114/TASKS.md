# Issue #114: Bazarr Integration (Subtitles)

**Goal:** Add Bazarr subtitle management to Addarr — check subtitle status, view wanted lists, and trigger subtitle searches via Telegram.

**Sizing:** Medium (3 tasks across 2 phases, ~15 files)

---

### Phase 1: Backend Foundation (2 tasks)

**Goal:** Config, API client, and service layer — all backend pieces ready for the handler.

- [x] **1.1** Config + BazarrClient API client
    - **Context:** See plan.md Phase 1 (Tasks 1.1 + 1.2). Key refs: `src/api/base.py:56` (BaseApiClient), `src/api/radarr.py:20` (concrete client pattern), `config_example.yaml:14` (config structure pattern), `tests/conftest.py:23` (MOCK_CONFIG_DATA)
    - **Watch out:**
        - Bazarr API has no version prefix — set `API_VERSION = ""`. URL becomes `http://host:port/api//endpoint` (double slash). Tests must mock this exact URL pattern: `http://localhost:6767/api//movies`
        - `search()` is abstract in BaseApiClient — implement as title filter over `GET /api/movies` since Bazarr has no text search endpoint
        - `_get_headers()` from base uses `X-Api-Key` — Bazarr uses `X-API-KEY`. Both work (HTTP headers are case-insensitive)
    - **Scope:** Bazarr config in `config_example.yaml` + mock config, `BazarrClient` with init validation, search, get_movies, get_wanted_movies, get_wanted_episodes, search_movie_subtitles, search_episode_subtitles. Sample test data. Full test coverage.
    - **Touches:**
        - Create: `src/api/bazarr.py`, `tests/test_api/test_bazarr.py`, `tests/fixtures/bazarr_data.py`
        - Modify: `config_example.yaml`, `tests/conftest.py` (MOCK_CONFIG_DATA), `src/api/__init__.py`
    - **Action items:**
        - [RED] Write tests for init validation (missing addr, missing apikey)
        - [RED] Write tests for `search()` — success with matches, success with no matches, empty API response, exception
        - [RED] Write tests for `get_movies()` — success, empty, exception
        - [RED] Write tests for `get_wanted_movies()` / `get_wanted_episodes()` — success, empty, exception
        - [RED] Write tests for `search_movie_subtitles()` / `search_episode_subtitles()` — success, failure, exception
        - [GREEN] Add bazarr section to `config_example.yaml` (after lidarr, before webhooks)
        - [GREEN] Add bazarr to `MOCK_CONFIG_DATA` in `tests/conftest.py`
        - [GREEN] Create `tests/fixtures/bazarr_data.py` with sample responses
        - [GREEN] Implement `BazarrClient` in `src/api/bazarr.py`
        - [GREEN] Add `BazarrClient` export to `src/api/__init__.py`
    - **Success:** `pytest tests/test_api/test_bazarr.py -v` passes, 100% coverage on `src/api/bazarr.py`
    - **Completed:** 2026-03-10
    - **Learnings:**
        - `API_VERSION = ""` produces double-slash URLs (`/api//movies`) — aioresponses mocks must match this exact pattern
        - Exception tests need `patch.object` on `_request`/`_make_request` to hit outer `except` blocks, since `_request` internally catches all HTTP errors
        - Added 3 extra `api_returns_none` tests for non-dict response paths to reach 100% coverage (27 tests total)
    - **Key Changes:**
        - Created `src/api/bazarr.py` with `BazarrClient` (7 methods)
        - Created `tests/test_api/test_bazarr.py` (27 tests, 100% coverage)
        - Created `tests/fixtures/bazarr_data.py` (sample responses)
        - Added bazarr config to `config_example.yaml` and `tests/conftest.py`
        - Updated `src/api/__init__.py` and `tests/test_api/conftest.py`
    - **Notes:** Bazarr health check method for `HealthService` deferred to task 2.1

- [x] **1.2** BazarrService singleton + architecture updates
    - **Context:** See plan.md Phase 1 (Task 1.3). Key refs: `src/services/transmission.py:17` (singleton pattern), `tests/conftest.py:218` (singleton reset fixture), `tests/test_architecture/test_conventions.py` (SINGLETON_CLASSES set)
    - **Watch out:**
        - Class-level type annotations required for mypy to see attributes set in `__new__`/`_initialize`
        - Must add `BazarrService` to `SINGLETON_CLASSES` or architecture test fails
        - Must add singleton reset in `tests/conftest.py` or state leaks between tests
    - **Scope:** `BazarrService` singleton with lazy client init, `is_enabled()`, delegation methods. Architecture test + conftest updates.
    - **Touches:**
        - Create: `src/services/bazarr.py`, `tests/test_services/test_bazarr.py`
        - Modify: `src/services/__init__.py`, `tests/conftest.py` (singleton reset), `tests/test_architecture/test_conventions.py`
    - **Action items:**
        - [RED] Write tests for singleton behavior (same instance on repeated instantiation)
        - [RED] Write tests for `is_enabled()` — enabled vs disabled config
        - [RED] Write tests for `client` property — lazy init, disabled returns None, init failure returns None
        - [RED] Write tests for delegation methods — each returns empty/False when client is None
        - [RED] Write tests for delegation methods — each delegates to client when available
        - [GREEN] Implement `BazarrService` in `src/services/bazarr.py`
        - [GREEN] Add export to `src/services/__init__.py`
        - [GREEN] Add singleton reset to `tests/conftest.py`
        - [GREEN] Add `"BazarrService"` to `SINGLETON_CLASSES` in `tests/test_architecture/test_conventions.py`
    - **Success:** `pytest tests/test_services/test_bazarr.py tests/test_architecture/ -v` passes, 100% coverage on `src/services/bazarr.py`
    - **Completed:** 2026-03-10
    - **Learnings:**
        - Singleton reset in conftest must include ALL class vars (`_client`, `_config`) not just `_instance`, otherwise state leaks between tests cause failures
        - Bazarr config is enabled by default in mock config, so disabled tests need a fixture to temporarily flip it
        - Delegation tests inject mock client via class attribute (`BazarrService._client = mock_client`) after singleton init — simpler than patching the constructor
    - **Key Changes:**
        - Created `src/services/bazarr.py` with `BazarrService` singleton (7 delegation methods)
        - Created `tests/test_services/test_bazarr_service.py` (19 tests, 100% coverage)
        - Added `BazarrService` to singleton reset in `tests/conftest.py`
        - Added `"BazarrService"` to `SINGLETON_CLASSES` in `tests/test_architecture/test_conventions.py`
        - Added export to `src/services/__init__.py`
    - **Notes:** Service follows TransmissionService pattern with lazy client init via property

---

### Phase 2: Handler + Integration (1 task)

**Goal:** Telegram handler, translations, health check, help text, bot command registration — feature is user-facing.

- [ ] **2.1** BazarrHandler + translations + registration + health check
    - **Context:** See plan.md Phase 2 (Tasks 2.1–2.3) + Phase 3 (Task 3.1). Key refs: `src/bot/handlers/help.py:22` (simple handler pattern), `src/bot/handlers/transmission.py` (enabled-gated handler), `src/main.py:111` (`_add_handlers` registration), `src/services/health.py:256` (`check_service_health`), `src/bot/commands.py` (command registration), `src/bot/states.py:9` (States class), `translations/addarr.en-us.yml` (flat key pattern)
    - **Watch out:**
        - `prompt_search` callback is registered OUTSIDE the ConversationHandler (standalone CallbackQueryHandler) but returns `States.BAZARR_SEARCH` — this won't work as a state transition outside a ConversationHandler. Fix: move `bazarr_movie_search` into the ConversationHandler entry_points so the state transition is valid
        - Translation keys must be flat (no dots). `get_text()` does single-level lookup only
        - Handler registration is gated on `config.get("bazarr", {}).get("enable")` — place after History, before Transmission
        - Bazarr health check uses `X-API-KEY` header (not `X-Api-Key`) and endpoint `/api/system/status` (no version prefix)
        - Add `BAZARR_SEARCH = 10` to States class — verify no collision with existing state values
        - All 9 locale files + template need the new keys
        - `HelpBazarr` translation key for help text section
        - Add `/subtitles` to `build_authenticated_commands()` in `src/bot/commands.py`
    - **Scope:** Full handler with ConversationHandler for search flow + callback handlers for wanted lists and subtitle search triggers. Translation keys in all locales. Health check method + integration. Help text. Bot command registration. Tests for handler.
    - **Touches:**
        - Create: `src/bot/handlers/bazarr.py`, `tests/test_handlers/test_bazarr.py`
        - Modify: `src/bot/handlers/__init__.py`, `src/bot/states.py`, `src/main.py`, `src/services/health.py`, `src/bot/handlers/help.py`, `src/bot/commands.py`, `translations/addarr.*.yml` (all 9 + template)
    - **Action items:**
        - [RED] Write tests for `subtitles_menu` — not enabled shows error, enabled shows keyboard (command and callback variants)
        - [RED] Write tests for `prompt_search` — sends prompt text, returns BAZARR_SEARCH state
        - [RED] Write tests for `handle_search` — results found (shows status), no results, empty text
        - [RED] Write tests for `wanted_movies` — results found, empty list
        - [RED] Write tests for `wanted_episodes` — results found, empty list
        - [RED] Write tests for `search_subtitles_trigger` — success (movie), failure
        - [RED] Write tests for `cancel` — callback query variant, message variant
        - [RED] Write tests for `get_handler()` returns list with ConversationHandler
        - [GREEN] Add `BAZARR_SEARCH = 10` to `src/bot/states.py`
        - [GREEN] Add translation keys to all locale files + template
        - [GREEN] Implement `BazarrHandler` in `src/bot/handlers/bazarr.py`
        - [GREEN] Add export to `src/bot/handlers/__init__.py`
        - [GREEN] Add handler registration to `src/main.py:_add_handlers()`
        - [GREEN] Add `check_bazarr_health()` to `src/services/health.py` + call in `run_health_checks()`
        - [GREEN] Add Bazarr section to `src/bot/handlers/help.py:_build_help_text()`
        - [GREEN] Add `/subtitles` to `src/bot/commands.py`
    - **Success:** `pytest tests/test_handlers/test_bazarr.py -v` passes, 100% coverage on `src/bot/handlers/bazarr.py`, `python -m flake8 .` clean, `mypy src/` clean, `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` passes, architecture tests pass

---

## Verification Checklist

- [ ] `pytest --tb=short -q` — full suite passes
- [ ] `python -m flake8 .` — no lint errors
- [ ] `mypy src/` — no type errors
- [ ] `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` — translations valid
- [ ] Architecture tests pass (SINGLETON_CLASSES, get_handler convention)
- [ ] 100% coverage on all new source files
- [ ] Config example includes bazarr section
- [ ] Help text shows Bazarr commands when enabled
- [ ] Health check includes Bazarr when enabled

---

## Follow-Up Issues

After this PR merges, create GitHub issues for out-of-scope items:
- [ ] Bazarr download notifications (notify when subtitles are downloaded)
- [ ] Bazarr provider management (view/manage subtitle providers)
- [ ] Bazarr settings management (configure Bazarr via Telegram)
