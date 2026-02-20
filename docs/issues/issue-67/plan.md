# Issue #67: Implement Downloads & Users Settings Sub-Menus + Cleanup

## Context

Issue #16 (settings management) is already fully implemented — language selection, quality profiles, and service toggles all work. However, the Downloads and Users buttons in the settings menu still show "Coming soon" placeholders. This plan implements those two sub-menus and cleans up dead code discovered during exploration.

## Scope

**New features:**
- Downloads sub-menu: Transmission enable/disable + turtle mode, SABnzbd enable/disable + speed limits + pause/resume
- Users sub-menu: view admin/authenticated user counts, toggle `security.enableAdmin` and `security.enableAllowlist`

**Cleanup:**
- Remove dead `AWAITING_SETTING_ACTION` state from `src/bot/states.py:23`
- Remove dead `get_service_toggle_keyboard` from `src/bot/keyboards.py:138-158`
- Add `per_message=False` to all 4 ConversationHandlers to silence PTB warning
- Remove corresponding dead-code tests

## Callback Data Namespace

| Prefix | Purpose | Examples |
|--------|---------|---------|
| `dl_` | Downloads sub-menu | `dl_transmission`, `dl_sabnzbd` |
| `dl_trans_` | Transmission actions | `dl_trans_toggle`, `dl_trans_turtle` |
| `dl_sab_` | SABnzbd actions | `dl_sab_toggle`, `dl_sab_speed_25`, `dl_sab_pause`, `dl_sab_resume` |
| `usr_` | Users sub-menu | `usr_toggle_admin`, `usr_toggle_allowlist` |

## Files to Modify

| File | Changes |
|------|---------|
| `src/bot/states.py` | Add `SETTINGS_DOWNLOADS`, `SETTINGS_USERS`; remove `AWAITING_SETTING_ACTION` |
| `src/bot/keyboards.py` | Add 4 new keyboard functions; remove `get_service_toggle_keyboard` |
| `src/bot/handlers/settings.py` | Add downloads + users handler methods, new states in ConversationHandler, new imports, `per_message=False` |
| `src/bot/handlers/media.py` | Add `per_message=False` |
| `src/bot/handlers/start.py` | Add `per_message=False` |
| `src/bot/handlers/auth.py` | Add `per_message=False` |
| `tests/test_bot/test_states.py` | Update for new/removed states |
| `tests/test_bot/test_keyboards.py` | Add new keyboard tests; remove `TestServiceToggleKeyboard` |
| `tests/test_handlers/conftest.py` | Extend `settings_handler` fixture with Transmission/SABnzbd mocks |
| `tests/test_handlers/test_settings_handler.py` | Add `TestDownloadsFlow`, `TestUsersFlow`; update `TestMisc` |

## Key Implementation Notes

- **SABnzbdService raises ValueError** if not enabled (`src/services/sabnzbd.py:23-24`). Settings handler must catch this in `__init__` and set `self.sabnzbd_service = None`.
- **TransmissionService is safe** — constructor never raises, lazy-initializes client via property.
- **MOCK_CONFIG_DATA** has `transmission.enable: False`, `sabnzbd.enable: False`, `security.enableAdmin: False`, `security.enableAllowlist: False`, `admins: []`, `authenticated_users: [12345]`.
- Reuse existing `handle_settings_from_callback` for all back-to-settings-menu navigation.

## TDD Steps

### Step 1: Dead code removal + per_message fix

**Tests first:**
- `test_states.py`: Remove `AWAITING_SETTING_ACTION` assertion from `test_string_states_are_strings` (line 51); add test asserting `not hasattr(States, "AWAITING_SETTING_ACTION")`
- `test_keyboards.py`: Remove `TestServiceToggleKeyboard` class (lines 203-239); add test asserting `get_service_toggle_keyboard` is not in module

**Implementation:**
- `states.py`: Delete line 23 (`AWAITING_SETTING_ACTION`)
- `keyboards.py`: Delete lines 138-158 (`get_service_toggle_keyboard`)
- Add `per_message=False` to ConversationHandlers in: `settings.py`, `media.py`, `start.py`, `auth.py`

**Verify:** `pytest tests/test_bot/ -v && flake8 .`

### Step 2: New states + keyboard functions

**Tests first:**
- `test_states.py`: Add tests for `SETTINGS_DOWNLOADS` and `SETTINGS_USERS` — existence, type (str), uniqueness with other settings states
- `test_keyboards.py`: Add `TestDownloadsKeyboard`, `TestTransmissionSettingsKeyboard`, `TestSabnzbdSettingsKeyboard`, `TestUsersKeyboard` — verify correct callback data in each keyboard

**Implementation:**
- `states.py`: Add `SETTINGS_DOWNLOADS = "settings_downloads"`, `SETTINGS_USERS = "settings_users"`
- `keyboards.py`: Add 4 functions:
  - `get_downloads_keyboard(transmission_enabled, sabnzbd_enabled)` — row per enabled client + back
  - `get_transmission_settings_keyboard(enabled, alt_speed_enabled)` — enable toggle + turtle toggle + back
  - `get_sabnzbd_settings_keyboard(enabled)` — enable toggle + speed buttons (25/50/100) + pause/resume + back
  - `get_users_keyboard(admin_enabled, allowlist_enabled, admin_count, auth_count)` — info + toggles + back

**Verify:** `pytest tests/test_bot/ -v`

### Step 3: Downloads settings handler

**Tests first** (new `TestDownloadsFlow` class in `test_settings_handler.py`):
- `test_handle_downloads_menu_shows_keyboard` — returns `SETTINGS_DOWNLOADS`
- `test_handle_transmission_settings` — shows transmission keyboard
- `test_handle_transmission_toggle` — calls `config.update_nested("transmission.enable", ...)` + save
- `test_handle_transmission_turtle` — calls `transmission_service.set_alt_speed()`
- `test_handle_transmission_turtle_error` — service error handled gracefully
- `test_handle_sabnzbd_settings` — shows sabnzbd keyboard
- `test_handle_sabnzbd_toggle` — calls `config.update_nested("sabnzbd.enable", ...)` + save
- `test_handle_sabnzbd_speed` — calls `sabnzbd_service.set_speed_limit(percentage)`
- `test_handle_sabnzbd_pause` / `test_handle_sabnzbd_resume`
- `test_handle_downloads_back` — returns to `SETTINGS_MENU`

**Fixture update** (`conftest.py`): Extend `settings_handler` to also patch `TransmissionService` and `SABnzbdService` with mocks.

**Implementation** (`settings.py`):
- Add imports: `TransmissionService`, `SABnzbdService`, new keyboard functions
- `__init__`: Add `self.transmission_service = TransmissionService()`, wrap `self.sabnzbd_service = SABnzbdService()` in try/except ValueError
- `get_handler()`: Replace `handle_coming_soon` for `settings_downloads` pattern, add `SETTINGS_DOWNLOADS` state
- Add handler methods for downloads flow

**Verify:** `pytest tests/test_handlers/test_settings_handler.py -v`

### Step 4: Users settings handler

**Tests first** (new `TestUsersFlow` class):
- `test_handle_users_menu_shows_keyboard` — returns `SETTINGS_USERS`
- `test_handle_users_toggle_admin` — flips `security.enableAdmin`, calls save
- `test_handle_users_toggle_allowlist` — flips `security.enableAllowlist`, calls save
- `test_handle_users_back` — returns to `SETTINGS_MENU`

**Implementation** (`settings.py`):
- `get_handler()`: Replace `handle_coming_soon` for `settings_users` pattern, add `SETTINGS_USERS` state
- Add methods: `handle_users_menu`, `handle_users_toggle`
- Remove `handle_coming_soon` (nothing routes to it anymore)
- Update `TestMisc`: Remove `test_handle_coming_soon`

**Verify:** `pytest tests/test_handlers/test_settings_handler.py -v`

### Step 5: Final verification

```bash
pytest --tb=short -q
pytest --cov=src/bot/handlers/settings --cov=src/bot/keyboards --cov=src/bot/states --cov-report=term-missing
flake8 .
```

## Notes

- No per-user settings — all toggles modify global `config.yaml` (admin-only access enforced by `@require_auth` + `is_admin()`)
- Users v1 is read-heavy: view counts + toggle features. Add/remove individual users deferred (requires text input conversation states)
- Service `set_speed_limit` already exists in `SABnzbdService` (`src/services/sabnzbd.py`)
- `TransmissionService.set_alt_speed` already exists (`src/services/transmission.py:45`)
