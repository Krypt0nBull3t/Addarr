# Issue #17: Implement System Actions

## Summary

Consolidate fragmented `/status` handling into a single `SystemHandler` with real system actions (refresh health checks, view service details, back to menu). Remove dead `StatusHandler` and `MediaHandler.handle_status` code.

---

### Phase 1: Implement System Actions (3 tasks)

**Goal:** Replace the empty SystemHandler stub with working system actions and clean up dead status code.

**Phase Context:**

- Why NOT keep StatusHandler: It's dead code — `MediaHandler` registers `CommandHandler("status", ...)` first, so StatusHandler's `/status` never matches. It also has a bug referencing `health_status['check_interval']` which `HealthService.get_status()` doesn't return.
- Why NOT ConversationHandler: System actions are stateless one-shot operations (refresh, details, back) — `CallbackQueryHandler` is the correct pattern.

- [x] **1.1** Implement system keyboard and SystemHandler
    - **Context:**
        - **Why:** `get_system_keyboard()` returns `None` and `handle_system_action()` parses the callback action but does nothing — the entire system handler is a non-functional stub
        - **Architecture:** Follows existing callback-based inline keyboard pattern (like settings handler). SystemHandler uses `health_service` singleton for health data. Keyboard in `keyboards.py`, handler dispatches on `system_*` callback prefix.
        - **Key refs:** `src/bot/keyboards.py:64` (`get_system_keyboard` stub), `src/bot/handlers/system.py:41` (`handle_system_action` stub), `src/services/health.py:277` (`get_status()` returns `{running, last_check, unhealthy_services}`), `src/services/health.py:223` (`run_health_checks()` returns `{media_services, download_clients}`)
        - **Watch out:** `HealthService.get_status()` does NOT return `check_interval` — don't reference it. `show_status` must support both direct command (reply_text) and callback query (edit_text) invocation. The `system_handler` fixture in conftest needs updating to mock `health_service`.
    - **Scope:** System keyboard with 3 buttons + full SystemHandler with show_status, refresh, details, back actions
    - **Touches:** `src/bot/keyboards.py`, `src/bot/handlers/system.py`, `tests/test_bot/test_keyboards.py`, `tests/test_handlers/test_system_handler.py`, `tests/test_handlers/conftest.py`
    - **Action items:**
        - [RED] Replace `TestSystemKeyboard.test_system_keyboard_returns_none` with tests asserting `InlineKeyboardMarkup` with `system_refresh`, `system_details`, `system_back` buttons
        - [GREEN] Implement `get_system_keyboard()` returning 3-button `InlineKeyboardMarkup`
        - [RED] Update `system_handler` fixture in conftest to mock `health_service`, `get_system_keyboard`, `get_main_menu_keyboard`
        - [RED] Rewrite `test_system_handler.py` with tests: `test_show_status_direct`, `test_show_status_callback`, `test_show_status_no_user`, `test_show_status_not_authenticated`, `test_handle_refresh`, `test_handle_refresh_error`, `test_handle_details`, `test_handle_details_empty`, `test_handle_details_error`, `test_handle_back`, `test_handle_unknown_action`, `test_handle_no_callback`, `test_get_handler`
        - [GREEN] Implement SystemHandler: `show_status` (build status text + system keyboard), `handle_system_action` (dispatch to `_handle_refresh`/`_handle_details`/`_handle_back`), `_build_status_text`, `_build_details_text`
    - **Success:** `pytest tests/test_bot/test_keyboards.py tests/test_handlers/test_system_handler.py -v` all pass, `flake8` clean
    - **Completed:** 2026-02-20
    - **Learnings:**
        - Fixture must patch attributes that exist in the module — can't mock `health_service` until it's imported in `system.py`
        - `show_status` dual-path (reply_text vs edit_text) is cleanly testable with `make_update(text=...)` vs `make_update(callback_data=...)`
        - 3 extra tests beyond plan (health info content, last_check display, unhealthy listing) added for thorough status text coverage
    - **Key Changes:**
        - `src/bot/keyboards.py`: `get_system_keyboard()` now returns 3-button InlineKeyboardMarkup (Refresh, Details, Back)
        - `src/bot/handlers/system.py`: Full rewrite with `show_status`, `handle_system_action`, `_handle_refresh`, `_handle_details`, `_handle_back`, `_build_status_text`, `_build_details_text`
        - `tests/test_handlers/conftest.py`: `system_handler` fixture updated to mock `health_service`, `get_system_keyboard`, `get_main_menu_keyboard`
        - `tests/test_handlers/test_system_handler.py`: 16 tests (was 6)
        - `tests/test_bot/test_keyboards.py`: 4 system keyboard tests (was 1)
    - **Notes:** Full suite: 1027 passed. Net +10 tests.

- [x] **1.2** Wire up registration and delegation
    - **Context:**
        - **Why:** SystemHandler exists but is never registered in `main.py`. StartHandler delegates `menu_status` to `MediaHandler.handle_status` instead of SystemHandler.
        - **Architecture:** Replace `StatusHandler` registration in `_add_handlers()` with `SystemHandler` (same position — last handler). Update StartHandler to instantiate and delegate to SystemHandler for `menu_status` callback.
        - **Key refs:** `src/main.py:25` (StatusHandler import), `src/main.py:149-152` (StatusHandler registration block), `src/bot/handlers/start.py:169` (`await self.media_handler.handle_status(update, context)`)
        - **Watch out:** `start_handler` fixture in conftest must add `patch("src.bot.handlers.start.SystemHandler")` and create mock with `show_status = AsyncMock()`. Existing start handler tests for status delegation need updating.
    - **Scope:** main.py registration swap + StartHandler delegation change + test updates
    - **Touches:** `src/main.py`, `src/bot/handlers/start.py`, `tests/test_handlers/conftest.py`, `tests/test_handlers/test_start_handler.py`
    - **Action items:**
        - [RED] Update `start_handler` fixture to patch `SystemHandler` and create mock with `show_status = AsyncMock()`
        - [RED] Update status delegation test in `test_start_handler.py` to assert `system_handler.show_status` called
        - [GREEN] In `start.py`: import `SystemHandler`, instantiate in `__init__`, change `menu_status` to call `self.system_handler.show_status(update, context)`
        - [GREEN] In `main.py`: replace `StatusHandler` import/registration with `SystemHandler`
    - **Success:** `pytest tests/test_handlers/test_start_handler.py -v` passes, bot registers SystemHandler correctly
    - **Completed:** 2026-02-20
    - **Learnings:**
        - Fixture patch must match import path exactly — `src.bot.handlers.start.SystemHandler` only works after the import is added to `start.py`
        - Removed `handle_status` from mock_media_handler since it's no longer needed
    - **Key Changes:**
        - `src/bot/handlers/start.py`: Added `SystemHandler` import, instantiate in `__init__`, delegate `menu_status` to `system_handler.show_status`
        - `src/main.py`: Replaced `StatusHandler` import/registration with `SystemHandler`
        - `tests/test_handlers/conftest.py`: Added `SystemHandler` patch + mock to `start_handler` fixture
        - `tests/test_handlers/test_start_handler.py`: Updated status delegation test assertion
    - **Notes:** No net test count change — same 15 start handler tests, just updated assertion target.

- [x] **1.3** Remove dead status code
    - **Context:**
        - **Why:** With SystemHandler now owning `/status`, three pieces of dead code remain: `StatusHandler` (never matched), `MediaHandler.handle_status`/`_get_status_text` (no longer delegated to), and the `status_handler` fixture.
        - **Architecture:** Pure deletion — no new code, just removing unreachable paths.
        - **Key refs:** `src/bot/handlers/status.py` (entire file), `src/bot/handlers/media.py:111` (`CommandHandler("status", ...)`), `src/bot/handlers/media.py:857` (`handle_status`), `src/bot/handlers/media.py:912` (`_get_status_text`), `tests/test_handlers/conftest.py:143-172` (`status_handler` fixture)
        - **Watch out:** Grep for any remaining references to `StatusHandler`, `handle_status`, or `_get_status_text` before declaring done. The `get_system_keyboard` import in `media.py` may also be unused after removal — check.
    - **Scope:** Delete StatusHandler + tests, remove MediaHandler status methods + tests, remove status_handler fixture
    - **Touches:** `src/bot/handlers/media.py`, `tests/test_handlers/test_media_handler.py`, `tests/test_handlers/conftest.py`
    - **Deletes:** `src/bot/handlers/status.py`, `tests/test_handlers/test_status_handler.py`
    - **Action items:**
        - [GREEN] Remove `CommandHandler("status", self.handle_status)` from `MediaHandler.get_handler()`
        - [GREEN] Remove `handle_status()` and `_get_status_text()` methods from `MediaHandler`
        - [GREEN] Remove `handle_status` / `_get_status_text` tests from `test_media_handler.py`
        - [GREEN] Delete `src/bot/handlers/status.py` and `tests/test_handlers/test_status_handler.py`
        - [GREEN] Remove `status_handler` fixture from `tests/test_handlers/conftest.py`
        - [GREEN] Grep for stale references to `StatusHandler`, `handle_status`, `_get_status_text`
    - **Success:** `pytest --tb=short -q` full suite green, `flake8` clean on all modified files, no stale references found
    - **Completed:** 2026-02-20
    - **Learnings:**
        - `get_system_keyboard` import in `media.py` was only used by the removed methods — safe to remove entirely
        - No other files referenced `StatusHandler` or `handle_status` — clean removal with zero stale references
    - **Key Changes:**
        - `src/bot/handlers/media.py`: Removed `get_system_keyboard` import, `CommandHandler("status", ...)`, `handle_status()`, `_get_status_text()`
        - `tests/test_handlers/test_media_handler.py`: Removed 9 status/status-text tests
        - `tests/test_handlers/conftest.py`: Removed `status_handler` fixture
        - Deleted `src/bot/handlers/status.py` and `tests/test_handlers/test_status_handler.py`
    - **Notes:** Test count went from 1027 → 1009 (net -18: removed 9 media handler + 9 status handler tests). All new functionality covered by the 16 system handler tests from task 1.1.
