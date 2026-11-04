# Issue #226: Delete dead code and its tests

Issue: https://github.com/Krypt0nBull3t/Addarr/issues/226 (audit finding F260).
Branch: `refactor/226-delete-dead-code`, from `development` at cf51f57.

## Context

The audit found code in `src/` with no live reader. #202 (PR #252) has merged, so nothing imports
`is_admin` from `src.definitions` any more. Line numbers in the issue are stale (#198, #200, #202 and
#203 moved them); this plan uses the lines on cf51f57.

## Scope (verified on cf51f57)

| Item | Where | Live callers |
|-|-|-|
| `check_auth`, `get_authorized_chats`, `save_chat_id`, `is_authenticated` | `src/utils/helpers.py:18-51`, `:87-89` | none (`AuthHandler.is_authenticated` in `auth.py` is another method) |
| `load_config`, `get_admins`, `get_allowed_chats`, `is_allowed_chat` | `src/definitions.py:42-65` | none |
| `src/models/media.py`, `src/models/notification.py` | whole files | none (`src/models/webhook.py` stays) |
| `get_metadata_profiles` | `src/api/lidarr.py:209` | none |
| `log_exception` | `src/utils/logger.py:160` | none |
| `show_token_help` | `src/utils/splash.py:118` | none |
| `"message": profile_text` and `profile_text` | `src/services/media.py:275`, `:344`, `:413` (and the loops at :265, :333, :403) | none read `result["message"]` |
| `States.SEARCHING`, `SELECTING`, `QUALITY_SELECT`, `SEASON_SELECT`, `ALBUM_SELECT`, `PASSWORD`, `END` | `src/bot/states.py` | none (media states live in `src/bot/handlers/media/dispatch.py`) |

## Deviation from the issue (approved by the maintainer)

The issue says `src/bot/states.py` must be gone. It is not fully dead: `SETTINGS_*`
(`settings.py`), `WEBHOOK_*` (`webhooks.py`) and `BAZARR_SEARCH` (`bazarr.py`) are in use. Deleting
the file would break those three handlers. So we delete only the 7 dead constants and keep the file.
The PR body states this and replaces the acceptance item "`src/bot/states.py` is gone".

## Design decisions

- No new code. Each task deletes the code, its tests, and anything only it used (imports, fixtures, mocks, doc lines).
- `tests/test_models/test_media.py` and `test_notification.py` are deleted here, in the same commit set as the models. #225 (addarr-8) does not delete them.
- `test_media_state_constants_in_sync` in `tests/test_architecture/test_conventions.py` goes: the media states no longer exist in `States`, so nothing is mirrored.
- `tests/test_bot/test_states.py`: remove only the tests for deleted constants (`TestMediaStates`, `TestAuthStates`, `TestGeneralStates`). Keep the settings tests. `TestRemovedStates` asserts removed names are absent, so it stays valid.
- Keep the `models` test runner domain: `src/models/webhook.py` is still there. Update its description in `scripts/test_runner.py` and CLAUDE.md.
- No behavior changes, so no new tests. Coverage must stay at 100%: deleting a function with its tests leaves no uncovered lines.

## Tasks (one commit each)

1. **helpers.py**: delete the four functions and the imports they alone used (`CHATID_PATH`, `os`, `List` if unused); delete `TestSaveChatId`, `TestCheckAuth`, `TestGetAuthorizedChats`, `TestIsAuthenticated` and their imports in `tests/test_utils/test_helpers.py`.
2. **definitions.py**: delete the four functions and the unused imports (`Path`, `yaml`); delete the tests for them in `tests/test_definitions.py` (`TestLoadConfig`, `TestGetAdmins`, `TestGetAllowedChats`, `TestIsAllowedChat`) and unused imports.
3. **models**: delete `src/models/media.py`, `src/models/notification.py`, `tests/test_models/test_media.py`, `tests/test_models/test_notification.py`; reduce `src/models/__init__.py` to the webhook package docstring (no imports of the deleted modules); fix `tests/test_models/conftest.py` if it names them; update the `models` description in `scripts/test_runner.py` and CLAUDE.md.
4. **lidarr**: delete `get_metadata_profiles` and its tests in `tests/test_api/test_lidarr.py`; remove the mock in `tests/test_services/conftest.py:65` and the line in `.claude/skills/addarr-testing/references/fixtures.md:189`.
5. **logger**: delete `log_exception` and its tests (`tests/test_utils/test_logger.py`) and import.
6. **splash**: delete `show_token_help` and its tests (`tests/test_utils/test_splash.py`) and import.
7. **media service**: delete the three `"message"` keys and the `profile_text` loops that only fed them; fix any test that asserts the key.
8. **states**: delete the 7 dead constants from `src/bot/states.py`; delete the matching tests in `tests/test_bot/test_states.py`; delete `test_media_state_constants_in_sync` and `MEDIA_STATE_NAMES`; update CLAUDE.md lines 106, 141 and 151 (media states live in `src/bot/handlers/media/dispatch.py`; `states.py` holds the settings, webhook and Bazarr states).
9. **Verify**: acceptance greps (below), then the preflight (`flake8`, `mypy src/`, translations, unit tests with the 100% gate, integration, architecture) through the suite lock.

## Verification

- `grep -n "^def " src/definitions.py` returns nothing.
- `src/models/media.py` and `src/models/notification.py` are gone, and so are their tests.
- `grep -rn "def check_auth\|def get_authorized_chats\|def save_chat_id\|def is_authenticated\|def get_metadata_profiles\|def log_exception\|def show_token_help" src` returns only `AuthHandler.is_authenticated` (`src/bot/handlers/auth.py`), which is live and not in scope.
- `grep -n '"message": profile_text' src/services/media.py` returns nothing.
- `grep -n "SEARCHING\|SELECTING\|QUALITY_SELECT\|SEASON_SELECT\|ALBUM_SELECT\|PASSWORD\|END" src/bot/states.py` returns nothing.
- Preflight passes with coverage at 100%.

## Risks

- A hidden reader of a "dead" item (dynamic access, `getattr`, YAML). Mitigation: grep `src/`, `tests/`, `scripts/` for each name before deleting, and run the whole suite.
- `tests/test_models/conftest.py` loads `src.models` through `importlib`; the trimmed `__init__.py` must still import.
