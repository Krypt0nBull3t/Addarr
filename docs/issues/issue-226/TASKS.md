# Issue #226: Delete dead code and its tests

Plan: `docs/issues/issue-226/plan.md`. Branch `refactor/226-delete-dead-code`, base cf51f57.

Deletion tasks have no new behavior, so the [RED] step is the proof that nothing reads the code
(a grep of `src/`, `tests/`, `scripts/`) and the [GREEN] step is the deletion. Coverage must stay at 100%.

### Phase 1: Delete the dead code (9 tasks)

**Goal:** `src/` has no function, module, key or constant without a live reader.

- [x] **1.1** Delete the dead helpers in `src/utils/helpers.py`
    - **Context:**
        - **Why:** F260: `check_auth`, `get_authorized_chats`, `save_chat_id` and `is_authenticated` have no caller
        - **Architecture:** `is_admin`, `is_allowed`, `admin_only` and `format_bytes` in the same file are live: keep them
        - **Key refs:** `src/utils/helpers.py:18-51`, `:87-89`; `tests/test_utils/test_helpers.py` (`TestSaveChatId`, `TestCheckAuth`, `TestGetAuthorizedChats`, `TestIsAuthenticated`)
        - **Watch out:** `AuthHandler.is_authenticated` in `src/bot/handlers/auth.py:129` is a different, live method. `CHATID_PATH` stays defined in `src/definitions.py` (#218 deletes it later). Drop imports left unused (`CHATID_PATH`, `os`, `List`) so flake8 passes
    - **Scope:** 4 functions, their tests, leftover imports
    - **Touches:** `src/utils/helpers.py`, `tests/test_utils/test_helpers.py`
    - **Action items:**
        - [RED] Grep `src/`, `tests/`, `scripts/` for each name: only the definition, `helpers.py:89` and the tests reference them
        - [GREEN] Delete the 4 functions and the 4 test classes with their imports
        - [GREEN] Remove unused imports
    - **Success:** `scripts/test_runner.py utils --coverage` passes, flake8 clean
    - **Completed:** 2026-11-05
    - **Learnings:**
        - `AsyncMock` in `test_helpers.py` became unused with the deleted tests: flake8 F401
        - The module docstring named chat ID management: reworded
    - **Key Changes:**
        - Deleted `check_auth`, `get_authorized_chats`, `save_chat_id`, `is_authenticated` from `src/utils/helpers.py`, with imports `os`, `List`, `CHATID_PATH`
        - Deleted `TestSaveChatId`, `TestCheckAuth`, `TestGetAuthorizedChats`, `TestIsAuthenticated`
    - **Notes:** `CHATID_PATH` stays in `src/definitions.py` (#218 removes it)

- [ ] **1.2** Delete the dead functions in `src/definitions.py`
    - **Context:**
        - **Why:** F260: `load_config`, `get_admins`, `get_allowed_chats` and `is_allowed_chat` have no caller since #202 moved `is_admin` to `helpers.py`
        - **Architecture:** `definitions.py` keeps only constants (`CHAT_MODES`, the paths)
        - **Key refs:** `src/definitions.py:42-65`; `tests/test_definitions.py` (`TestLoadConfig`, `TestGetAdmins`, `TestGetAllowedChats`, `TestIsAllowedChat`)
        - **Watch out:** Keep `TestModuleDoesNotExportDeadCode`, `TestPreferencesPath` and `TestIsAdmin` (asserts `is_admin` is not defined here; still true). After the deletion `Path` and `yaml` are unused. Check `tests/` for patches of `src.definitions.load_config`
    - **Scope:** 4 functions, their tests, leftover imports
    - **Touches:** `src/definitions.py`, `tests/test_definitions.py`
    - **Action items:**
        - [RED] Grep for the 4 names in `src/`, `tests/`, `scripts/`, `run.py`: only definitions and `test_definitions.py`
        - [GREEN] Delete the functions, their tests and the unused imports
    - **Success:** `grep -n "^def " src/definitions.py` returns nothing; `scripts/test_runner.py config --coverage` and `pytest tests/test_definitions.py` pass

- [ ] **1.3** Delete the dead models
    - **Context:**
        - **Why:** F260: `src/models/media.py` and `src/models/notification.py` are imported only by `src/models/__init__.py`
        - **Architecture:** `src/models/webhook.py` is live (`webhook.py`, `webhook_formatter.py`): the package stays
        - **Key refs:** `src/models/__init__.py` (re-exports), `tests/test_models/test_media.py`, `tests/test_models/test_notification.py`, `tests/test_models/conftest.py`, `scripts/test_runner.py:14`, CLAUDE.md line 77
        - **Watch out:** #225 does not delete the two test files; this task does, in the same commit. `tests/test_models/conftest.py` loads the package through `importlib`: it must still import after the trim
    - **Scope:** 2 modules, 2 test files, `__init__.py`, docs text
    - **Touches:** `src/models/`, `tests/test_models/`, `scripts/test_runner.py`, `CLAUDE.md`
    - **Action items:**
        - [RED] Grep `src/`, `tests/`, `scripts/` for `models.media`, `models.notification`, `MediaItem`, `NotificationType`: only models and their tests
        - [GREEN] Delete the 2 modules and the 2 test files
        - [GREEN] Trim `src/models/__init__.py` (docstring about webhook models, no deleted imports); fix `tests/test_models/conftest.py` if it names them
        - [GREEN] Change the `models` description (`Data models (media, notification)`) in `scripts/test_runner.py` and CLAUDE.md to webhook models
    - **Success:** `scripts/test_runner.py models --coverage` passes, flake8 and mypy clean

- [ ] **1.4** Delete `get_metadata_profiles` in `src/api/lidarr.py`
    - **Context:**
        - **Why:** F260: no service or handler calls it
        - **Architecture:** `LidarrClient` methods that the service uses stay
        - **Key refs:** `src/api/lidarr.py:209`; `tests/test_api/test_lidarr.py:635-671`; `tests/test_services/conftest.py:65` (mock); `.claude/skills/addarr-testing/references/fixtures.md:189`
        - **Watch out:** `tests/test_architecture/test_skills.py` checks that names in skills exist: update `fixtures.md` with the mock. Use the `arr-api-contract-checker` agent only if a request changes (it does not: nothing is added)
    - **Scope:** 1 method, its 3 tests, the mock, one doc line
    - **Touches:** `src/api/lidarr.py`, `tests/test_api/test_lidarr.py`, `tests/test_services/conftest.py`, `.claude/skills/addarr-testing/references/fixtures.md`
    - **Action items:**
        - [RED] Grep for `get_metadata_profiles`: definition, tests, the mock and the fixtures doc only
        - [GREEN] Delete the method, its tests, the mock and the doc line
    - **Success:** `scripts/test_runner.py api --coverage` and `services --coverage` pass

- [ ] **1.5** Delete `log_exception` in `src/utils/logger.py`
    - **Context:**
        - **Why:** F260: no caller
        - **Architecture:** none
        - **Key refs:** `src/utils/logger.py:160`; `tests/test_utils/test_logger.py:14` (import), `:263-280`
        - **Watch out:** Drop `Optional` or other imports only if now unused
    - **Scope:** 1 function, 2 tests, import
    - **Touches:** `src/utils/logger.py`, `tests/test_utils/test_logger.py`
    - **Action items:**
        - [RED] Grep `log_exception` in `src/`, `tests/`, `scripts/`
        - [GREEN] Delete the function, the test class and the import
    - **Success:** `scripts/test_runner.py utils --coverage` passes, flake8 clean

- [ ] **1.6** Delete `show_token_help` in `src/utils/splash.py`
    - **Context:**
        - **Why:** F260: no caller
        - **Architecture:** none
        - **Key refs:** `src/utils/splash.py:118`; `tests/test_utils/test_splash.py:11` (import), `:239-280`
        - **Watch out:** Check which imports only that function used
    - **Scope:** 1 function, its tests, import
    - **Touches:** `src/utils/splash.py`, `tests/test_utils/test_splash.py`
    - **Action items:**
        - [RED] Grep `show_token_help` in `src/`, `tests/`, `scripts/`
        - [GREEN] Delete the function, the test class and the import
    - **Success:** `scripts/test_runner.py utils --coverage` passes, flake8 clean

- [ ] **1.7** Delete the unread `"message"` key in `src/services/media.py`
    - **Context:**
        - **Why:** F260: `add_movie`, `add_series` and the third add method return `"message": profile_text` and nothing reads it
        - **Architecture:** The handler builds its own text from `profiles`
        - **Key refs:** `src/services/media.py:265-275`, `:333-344`, `:403-413`; `tests/test_services/`
        - **Watch out:** `profile_text` and its loop feed only that key: delete both. Check that no test asserts `result["message"]`. Keep every other key of the dict
    - **Scope:** 3 dict keys and 3 loops
    - **Touches:** `src/services/media.py`, `tests/test_services/test_media_service.py` (if it asserts the key)
    - **Action items:**
        - [RED] Grep `src/` for readers of `["message"]` / `.get("message")` on these results: none
        - [GREEN] Delete the 3 keys and 3 `profile_text` blocks, fix tests that assert them
    - **Success:** `grep -n '"message": profile_text' src/services/media.py` returns nothing; `scripts/test_runner.py services --coverage` passes

- [ ] **1.8** Delete the dead constants in `src/bot/states.py`
    - **Context:**
        - **Why:** F260: `SEARCHING`, `SELECTING`, `QUALITY_SELECT`, `SEASON_SELECT`, `ALBUM_SELECT`, `PASSWORD` and `END` are unread; the media states live in `src/bot/handlers/media/dispatch.py`
        - **Architecture:** `states.py` stays: `SETTINGS_*`, `WEBHOOK_*` and `BAZARR_SEARCH` are live. The issue's item "`states.py` is gone" is replaced (maintainer decision; state it in the PR body)
        - **Key refs:** `src/bot/states.py`; `tests/test_bot/test_states.py` (`TestMediaStates`, `TestAuthStates`, `TestGeneralStates`); `tests/test_architecture/test_conventions.py:355-385` (`MEDIA_STATE_NAMES`, `test_media_state_constants_in_sync`); CLAUDE.md lines 106, 141, 151
        - **Watch out:** `test_media_state_constants_in_sync` goes because one of its two sides is deleted. CLAUDE.md names it and `tests/test_architecture/test_repo_docs.py` checks the names, so remove it from CLAUDE.md in the same commit. Keep `TestRemovedStates` and the settings tests. Also update the skill lines that call `states.py` the home of all states only if they now mislead (`addarr-handlers` `SKILL.md:15`, `wiring.md:5`: they say "new states", still true)
    - **Scope:** 7 constants, 3 test classes, 1 architecture test, 3 CLAUDE.md lines
    - **Touches:** `src/bot/states.py`, `tests/test_bot/test_states.py`, `tests/test_architecture/test_conventions.py`, `CLAUDE.md`
    - **Action items:**
        - [RED] Grep `States.<NAME>` for the 7 names in `src/`, `tests/`: only `states.py`, `test_states.py` and `test_conventions.py`
        - [GREEN] Delete the constants and the matching tests
        - [GREEN] Delete `MEDIA_STATE_NAMES` and `test_media_state_constants_in_sync`
        - [GREEN] Edit CLAUDE.md: remove the sync-test bullet; state that media states live in `dispatch.py` and `states.py` holds the settings, webhook and Bazarr states
    - **Success:** `pytest tests/test_bot tests/test_architecture` passes (docs drift test included)

- [ ] **1.9** Verify the whole change
    - **Context:**
        - **Why:** Confirm the acceptance criteria and that nothing else broke
        - **Architecture:** Preflight from `.claude/skills/addarr-workflow/references/preflight.md`, every command through the suite lock
        - **Key refs:** the Verification section of `plan.md`
        - **Watch out:** The `def is_authenticated` grep still lists `AuthHandler.is_authenticated`; that is the live method, not the helper
    - **Scope:** Greps and the preflight
    - **Touches:** none
    - **Action items:**
        - [RED] Run the acceptance greps from `plan.md`
        - [GREEN] Run the preflight (flake8, mypy, translations, unit tests with the 100% gate, integration, architecture)
        - [GREEN] Run `graphify update .`
    - **Success:** all greps empty (bar the note above), preflight passes, coverage 100%
