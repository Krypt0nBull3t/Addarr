# Issue 202: Settings and admin controls do the wrong thing: Tasks

Plan: `docs/issues/issue-202/plan.md`. Branch: `fix/202-settings-admin-controls`.

### Phase 1: Settings and admin fixes (3 tasks)

**Goal:** `/settings` and `/webhooks` use the shared admin check, the Allowlist button counts `allow_list`, and a service toggle says a restart is needed.

- [x] **1.1** F070: one admin check (and `admins: None` in the Users menu)
    - **Context:**
        - **Why:** `settings.py` and `webhooks.py` import `is_admin` from `src.definitions`. That copy compares ints, reads `./config.yaml` from the working directory and raises `TypeError` on an empty `admins:`.
        - **Architecture:** Import `is_admin` from `src.utils.helpers` (`str()` compare, `or []`), as `auth.py`, `downloads.py` and `media/handler.py` do. Delete the copy in `src/definitions.py`; keep `get_admins` and the rest (issue #226 removes them).
        - **Key refs:** `src/bot/handlers/settings.py:37,658,698`, `src/bot/handlers/webhooks.py:29`, `src/definitions.py:60-62`, `src/utils/helpers.py:63`, `tests/test_handlers/conftest.py` (`settings_handler`, `admin_mode`)
        - **Watch out:** `settings_handler` patches `src.bot.handlers.settings.is_admin`. For the real check set `settings_handler._mock_is_admin.side_effect = helpers.is_admin` and patch `src.utils.helpers.config`. `len(config.get("admins", []))` returns `len(None)` when the key is present but empty: use `config.get("admins") or []`. Integration tests patch `src.bot.handlers.settings.is_admin`; the name stays valid.
    - **Scope:** Imports, the `definitions.py` deletion, the admins-count guard, tests
    - **Touches:** `src/bot/handlers/settings.py`, `src/bot/handlers/webhooks.py`, `src/definitions.py`, `tests/test_definitions.py`, `tests/test_handlers/test_settings_handler.py`, `tests/test_handlers/test_webhooks_handler.py`
    - **Action items:**
        - [RED] `tests/test_definitions.py`: replace `test_is_admin_true` and `test_is_admin_false` with `test_is_admin_not_defined_in_definitions`
        - [RED] `TestAdminCheck` in `test_settings_handler.py`: `admins: None` raises no `TypeError` in `handle_settings`; `admins: ["12345"]` makes user 12345 an admin; `handle_users_menu` with `admins: None` returns `States.SETTINGS_USERS`
        - [RED] `TestWebhookAdminCheck` in `test_webhooks_handler.py`, patching `src.utils.helpers.config` only: `admins: None` returns `ConversationHandler.END`; `admins: ["12345"]` returns the menu state
        - [GREEN] Change both imports, delete `is_admin` from `definitions.py`, guard `settings.py:658,698` with `or []`
    - **Success:** The new tests fail before the change and pass after; `pytest tests/test_handlers tests/test_definitions.py` passes; flake8 and mypy clean
    - **Completed:** 2026-11-04
    - **Learnings:**
        - The `settings_handler` fixture patches `src.bot.handlers.settings.is_admin`, so it cannot prove the real check. A separate fixture (`real_admin_settings_handler`) patches `config` and leaves `is_admin` real.
        - Before the change the new tests failed on `FileNotFoundError: config.yaml not found` (the old check reads `./config.yaml`) and on `TypeError` at `settings.py:698`.
    - **Key Changes:**
        - `settings.py` and `webhooks.py` import `is_admin` from `src.utils.helpers`; `definitions.is_admin` is deleted.
        - `settings.py` counts admins with `len(config.get("admins") or [])` in `handle_users_menu` and `handle_users_toggle`.
        - Tests: `TestAdminCheck` (settings), `TestWebhookAdminCheck` (webhooks), `test_is_admin_not_defined_in_definitions`.
    - **Notes:** `get_admins` and the rest of `src/definitions.py` stay for issue #226.

- [x] **1.2** F072: Allowlist button counts `allow_list`
    - **Context:**
        - **Why:** The button shows `len(authenticated_users)`, so an admin sees "Allowlist (5 users)" while `allow_list` is empty and turns the allowlist on, which locks out every non-admin.
        - **Architecture:** Pass `len(config.get("allow_list") or [])` where `settings.py` builds `get_users_keyboard`.
        - **Key refs:** `src/bot/handlers/settings.py:659,699`, `src/bot/keyboards.py:285-303` (`get_users_keyboard`, parameter `auth_count`)
        - **Watch out:** Rename `auth_count` to `allow_count` in the keyboard and its callers and tests (grep `get_users_keyboard`). Keep the button text "Allowlist (N users)". `allow_list` may be `None`.
    - **Scope:** Two call sites, one parameter rename, tests
    - **Touches:** `src/bot/handlers/settings.py`, `src/bot/keyboards.py`, `tests/test_handlers/test_settings_handler.py`, `tests/test_bot/test_keyboards.py`
    - **Action items:**
        - [RED] `test_users_menu_allowlist_count_uses_allow_list` and `test_users_toggle_allowlist_count_uses_allow_list`: 5 `authenticated_users`, `allow_list: []`; patch `src.bot.handlers.settings.get_users_keyboard`; the fourth argument is `0`
        - [RED] Same check with `allow_list: None`
        - [GREEN] Change both call sites and the keyboard parameter name
    - **Success:** The tests fail before and pass after; `pytest tests/test_handlers tests/test_bot` passes
    - **Completed:** 2026-11-04
    - **Learnings:**
        - `settings_handler._mock_cfg.get.side_effect` can return per-key data, so one parametrized test covers both call sites (`handle_users_menu`, `handle_users_toggle`) and both empty shapes (`[]`, `None`).
    - **Key Changes:**
        - `settings.py` passes `len(config.get("allow_list") or [])` at both call sites.
        - `get_users_keyboard` parameter `auth_count` is now `allow_count` (keyboard and `test_keyboards.py`).
    - **Notes:** The button text stays "Allowlist (N users)".

- [ ] **1.3** F071: restart notice on the service toggle
    - **Context:**
        - **Why:** `handle_service_toggle` writes `<service>.enable`, but `MediaService` and `SABnzbdService` build their clients once at boot. The reply hides that the change needs a restart.
        - **Architecture:** Append a translated notice to the toggle reply, as `WebhookPortSaved` does. No change to the services.
        - **Key refs:** `src/bot/handlers/settings.py:320-349`, `translations/addarr.en-us.yml:171-172` (`Settings.ServiceEnabled`), `translations/addarr.en-us.yml:359` (`WebhookPortSaved`), skill `i18n-key`
        - **Watch out:** New key `Settings.ServiceRestartNotice` in `translations/addarr.template.yml` and all 9 locale files, next to `Settings.ServiceDisabled`. English: `Restart the bot for this to take effect.` The key has no placeholder. Dutch text uses Netherlands Dutch. Run `PYTHONIOENCODING=utf-8 python run.py --validate-i18n`.
    - **Scope:** One key in 10 files, one handler change, tests
    - **Touches:** `src/bot/handlers/settings.py`, `translations/` (template + 9 locales), `tests/test_handlers/test_settings_handler.py`
    - **Action items:**
        - [RED] `test_handle_service_toggle_reply_has_restart_notice`, parametrized for enable and disable: the `edit_text` text contains the notice (read how the mock translation returns text in `conftest.py`)
        - [GREEN] Build the reply from the notice; add the key to the template and all locales
    - **Success:** The test fails before and passes after; `--validate-i18n` passes

### Phase 2: Calendar add path and default quality profile (2 tasks)

**Goal:** No calendar add path exists that no button reaches, and the normal add flow uses `<service>.quality.defaultProfileId` and skips the picker.

- [ ] **2.1** F073a: delete the calendar add path
    - **Context:**
        - **Why:** The *arr calendars list only library items, so `in_library` is always true and no Add button shows. If reached, the path skips `adminRestrictions`.
        - **Architecture:** Delete the code, its translation keys and its tests. `/upcoming` stays read-only.
        - **Key refs:** `src/bot/handlers/calendar.py:28-33,97-98,142-184`, `src/bot/keyboards.py:552-600` (Add button at `:582`), `src/services/media.py:545-596` (`in_library` in both normalizers), `.claude/skills/addarr-handlers/references/callbacks.md`, `tests/test_handlers/test_calendar_handler.py:232-337,406`
        - **Watch out:** Keep the `Add` key (used at `keyboards.py:419`). Remove `CalendarAddSuccess` and `CalendarAddFailed` from the template and all locales (grep to confirm no other use). Remove `asyncio` and `config` imports from `calendar.py` only if unused. `add_movie_with_profile` and `add_series_with_profile` stay (the add flow uses them). Update the skill reference that names `cal_add_`; `tests/test_architecture/test_skills.py` and `test_repo_docs.py` must stay green.
    - **Scope:** Handler, keyboard, service normalizers, translations, tests, skill note
    - **Touches:** `src/bot/handlers/calendar.py`, `src/bot/keyboards.py`, `src/services/media.py`, `translations/`, `tests/test_handlers/test_calendar_handler.py`, `tests/test_bot/test_keyboards.py`, `tests/test_services/test_media_service.py`, `.claude/skills/addarr-handlers/references/callbacks.md`
    - **Action items:**
        - [RED] `test_calendar_keyboard_has_no_add_button` and `test_cal_add_callback_is_ignored` (`cal_add_movie_1` reaches the `query.answer()` branch and adds nothing)
        - [GREEN] Delete the code and keys listed above; delete the `cal_add_*`, `_pick_profile_id` and Add-button tests; drop `in_library` from fixtures and asserts
    - **Success:** `pytest tests/test_handlers tests/test_bot tests/test_services tests/test_architecture` passes; `--validate-i18n` passes

- [ ] **2.2** F073b: default quality profile in the add flow
    - **Context:**
        - **Why:** `defaultProfileId` is read only by the calendar add path, which task 2.1 deletes. The `/settings` default profile must act in the normal add flow.
        - **Architecture:** `handle_selection` calls `add_fn`, which only returns `{"type": "quality_selection", "profiles", "root_folder", ["seasons"]}`. Add `MediaHandler._default_profile_id(search_type, profiles) -> Optional[int]` and extract the code from `profile_id = int(...)` to the end of `handle_quality_selection` into `_continue_with_profile(query, context, profile_id: Union[int, str]) -> int`. `handle_selection` calls it when a default exists. Series and artists keep their season and album pickers.
        - **Key refs:** `src/bot/handlers/media/handler.py:396-627` (`handle_selection`, `handle_quality_selection`), `src/bot/handlers/media/dispatch.py` (`MEDIA_CONFIG[...]["config_key"]`), `tests/test_handlers/test_media_handler.py:260-285,527-552`
        - **Watch out:** `config.get(service) or {}` and `.get("quality") or {}`: the values can be `None`. Return the id only when some `p["id"] == id` in `profiles` (a stale id falls back to the picker). `int(profile_id)` and the `SelectionProcessError` reply stay inside the `try` of `_continue_with_profile`. Issue #203 puts a modify check just before each add request. That call now lives in `_continue_with_profile`, so the default path is covered only if the #203 check sits there; do not call `add_*_with_profile` from `handle_selection` directly. The `media_handler` fixture does not patch `config`: patch `src.bot.handlers.media.handler.config` in each test.
    - **Scope:** Two helper methods, one branch in `handle_selection`, tests
    - **Touches:** `src/bot/handlers/media/handler.py`, `tests/test_handlers/test_media_handler.py`
    - **Action items:**
        - [RED] `test_handle_selection_default_profile_skips_picker`: radarr default `1`, profiles `[1, 2]`; `add_movie_with_profile` awaited once with `("123", 1, "/movies")`; result `ConversationHandler.END`; no `quality_` button sent
        - [RED] `test_handle_selection_no_default_shows_picker` and `test_handle_selection_stale_default_shows_picker` (default `99`): result `QUALITY_SELECT`
        - [RED] `test_handle_selection_default_series_goes_to_season_select` (result `SEASON_SELECT`) and `test_handle_selection_default_is_per_service` (radarr default set, search type `series`, picker shows)
        - [GREEN] Implement `_default_profile_id` and `_continue_with_profile`; call them from `handle_selection` and `handle_quality_selection`
    - **Success:** New tests fail before and pass after; existing `handle_quality_selection` tests stay green; `python scripts/test_runner.py handlers --coverage` shows full coverage for the changed lines

### Phase 3: Verify (1 task)

**Goal:** The whole change passes the CI checks.

- [ ] **3.1** Preflight
    - **Context:**
        - **Why:** The PR must pass every CI job, including the 100% coverage gate.
        - **Architecture:** Flow `preflight` (`references/preflight.md`) through the suite lock.
        - **Key refs:** `.github/workflows/ci.yml`
        - **Watch out:** After any fix, re-run from the first check.
    - **Scope:** flake8, mypy, `--validate-i18n`, unit tests with the coverage gate, integration tests, architecture tests
    - **Touches:** none
    - **Action items:**
        - [GREEN] Run the preflight
    - **Success:** All checks pass
