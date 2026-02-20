# Plan: Implement System Actions (Issue #17)

## Context

`SystemHandler` is an empty stub — `handle_system_action()` parses the callback but does nothing, and `get_system_keyboard()` returns `None`. Additionally, `/status` handling is fragmented across three places:

1. **MediaHandler** (`media.py:111`) — registers `CommandHandler("status", self.handle_status)` outside its ConversationHandler. Since MediaHandler is registered first, it wins.
2. **StatusHandler** (`status.py`) — also registers `CommandHandler("status", ...)` but is registered last, so it's effectively dead code. It also has a pre-existing bug (references `health_status['check_interval']` which `HealthService.get_status()` doesn't return).
3. **SystemHandler** (`system.py`) — has a `/status` command but is never registered in `main.py`.

**Goal**: Consolidate all status functionality into SystemHandler with real system actions, and clean up the dead code.

## System Actions

| Button | Callback | Behavior |
|---|---|---|
| 🔄 Refresh | `system_refresh` | Re-run health checks, update status display |
| 📋 Details | `system_details` | Show per-service health with version info |
| ◀️ Back | `system_back` | Return to main menu |

## Files to Modify

| File | Change |
|---|---|
| `src/bot/keyboards.py` | Replace `get_system_keyboard()` stub with real 3-button keyboard |
| `src/bot/handlers/system.py` | Implement real `show_status` + `handle_system_action` with refresh/details/back |
| `src/main.py` | Replace StatusHandler import/registration with SystemHandler |
| `src/bot/handlers/start.py` | Delegate `menu_status` to SystemHandler instead of MediaHandler |
| `src/bot/handlers/media.py` | Remove `CommandHandler("status", ...)`, `handle_status()`, `_get_status_text()` |
| `tests/test_bot/test_keyboards.py` | Replace `test_system_keyboard_returns_none` with real keyboard assertions |
| `tests/test_handlers/test_system_handler.py` | Rewrite for new handler behavior |
| `tests/test_handlers/conftest.py` | Update `system_handler` fixture; update `start_handler` fixture; remove `status_handler` fixture |
| `tests/test_handlers/test_start_handler.py` | Update status delegation test |
| `tests/test_handlers/test_media_handler.py` | Remove `handle_status` / `_get_status_text` tests |

## Files to Delete

| File | Reason |
|---|---|
| `src/bot/handlers/status.py` | Dead code — never matched because MediaHandler registered first |
| `tests/test_handlers/test_status_handler.py` | Tests for deleted handler |

## TDD Steps

### Step 1 — Keyboard (RED → GREEN)

**Tests** (`tests/test_bot/test_keyboards.py`):
- Replace `TestSystemKeyboard.test_system_keyboard_returns_none` with:
  - `test_system_keyboard_returns_markup` — asserts `InlineKeyboardMarkup` returned
  - `test_system_keyboard_has_refresh_button` — `system_refresh` callback in buttons
  - `test_system_keyboard_has_details_button` — `system_details` callback in buttons
  - `test_system_keyboard_has_back_button` — `system_back` callback in buttons

**Implementation** (`src/bot/keyboards.py`):
- `get_system_keyboard()` returns `InlineKeyboardMarkup` with 3 buttons

### Step 2 — SystemHandler (RED → GREEN)

**Tests** (`tests/test_handlers/test_system_handler.py`) — rewrite entirely:
- `test_show_status_direct` — sends reply_text with status text + system keyboard
- `test_show_status_callback` — edits message (for `menu_status` callback)
- `test_show_status_no_user` — returns None
- `test_show_status_not_authenticated` — blocked by `@require_auth`
- `test_handle_refresh` — calls `run_health_checks()`, answers query, edits message
- `test_handle_refresh_error` — exception → edits error message, answers query
- `test_handle_details` — calls `run_health_checks()`, edits with per-service info
- `test_handle_details_empty` — no services → shows "No services enabled"
- `test_handle_details_error` — exception → edits error message
- `test_handle_back` — edits with main menu keyboard
- `test_handle_unknown_action` — answers "Unknown action"
- `test_handle_no_callback` — returns None
- `test_get_handler` — returns list of handlers

**Fixture** (`tests/test_handlers/conftest.py`):
- Update `system_handler` fixture to mock `health_service`, `get_system_keyboard`, `get_main_menu_keyboard`

**Implementation** (`src/bot/handlers/system.py`):
- Import `health_service` from `src.services.health`
- Import `get_main_menu_keyboard` from keyboards
- `show_status()`: build status text from `health_service.get_status()`, send/edit with system keyboard
- `handle_system_action()`: dispatch on action → `_handle_refresh`, `_handle_details`, `_handle_back`
- `_handle_refresh()`: `await health_service.run_health_checks()`, rebuild status text, edit message, answer query
- `_handle_details()`: `await health_service.run_health_checks()`, format per-service results, edit message
- `_handle_back()`: edit message with main menu keyboard via `get_main_menu_keyboard()`
- `_build_status_text()`: format health monitor status, last check time, unhealthy services
- `_build_details_text(results)`: format media_services + download_clients with status per service

### Step 3 — Wire Up (registration + delegation)

**main.py**: Replace `StatusHandler` with `SystemHandler` import and registration (same position — last handler).

**start.py**:
- Import `SystemHandler`, instantiate in `__init__`
- Change `menu_status` delegation: `await self.system_handler.show_status(update, context)`

**start_handler fixture** in conftest.py:
- Add `patch("src.bot.handlers.start.SystemHandler")`
- Create mock with `show_status = AsyncMock()`

**test_start_handler.py**: Update status delegation test to assert `system_handler.show_status` called.

### Step 4 — Clean Up Dead Code

**media.py**: Remove `CommandHandler("status", self.handle_status)` from `get_handler()`, remove `handle_status()` and `_get_status_text()` methods.

**test_media_handler.py**: Remove tests for `handle_status` and `_get_status_text`.

**Delete**: `src/bot/handlers/status.py`, `tests/test_handlers/test_status_handler.py`

**conftest.py**: Remove `status_handler` fixture.

### Step 5 — Verify

```bash
pytest tests/test_bot/test_keyboards.py -v
pytest tests/test_handlers/test_system_handler.py -v
pytest tests/test_handlers/test_start_handler.py -v
pytest tests/test_handlers/test_media_handler.py -v
pytest --tb=short -q
flake8 src/bot/handlers/system.py src/bot/keyboards.py src/main.py src/bot/handlers/start.py src/bot/handlers/media.py
```

## Verification

1. All state/keyboard/handler tests pass
2. Full suite green — no other code references StatusHandler or MediaHandler.handle_status
3. `flake8` clean on all modified files
