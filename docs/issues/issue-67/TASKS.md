# Issue #67: Downloads & Users Settings Sub-Menus + Cleanup

## Phase 1: Foundation Layer (3 tasks)

**Goal:** Replace "Coming soon" placeholders with functional Downloads and Users sub-menus in the settings conversation, and clean up dead code.

### Phase Context

- Why NOT separate cleanup task: Dead code removal and new states/keyboards both touch `states.py` and `keyboards.py` — combining avoids double-touching the same files and their tests.
- Why NOT combine downloads + users into one handler task: Each sub-menu has distinct service dependencies (Transmission/SABnzbd vs config security flags) and different fixture requirements. Separate tasks keep the test-first cycles focused.

---

- [x] **1.1** Foundation: cleanup dead code, add new states/keyboards, fix per_message
    - **Context:**
        - **Why:** `AWAITING_SETTING_ACTION` and `get_service_toggle_keyboard` are unused dead code. PTB emits a warning when `per_message` is not explicitly set on ConversationHandlers. New states and keyboards are needed before the handler methods can be wired up.
        - **Architecture:** States are string constants on `States` class. Keyboards are module-level factory functions returning `InlineKeyboardMarkup`. `per_message=False` is a ConversationHandler kwarg.
        - **Key refs:**
            - Dead state: `src/bot/states.py:23` (`AWAITING_SETTING_ACTION`)
            - Dead keyboard: `src/bot/keyboards.py:138-158` (`get_service_toggle_keyboard`)
            - Dead test: `tests/test_bot/test_keyboards.py:203-239` (`TestServiceToggleKeyboard`)
            - ConversationHandlers: `settings.py:46`, `media.py:48`, `start.py:43`, `auth.py:89`
        - **Watch out:** `test_string_states_are_strings` (line 51) asserts `AWAITING_SETTING_ACTION` exists — must update. Callback data prefixes: `dl_` for downloads, `dl_trans_`/`dl_sab_` for sub-actions, `usr_` for users.
    - **Scope:** Remove dead code, add 2 new states, add 4 new keyboard functions, add `per_message=False` to all 4 ConversationHandlers, update all related tests.
    - **Touches:** `src/bot/states.py`, `src/bot/keyboards.py`, `src/bot/handlers/settings.py`, `src/bot/handlers/media.py`, `src/bot/handlers/start.py`, `src/bot/handlers/auth.py`, `tests/test_bot/test_states.py`, `tests/test_bot/test_keyboards.py`
    - **Action items:**
        - [RED] `test_states.py`: Remove `AWAITING_SETTING_ACTION` from `test_string_states_are_strings`; add `test_awaiting_setting_action_removed` asserting `not hasattr`; add tests for `SETTINGS_DOWNLOADS` and `SETTINGS_USERS` — existence, str type, uniqueness with existing settings states
        - [RED] `test_keyboards.py`: Remove `TestServiceToggleKeyboard` class; add `test_service_toggle_keyboard_removed`; add `TestDownloadsKeyboard`, `TestTransmissionSettingsKeyboard`, `TestSabnzbdSettingsKeyboard`, `TestUsersKeyboard` — verify correct callback data values and back button in each
        - [GREEN] `states.py`: Delete `AWAITING_SETTING_ACTION`; add `SETTINGS_DOWNLOADS = "settings_downloads"`, `SETTINGS_USERS = "settings_users"`
        - [GREEN] `keyboards.py`: Delete `get_service_toggle_keyboard`; add `get_downloads_keyboard(trans_enabled, sab_enabled)`, `get_transmission_settings_keyboard(enabled, alt_speed_enabled)`, `get_sabnzbd_settings_keyboard(enabled)`, `get_users_keyboard(admin_enabled, allowlist_enabled, admin_count, auth_count)`
        - [GREEN] Add `per_message=False` to ConversationHandler in `settings.py`, `media.py`, `start.py`, `auth.py`
    - **Success:** `pytest tests/test_bot/ -v` passes, `flake8 .` clean
    - **Completed:** 2026-02-20
    - **Learnings:**
        - PTB emits `PTBUserWarning` when `per_message=False` is set with `CallbackQueryHandler` — this is informational, not an error. It confirms the setting is active.
        - Keyboard tests use inline `from src.bot.keyboards import ...` inside test methods to avoid import errors when the function doesn't exist yet (ImportError is the expected RED failure).
    - **Key Changes:**
        - `src/bot/states.py`: Removed `AWAITING_SETTING_ACTION`, added `SETTINGS_DOWNLOADS` and `SETTINGS_USERS`
        - `src/bot/keyboards.py`: Removed `get_service_toggle_keyboard`, added `get_downloads_keyboard`, `get_transmission_settings_keyboard`, `get_sabnzbd_settings_keyboard`, `get_users_keyboard`
        - `src/bot/handlers/settings.py`, `media.py`, `start.py`, `auth.py`: Added `per_message=False` to all ConversationHandlers
        - `tests/test_bot/test_states.py`: Updated `test_string_states_are_strings`, added removal assertion and 4 new state tests, updated uniqueness test
        - `tests/test_bot/test_keyboards.py`: Replaced `TestServiceToggleKeyboard` with removal assertion and 4 new keyboard test classes (20 total new test methods)
    - **Notes:** Callback data prefixes established: `dl_` for downloads menu, `dl_trans_`/`dl_sab_` for sub-actions, `usr_` for users menu, `dl_back`/`usr_back` for back navigation

- [x] **1.2** Downloads settings handler (Transmission + SABnzbd)
    - **Context:**
        - **Why:** The "Downloads" button in the settings menu currently shows "Coming soon". Users need to toggle Transmission/SABnzbd enable, control turtle mode, set speed limits, and pause/resume from Telegram.
        - **Architecture:** New handler methods on `SettingsHandler`, routed via `SETTINGS_DOWNLOADS` state in the existing ConversationHandler. Services already exist: `TransmissionService.set_alt_speed(bool)` and `SABnzbdService.set_speed_limit(int)`, `.pause_queue()`, `.resume_queue()`.
        - **Key refs:**
            - `src/bot/handlers/settings.py:64-67` — current `handle_coming_soon` routing for `settings_downloads`
            - `src/services/transmission.py:45` — `set_alt_speed(enabled)` already implemented
            - `src/services/sabnzbd.py:75` — `set_speed_limit(percentage)` already implemented
            - `src/services/sabnzbd.py:23-24` — `SABnzbdService.__init__` raises `ValueError` if not enabled
            - `tests/test_handlers/conftest.py:295` — `settings_handler` fixture needs Transmission/SABnzbd mocks
        - **Watch out:** `SABnzbdService()` raises `ValueError` when `sabnzbd.enable` is `False` in config. Must `try/except ValueError` in `SettingsHandler.__init__` and set `self.sabnzbd_service = None`. `TransmissionService` is safe (lazy-init). `MOCK_CONFIG_DATA` has both disabled — fixture must patch both service constructors.
    - **Scope:** Fixture update, ~11 test methods, ~8 handler methods, ConversationHandler state wiring.
    - **Touches:** `tests/test_handlers/conftest.py`, `tests/test_handlers/test_settings_handler.py`, `src/bot/handlers/settings.py`
    - **Action items:**
        - [RED] Update `settings_handler` fixture in `conftest.py`: patch `TransmissionService` and `SABnzbdService` constructors, attach mocks to handler (`_mock_trans`, `_mock_sab`)
        - [RED] Write `TestDownloadsFlow` in `test_settings_handler.py`: `test_handle_downloads_menu_shows_keyboard`, `test_handle_transmission_settings`, `test_handle_transmission_toggle`, `test_handle_transmission_turtle`, `test_handle_transmission_turtle_error`, `test_handle_sabnzbd_settings`, `test_handle_sabnzbd_toggle`, `test_handle_sabnzbd_speed`, `test_handle_sabnzbd_pause`, `test_handle_sabnzbd_resume`, `test_handle_downloads_back`
        - [GREEN] Add imports to `settings.py`: `TransmissionService`, `SABnzbdService`, new keyboard functions
        - [GREEN] Update `SettingsHandler.__init__`: add `self.transmission_service = TransmissionService()`, wrap `self.sabnzbd_service = SABnzbdService()` in `try/except ValueError` → `None`
        - [GREEN] Update `get_handler()`: replace `handle_coming_soon` pattern for `settings_downloads`, add `SETTINGS_DOWNLOADS` state with callback handlers for `dl_` prefixed actions
        - [GREEN] Implement handler methods: `handle_downloads_menu`, `handle_transmission_settings`, `handle_transmission_toggle`, `handle_transmission_turtle`, `handle_sabnzbd_settings`, `handle_sabnzbd_toggle`, `handle_sabnzbd_speed`, `handle_sabnzbd_pause_resume`
    - **Success:** `pytest tests/test_handlers/test_settings_handler.py -v` passes, all 11 new tests green
    - **Completed:** 2026-02-20
    - **Learnings:**
        - The fixture must patch `TransmissionService` and `SABnzbdService` at the `src.bot.handlers.settings` module level — the imports must exist in production code before `patch()` can intercept them (otherwise `AttributeError`).
        - `SABnzbdService.__init__` raises `ValueError` when disabled — `try/except ValueError` in `SettingsHandler.__init__` sets `self.sabnzbd_service = None` cleanly.
        - `handle_sabnzbd_speed` handles both showing speed options (`dl_sab_speed`) and applying selected speed (`dl_sab_speed_25` etc.) using a single handler matched by `^dl_sab_speed` pattern.
        - `handle_sabnzbd_pause_resume` dispatches on `query.data` to call the correct service method.
    - **Key Changes:**
        - `src/bot/handlers/settings.py`: Added `TransmissionService`, `SABnzbdService` imports and 3 new keyboard imports; updated `__init__` with service instances; replaced `settings_downloads` routing from `handle_coming_soon` to `handle_downloads_menu`; added `SETTINGS_DOWNLOADS` state with 8 callback handlers; implemented 8 new handler methods
        - `tests/test_handlers/conftest.py`: Updated `settings_handler` fixture with `TransmissionService` and `SABnzbdService` patches, mock objects with async methods, and `_mock_trans`/`_mock_sab` attrs on handler
        - `tests/test_handlers/test_settings_handler.py`: Added `TestDownloadsFlow` class with 11 test methods
    - **Notes:** `handle_coming_soon` still routes `settings_users` — will be replaced in task 1.3. Speed limit handler uses inline keyboard buttons (25%, 50%, 100%) following the existing `SabnzbdHandler` pattern.

- [x] **1.3** Users settings handler + final cleanup
    - **Context:**
        - **Why:** The "Users" button shows "Coming soon". Admins need to see user counts and toggle security features. Also, once both sub-menus are implemented, `handle_coming_soon` becomes dead code and must be removed along with its test.
        - **Architecture:** Same pattern as downloads — new handler methods, new `SETTINGS_USERS` state in ConversationHandler. User counts come from `config.get("admins", [])` and `config.get("authenticated_users", [])`. Security toggles flip `security.enableAdmin` and `security.enableAllowlist` via `config.update_nested()`.
        - **Key refs:**
            - `src/bot/handlers/settings.py:64-67` — `handle_coming_soon` routing for `settings_users`
            - `src/bot/handlers/settings.py:369-379` — `handle_coming_soon` method to remove
            - `tests/test_handlers/test_settings_handler.py:375-390` — `TestMisc.test_handle_coming_soon` to remove
            - `tests/conftest.py:71` — `MOCK_CONFIG_DATA` has `security.enableAdmin: False`, `security.enableAllowlist: False`, `admins: []`, `authenticated_users: [12345]`
        - **Watch out:** `config.get("security", {})` returns nested dict — need `.get("enableAdmin", False)` to read current value before flipping. No service dependencies for this sub-menu, just config reads/writes.
    - **Scope:** ~4 test methods, 2 handler methods, ConversationHandler wiring, dead code removal.
    - **Touches:** `tests/test_handlers/test_settings_handler.py`, `src/bot/handlers/settings.py`
    - **Action items:**
        - [RED] Write `TestUsersFlow` in `test_settings_handler.py`: `test_handle_users_menu_shows_keyboard`, `test_handle_users_toggle_admin`, `test_handle_users_toggle_allowlist`, `test_handle_users_back`
        - [GREEN] Update `get_handler()`: replace `handle_coming_soon` pattern for `settings_users`, add `SETTINGS_USERS` state with callback handlers for `usr_` prefixed actions
        - [GREEN] Implement `handle_users_menu` and `handle_users_toggle` methods
        - [GREEN] Remove `handle_coming_soon` method (no remaining routes)
        - [GREEN] Remove `test_handle_coming_soon` from `TestMisc`
    - **Success:** `pytest tests/test_handlers/test_settings_handler.py -v` passes, `pytest --tb=short -q` full suite green, `flake8 .` clean
    - **Completed:** 2026-02-20
    - **Learnings:**
        - `config.get("security", {})` returns the nested dict; must chain `.get("enableAdmin", False)` to read the flag before flipping.
        - `handle_users_toggle` uses a `key_map` dict to translate callback data (`admin`/`allowlist`) to dotted config keys (`security.enableAdmin`/`security.enableAllowlist`), keeping the handler generic for both toggles.
        - Removing `handle_coming_soon` was clean — no remaining routes pointed to it after both downloads and users were wired up.
    - **Key Changes:**
        - `src/bot/handlers/settings.py`: Added `get_users_keyboard` import; replaced `settings_users` routing from `handle_coming_soon` to `handle_users_menu`; added `SETTINGS_USERS` state with `usr_toggle_` and `usr_back` handlers; implemented `handle_users_menu` and `handle_users_toggle`; deleted `handle_coming_soon` method
        - `tests/test_handlers/test_settings_handler.py`: Added `TestUsersFlow` class with 4 test methods; removed `test_handle_coming_soon` from `TestMisc`
    - **Notes:** All "Coming soon" placeholders are now replaced. The settings ConversationHandler has 6 states: SETTINGS_MENU, SETTINGS_LANGUAGE, SETTINGS_SERVICE, SETTINGS_QUALITY, SETTINGS_DOWNLOADS, SETTINGS_USERS.
