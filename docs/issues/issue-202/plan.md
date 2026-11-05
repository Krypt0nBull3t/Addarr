# Issue 202: Settings and admin controls do the wrong thing

**Issue:** https://github.com/Krypt0nBull3t/Addarr/issues/202 (audit findings F072, F070, F071, F073)
**Branch:** `fix/202-settings-admin-controls`

## Context

Four defects in `/settings`, `/webhooks` and `/upcoming`. Root causes, verified in the tree at `origin/development`:

- **F072** `handle_users_menu` and `handle_users_toggle` (`src/bot/handlers/settings.py:659`, `:699`) pass `len(config.get("authenticated_users", []))` as the Allowlist count. The allowlist is `allow_list`. A user who turns the allowlist on while `allow_list` is empty locks out every non-admin.
- **F070** `settings.py:37` and `webhooks.py:29` import `is_admin` from `src.definitions`. That copy (`definitions.py:60-62`) compares ints, reads `./config.yaml` from the working directory and raises `TypeError` on `admins:` with no value. The rest of the bot uses `src.utils.helpers.is_admin` (`str()` compare, `or []`). Same bug class: `len(config.get("admins", []))` at `settings.py:658` and `:698` raises `TypeError` when `admins:` is empty, because the key exists with value `None`.
- **F071** `handle_service_toggle` (`settings.py:320-349`) writes `<service>.enable`, but `MediaService` and `SABnzbdService` build their clients once at boot. The reply says "enabled/disabled <service>" and hides that a restart is needed. Fix: tell the user (the same wording as `WebhookPortSaved`). No change to the services.
- **F073** The *arr calendars list only library items, so `in_library` is always true and the calendar Add button (`keyboards.py:582`) never shows. The handler path behind it (`calendar.py:28-33`, `:142-184`) skips `adminRestrictions`. The `defaultProfileId` setting is read only there. Decision (issue, 2026-10-28): delete the calendar add path, keep the `/settings` default quality profile, and use it in the normal add flow.

Scope decisions from the orchestrator (step 3c): the admins-count fix is in scope; unused `CalendarAdd*` keys and their tests are deleted; a `defaultProfileId` that is not in the service's profile list falls back to the picker; the default-profile path must reach the add request through `_continue_with_profile`, the same call the picker path uses. Issue #203 puts its modify check just before each add request (`add_*_with_profile` / `_add_media_with_profile`), which moves into `_continue_with_profile`. `add_fn` only returns the profile list and adds nothing.

No new pattern, singleton or state. `src/bot/states.py` and `dispatch.py` do not change.

## Design

**Default profile in the add flow.** `handle_selection` (`src/bot/handlers/media/handler.py:396`) already calls `add_fn` and gets `{"type": "quality_selection", "profiles": [...], "root_folder": ..., ["seasons": ...]}`. Add:

```python
def _default_profile_id(self, search_type: str, profiles: list) -> Optional[int]:
    """Saved /settings default profile id for this media type, if it is still in profiles."""
```

It reads `config.get(MEDIA_CONFIG[search_type]["config_key"]) or {}`, then `quality` the same way, then `defaultProfileId`. It returns the id only when some `p["id"] == id` in `profiles`, else `None`.

Extract the body of `handle_quality_selection` from `profile_id = int(...)` to the final `return ConversationHandler.END` (including its `try/except` and `SelectionProcessError` reply) into:

```python
async def _continue_with_profile(self, query, context, profile_id: Union[int, str]) -> int:
```

`handle_quality_selection` keeps the cancel check and calls `return await self._continue_with_profile(query, context, query.data.replace("quality_", ""))`. `handle_selection` calls it after setting `context.user_data["quality_data"] = result` when `_default_profile_id` is not `None`; its return value (END, `SEASON_SELECT` or `ALBUM_SELECT`) is returned. Series and artist keep their season and album pickers. `_continue_with_profile` must do `int(profile_id)` inside the `try`, so a bad value keeps the old error reply.

**Admin check.** Import `is_admin` from `src.utils.helpers` in `settings.py` and `webhooks.py`. Delete `is_admin` from `src/definitions.py`. Keep `get_admins` and the rest of that file: issue #226 (F260) deletes them later. Tests patch `src.bot.handlers.settings.is_admin` and `src.bot.handlers.webhooks.is_admin`; those names stay valid.

**Restart notice.** New translation key `Settings.ServiceRestartNotice` in `translations/addarr.template.yml` and all 9 locales, placed next to `Settings.ServiceDisabled`. English text: `Restart the bot for this to take effect.` The toggle reply becomes `f"✅ {text}\n{notice}"`. Use the `i18n-key` skill for the locale files.

## Tasks (TDD order)

### 1. F070: one admin check

- Tests (red first):
  - `tests/test_definitions.py`: delete `test_is_admin_true` and `test_is_admin_false`; add `test_is_admin_not_defined_in_definitions`: `assert not hasattr(definitions, "is_admin")`.
  - `tests/test_handlers/test_settings_handler.py`, class `TestAdminCheck`: with `settings_handler._mock_is_admin.side_effect = helpers.is_admin` and `patch("src.utils.helpers.config", cfg)`:
    - `test_settings_admins_none_does_not_raise`: `admins: None`, user 12345, `handle_settings` replies with the rejection and raises no `TypeError`.
    - `test_settings_quoted_admin_id_is_admin`: `admins: ["12345"]`, `handle_settings` shows the menu.
    - `test_users_menu_admins_none_does_not_raise`: `handle_users_menu` with `admins: None` returns `States.SETTINGS_USERS`.
  - `tests/test_handlers/test_webhooks_handler.py`, class `TestWebhookAdminCheck`: patch `src.utils.helpers.config` (not `webhooks.is_admin`): `admins: None` gives `ConversationHandler.END` with no `TypeError`; `admins: ["12345"]` returns the menu state.
- Code: the import changes, the `definitions.py` deletion, `settings.py:658,698` use `config.get("admins") or []`.

### 2. F072: allowlist count

- Test: `TestUsersFlow.test_users_menu_allowlist_count_uses_allow_list` and `test_users_toggle_allowlist_count_uses_allow_list` in `test_settings_handler.py`. Set `config.get` so `authenticated_users` has 5 ids and `allow_list` is `[]`; patch `src.bot.handlers.settings.get_users_keyboard`; assert it is called with the fourth argument `0`. Add a case with `allow_list: None` (also 0).
- Code: `settings.py:659` and `:699` use `len(config.get("allow_list") or [])`. `keyboards.py` parameter `auth_count` becomes `allow_count`; the button text keeps "Allowlist (N users)".

### 3. F071: restart notice

- Tests: `TestServiceFlow.test_handle_service_toggle_reply_has_restart_notice` (enable and disable, parametrized): the `edit_text` text contains the `Settings.ServiceRestartNotice` key (the mock translation returns the key or default; follow how neighbouring tests read it). The key exists in the template and the 9 locales: `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` passes.
- Code: `handle_service_toggle` adds the notice; add the key to the template and all locales.

### 4. F073a: delete the calendar add path

- Tests: delete the `cal_add_*` tests and the `_pick_profile_id` test in `tests/test_handlers/test_calendar_handler.py` (lines ~232-337, ~406); drop `in_library` from its fixtures. Delete the Add-button tests in `tests/test_bot/test_keyboards.py` and the `in_library` asserts in `tests/test_services/test_media_service.py`. Add `test_calendar_keyboard_has_no_add_button` (keyboard has no `cal_add_` callback for an item list) and `test_cal_add_callback_is_ignored` (`cal_add_movie_1` falls to the `query.answer()` branch).
- Code: remove `_pick_profile_id`, `_handle_add`, the `cal_add_` branch, the unused `asyncio` import and the `config` import (if unused) in `calendar.py`; the Add button in `get_calendar_items_keyboard`; `in_library` in both normalizers in `services/media.py`; `CalendarAddSuccess` and `CalendarAddFailed` in the template and all locales. Keep the `Add` key (used by `keyboards.py:419`). Update `.claude/skills/addarr-handlers/references/callbacks.md` where it names `cal_add_`, and check `tests/test_architecture/test_skills.py` still passes.

### 5. F073b: default profile in the add flow

- Tests in `tests/test_handlers/test_media_handler.py` (patch `src.bot.handlers.media.handler.config`):
  - `test_handle_selection_default_profile_skips_picker`: `radarr.quality.defaultProfileId = 1`, profiles `[1, 2]`; `add_movie_with_profile` awaited once with `("123", 1, "/movies")`, result is `ConversationHandler.END`, no `quality_` button is sent.
  - `test_handle_selection_no_default_shows_picker`: no default, result `QUALITY_SELECT`.
  - `test_handle_selection_stale_default_shows_picker`: default `99` not in profiles, result `QUALITY_SELECT`.
  - `test_handle_selection_default_series_goes_to_season_select`: `sonarr` default set, result `SEASON_SELECT`.
  - `test_handle_selection_default_is_per_service`: radarr default set, search type `series`, picker shows.
  - Existing `handle_quality_selection` tests stay green (refactor).
- Code: `_default_profile_id` and `_continue_with_profile` as in Design.

### 6. Verify

Preflight per `references/preflight.md` through the suite lock. `mypy src/`, `flake8`, `--validate-i18n`, unit tests with the 100% gate, integration, architecture. Run the `arr-api-contract-checker` only if `src/api/` changes (it does not).

## Acceptance (from the issue)

Each new test fails before the fix and passes after: F072 (count 0), F070 (`admins: None`, `["12345"]`, patched config), F071 (notice key, template and 9 locales), F073 (default profile sent, picker skipped; picker still shows with no default; calendar add tests removed). `pytest`, `flake8`, `mypy src/` and `--validate-i18n` pass.

## Risks

- #203 (modify check on add requests) edits `handle_selection` and `handle_quality_selection` too. It puts the check just before each add request. The default-profile path adds through `_continue_with_profile`, so the #203 check covers it only if the check sits in `_continue_with_profile`. `add_fn` adds nothing. Whichever PR merges second rebases and must keep the check in `_continue_with_profile`. The PR body says this.
- #226 deletes the rest of `src/definitions.py`; this PR only removes `is_admin`.
- The restart notice does not change SABnzbd's frozen `_enabled`; the notice is the fix the issue asks for.
