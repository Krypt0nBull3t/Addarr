# Issue #166: Retroactive Tests for Migration-Day Bugfixes

## Context

Three commits were pushed directly to `development` during the DietPi migration session (2026-03-14) without tests or PR:

- `d8db2e3` — Docker compatibility and UI improvements
- `94298b0` — Wire delete menu button to actual delete handler
- `2809261` — NotAuthorized message directs to /auth not /start

## Scope

Write tests only — no implementation changes. All code is already merged to development.

## Test Areas

### 1. Config Auto-Defaults (src/config/settings.py)
- `_apply_default_key()` correctly traverses nested keys and sets defaults
- `_validate_config()` non-interactive branch applies defaults without error
- Existing: `TestMissingKeysLogic` covers `_get_missing_keys()` only

### 2. Quality Profile UX (src/bot/handlers/settings.py)
- `handle_quality_menu()` passes `current_profile_id` to keyboard
- Keyboard shows `"✅ "` prefix on current profile only
- `handle_quality_select()` strips prefix and shows profile name in confirmation
- Downloads menu shows empty state message when no clients configured
- Existing: Basic handler structure only

### 3. Delete Menu Routing (src/bot/handlers/delete.py + start.py)
- `get_delete_keyboard()` returns correct structure (3 media types + cancel)
- Main menu `menu_delete` callback routes to delete handler
- Existing: Some delete handler tests, no keyboard method or routing tests

### 4. NotAuthorized Message (src/bot/handlers/auth.py)
- `require_auth()` default message references `/auth` not `/start`
- Existing: Decorator tested but message content not verified

### 5. Dutch Flag (src/bot/keyboards.py)
- Language keyboard uses 🇳🇱 for Dutch, not 🇧🇪
- Existing: Keyboard structure tested, emoji content not verified

## Approach

Add tests to existing test files where possible. No new test files unless necessary. Follow project testing patterns (MockConfig, factory fixtures, patch at import site).
