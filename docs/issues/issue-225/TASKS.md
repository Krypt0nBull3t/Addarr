# Issue 225: Clean up tests: TASKS

Plan: `docs/issues/issue-225/plan.md`. Issue: https://github.com/Krypt0nBull3t/Addarr/issues/225.
Branch: `refactor/225-clean-up-tests-logs-fixtures-duplicates`.

Run every pytest, flake8 and mypy command with `.venv/bin/python` through the suite lock.
`tests/test_models/test_media.py` and `test_notification.py` stay: #226 deletes them with the models.

### Phase 1: Test cleanup (5 tasks)

**Goal:** Tests write only to temporary paths, no dead fixture, file or duplicate test is left, and `MockConfig` matches `config_example.yaml`. Coverage stays 100%.

**Phase Context:**

- Why NOT delete `tests/test_models/test_media.py` and `test_notification.py`: #226 deletes them together with `src/models/media.py` and `src/models/notification.py`. The PR body says the F251 item for those two files is met by the #226 PR.
- Line numbers in the issue are stale for `test_media_handler.py`: tasks name the tests instead.

- [x] **1.1** F253: `MockConfig` transmission block matches `config_example.yaml`
    - **Context:**
        - **Why:** `MockConfig` has `transmission.port` and `ssl`, which `config_example.yaml` lacks, so the default-port path in `TransmissionClient` is never tested.
        - **Architecture:** `MOCK_CONFIG_DATA` in `tests/conftest.py` is the mock config data. `src/api/transmission.py` lines 21-28 read `port` (default 9091) and `ssl` (default False) with `config.get`.
        - **Key refs:** `tests/conftest.py:66-70`, `tests/test_api/test_transmission_api.py` (`TestTransmissionInit`, `test_init_ssl_url` reads `_config["transmission"]["ssl"]`), `config_example.yaml:114-120`, `src/definitions.py` (`CONFIG_EXAMPLE_PATH`).
        - **Watch out:** `test_init_ssl_url` reads the `ssl` key, so it raises `KeyError` once the key is gone: use `patch.dict`. Build the new client with `patch("src.api.transmission.config", MockConfig({...}))`: `MockConfig(data)` deep-copies `data`.
    - **Scope:** Remove two keys, fix one test, add two tests.
    - **Touches:** `tests/conftest.py`, `tests/test_api/test_transmission_api.py`, `tests/test_config/test_mock_config_parity.py` (new)
    - **Action items:**
        - [RED] Write `test_mock_transmission_keys_match_config_example` (keys of `MOCK_CONFIG_DATA["transmission"]` equal keys of the `config_example.yaml` block); run it and see it fail on `port`, `ssl`
        - [RED] Write `test_init_default_port_from_config_example`: build `TransmissionClient` from the `config_example.yaml` block, assert no `port` and no `ssl` in it, assert `rpc_url == "http://localhost:9091/transmission/rpc"`
        - [GREEN] Remove `port` and `ssl` from `MOCK_CONFIG_DATA["transmission"]`
        - [GREEN] Rewrite `test_init_ssl_url` with `patch.dict(_mock_config._config["transmission"], {"ssl": True})`
    - **Success:** `tests/test_config/test_mock_config_parity.py` and `tests/test_api/test_transmission_api.py` pass, `scripts/test_runner.py api --coverage` and `config --coverage` pass, flake8 clean.
    - **Completed:** 2026-11-05
    - **Learnings:**
        - `patch.dict` on `_mock_config._config["transmission"]` adds and removes a key, so a test can set `ssl` without the key existing in `MOCK_CONFIG_DATA`.
        - The default-port test passes before the `MockConfig` edit, because it builds the client from the `config_example.yaml` block, not from `MockConfig`. Only the parity test is red first.
        - The venv must be reinstalled after switching to the branch: `requirements.txt` there pins `python-telegram-bot[job-queue]==22.8`. Without `apscheduler` every `tests/integration` test errors with `PTBUserWarning: No JobQueue set up`.
    - **Key Changes:**
        - `tests/conftest.py`: removed `port` and `ssl` from `MOCK_CONFIG_DATA["transmission"]`.
        - `tests/test_api/test_transmission_api.py`: new `test_init_default_port_from_config_example`; `test_init_ssl_url` uses `patch.dict`.
        - `tests/test_config/test_mock_config_parity.py` (new): `test_mock_transmission_keys_match_config_example`.
    - **Notes:** The parity test covers only the `transmission` block, as the issue asks.

- [x] **1.2** F250: redirect test log files to a temporary directory
    - **Context:**
        - **Why:** Tests write the real `logs/addarr.log` and `logs/error.log`. `LOG_PATH` and `ERROR_LOG_PATH` are not redirected.
        - **Architecture:** `src/utils/logger.py:18` does `from ..definitions import CONFIG_PATH, LOG_PATH, ERROR_LOG_PATH` and binds the values at import. Setting the attributes on `src.definitions` before `src.utils.logger` is first imported redirects every later logger. `tests/conftest.py` already injects fake `src` modules before any `src` import: add the redirect right after that block (after the `sys.modules["src.config"]` lines).
        - **Key refs:** `src/definitions.py:25-26`, `src/utils/logger.py:131-135`, `src/setup/wizard.py:38,133` (uses `LOG_PATH` only for its dirname; `tests/test_setup/test_wizard.py:454` patches it), `tests/test_utils/test_logger.py` (patches `src.utils.logger.LOG_PATH` per test).
        - **Watch out:** Importing `src.definitions` does not trigger `Config()` (it needs only `yaml`). Clean the tmp dir at exit with `atexit`. Add one comment saying why: logger binds the path at import.
    - **Scope:** Root conftest redirect plus one regression test.
    - **Touches:** `tests/conftest.py`, `tests/test_utils/test_logger.py`
    - **Action items:**
        - [RED] Write `test_log_paths_are_outside_repo_logs_dir`: `LOG_PATH` and `ERROR_LOG_PATH` are equal in `src.definitions` and `src.utils.logger`, and neither starts with `os.path.join(ROOT_DIR, "logs")`; see it fail
        - [GREEN] In `tests/conftest.py` create the tmp dir with `tempfile.mkdtemp`, register `atexit.register(shutil.rmtree, ...)`, set `src.definitions.LOG_PATH` and `ERROR_LOG_PATH` to files in it
        - Verify the acceptance criterion: delete `logs/addarr.log` and `logs/error.log` if they exist, run the unit suite, confirm neither file exists
    - **Success:** the regression test passes, `scripts/test_runner.py utils --coverage` and `setup --coverage` pass, no `logs/addarr.log` or `logs/error.log` after a run.
    - **Completed:** 2026-11-05
    - **Learnings:**
        - `logs/interactions.log` is built from `os.path.dirname(LOG_PATH)` in `src/utils/logger.py`, so one redirect covers all three log files.
        - Acceptance check: after deleting `logs/addarr.log` and `logs/error.log`, a full `pytest` run (2481 passed) recreated neither, and `logs/interactions.log` kept its old size and mtime.
    - **Key Changes:**
        - `tests/conftest.py`: `tempfile.mkdtemp` log dir, `atexit` cleanup, `src.definitions.LOG_PATH` and `ERROR_LOG_PATH` set right after the `sys.modules` injection (needs `# noqa: E402` on the import).
        - `tests/test_utils/test_logger.py`: `test_log_paths_are_outside_repo_logs_dir`.
    - **Notes:** `tests/test_utils/test_logger.py` still patches `src.utils.logger.LOG_PATH` per test; that is unchanged.

- [x] **1.3** F251: delete the dead files
    - **Context:**
        - **Why:** `tests/fixtures/config_fixtures.py`, `tests/integration/api_mocks.py` and its test `tests/integration/test_api_mocks.py` are used by nothing else.
        - **Architecture:** Plain deletion. `tests/test_architecture/test_skills.py` and `test_repo_docs.py` fail when a skill or CLAUDE.md names a path that no longer exists, so check references first.
        - **Key refs:** Grep for `config_fixtures`, `api_mocks` in `tests/`, `.claude/`, `docs/` (not `docs/issues/audit-*`), `CLAUDE.md`, `.github/`.
        - **Watch out:** Keep `tests/fixtures/__init__.py`, `bazarr_data.py`, `sample_data.py` and `tests/integration/fixtures.py`. Do not touch `tests/test_models/test_media.py` and `test_notification.py`.
    - **Scope:** Three file deletions and any reference fix.
    - **Touches:** `tests/fixtures/config_fixtures.py`, `tests/integration/api_mocks.py`, `tests/integration/test_api_mocks.py`
    - **Action items:**
        - [RED] Run the grep for references and the integration and architecture tests first (baseline green)
        - [GREEN] `git rm` the three files and fix any reference found
    - **Success:** `tests/integration` and `tests/test_architecture` pass, the three files are gone.
    - **Completed:** 2026-11-05
    - **Learnings:**
        - The `Grep` tool was not available in this session; `git grep` found the references.
        - `tests/test_architecture` does not catch stale file names in `.claude/skills/addarr-testing/references/`, so those two files were fixed by hand.
        - Old issue docs (`docs/issues/issue-136`, `docs/issues/feature/test-suite`) name the deleted files as history. They stay as they are.
    - **Key Changes:**
        - Deleted `tests/fixtures/config_fixtures.py`, `tests/integration/api_mocks.py`, `tests/integration/test_api_mocks.py`.
        - `.claude/skills/addarr-testing/references/fixtures.md`: removed the Config Fixtures section and the `api_mocks.py` paragraph.
        - `.claude/skills/addarr-testing/references/patterns.md`: removed the `api_mocks.py` table row.
    - **Notes:** Task 1.4 must also update the skill docs for the fixtures and constants it deletes (`SKILL.md` and `references/fixtures.md` name them).

- [x] **1.4** F251: delete dead fixtures and unused sample data
    - **Context:**
        - **Why:** An AST scan of `tests/` found fixtures nobody requests and constants nobody imports.
        - **Architecture:** Dead fixtures: `radarr_url`, `sonarr_url`, `lidarr_url`, `bazarr_url`, `transmission_url` (`tests/test_api/conftest.py`); `mock_notification_service`, `transmission_handler`, `auth_handler`, `help_handler` (`tests/test_handlers/conftest.py`, two import classes that do not exist); `bazarr_service` (`tests/test_services/test_bazarr_service.py`); `filtered_service` (`tests/test_services/test_webhook_service.py`). Unused constants in `tests/fixtures/sample_data.py`: `RADARR_ROOT_FOLDERS`, `SONARR_SEASONS`, `SABNZBD_QUEUE`, `SABNZBD_VERSION`, `SABNZBD_HISTORY`, plus any constant only the files deleted in 1.3 used (the audit counts 6).
        - **Key refs:** scan script at `/tmp/claude-1000/-home-mark--ao-data-worktrees-addarr-addarr-8/5946a16b-d184-5e81-a778-65b8fd90d5bd/scratchpad/deadfix.py` (run with `.venv/bin/python -I <script> tests`); autouse fixtures (`reset_singletons`, `mock_translation`, `cleanup_sessions`, and similar) are expected false positives.
        - **Watch out:** After deleting, remove imports only these fixtures used (flake8 F401). `transmission_client` and `bazarr_client` fixtures stay.
    - **Scope:** Delete fixtures and constants, fix imports.
    - **Touches:** `tests/test_api/conftest.py`, `tests/test_handlers/conftest.py`, `tests/test_services/test_bazarr_service.py`, `tests/test_services/test_webhook_service.py`, `tests/fixtures/sample_data.py`
    - **Action items:**
        - [RED] Re-run the scan after 1.3 and list what is dead (the baseline)
        - [GREEN] Delete each dead fixture and constant, then its unused imports
        - Re-run the scan: no non-autouse unused fixture and no unused constant remains
    - **Success:** `grep -rn "def radarr_url\|def filtered_service" tests` returns nothing, flake8 clean, unit suite passes at 100% coverage.
    - **Completed:** 2026-11-05
    - **Learnings:**
        - The scan found 5 unused `sample_data.py` constants, not the 6 the audit counts, and none was left after the 1.3 deletions. Every remaining constant is used.
        - The skill docs taught the deleted `radarr_url` fixture in many examples (`patterns.md`, `anti-patterns.md`, `fixtures.md`), although no test used it. The examples now use the literal URL `http://localhost:7878`.
        - A merge can revive a fixture. Re-run the scan after every merge of `origin/development`, and check each deleted name against the merged tree.
        - The AST scan reports autouse fixtures and fixtures used via `usefixtures` as unused. Those are false positives.
    - **Key Changes:**
        - Deleted the 5 `*_url` fixtures (`tests/test_api/conftest.py`), `mock_notification_service`, `transmission_handler`, `auth_handler`, `help_handler` (`tests/test_handlers/conftest.py`), `filtered_service`. `bazarr_service` was deleted, then restored by the merge of `origin/development`, because two new `TestBazarrServiceClose` tests use it.
        - Deleted `RADARR_ROOT_FOLDERS`, `SONARR_SEASONS`, `SABNZBD_QUEUE`, `SABNZBD_VERSION`, `SABNZBD_HISTORY` from `tests/fixtures/sample_data.py`.
        - Updated `.claude/skills/addarr-testing/SKILL.md`, `references/fixtures.md`, `references/patterns.md`, `references/anti-patterns.md` and `.claude/skills/task-writer/SKILL.md` (it named `bazarr_url`).
    - **Notes:** Full suite after this task: 2478 passed, coverage 100%.

- [x] **1.5** F252: delete duplicate tests
    - **Context:**
        - **Why:** Some tests copy others, so each fix to a behavior needs edits in two places.
        - **Architecture:** `tests/test_api/test_base.py`: `test_all_retries_exhausted_connection_error` and `test_no_retry_on_generic_exception` copy `test_make_request_connection_error` and `test_make_request_unexpected_exception`. `test_request_generic_exception` repeats in `test_radarr.py`, `test_sonarr.py`, `test_lidarr.py`. `tests/test_handlers/test_media_handler.py` copies `tests/test_handlers/test_media_formatters.py`: `test_send_response_with_photo`, `_without_photo`, `_fallback_on_error`; `test_build_result_caption_with_index_total`, `_album`, `_song`; also `_album_with_overview` and `_album_truncates_long_overview` when coverage of `formatters.py` allows.
        - **Key refs:** the audit line numbers for `test_media_handler.py` are stale; find tests by name. The issue lists `test_base.py:590` and `:651`, `test_radarr.py:71`, `test_sonarr.py:69`, `test_lidarr.py:85` (still valid).
        - **Watch out:** Read each copy next to its original first: if a copy asserts something the original does not, move that assertion into the original. The two album overview tests have no exact twin: delete them, run coverage for `src.bot.handlers.media.formatters`, and move them into `test_media_formatters.py` (call `build_result_caption(result)` without the `media_handler` fixture) only if a branch is lost. Coverage of `src/api/base.py` must also stay 100%.
    - **Scope:** Delete about 13 tests, move at most 2.
    - **Touches:** `tests/test_api/test_base.py`, `tests/test_api/test_radarr.py`, `tests/test_api/test_sonarr.py`, `tests/test_api/test_lidarr.py`, `tests/test_handlers/test_media_handler.py`, `tests/test_handlers/test_media_formatters.py`
    - **Action items:**
        - [RED] Compare each copy with its original and note any assertion to keep
        - [GREEN] Delete the duplicates, move kept assertions
        - [GREEN] Run `pytest --cov=src.api.base --cov=src.bot.handlers.media.formatters --cov-report=term-missing` on the touched files; move the album overview tests only if a line is lost
    - **Success:** the listed duplicates are gone, `scripts/test_runner.py api --coverage` and `handlers --coverage` pass, then the full suite with the 100% gate (preflight) passes.
    - **Completed:** 2026-11-05
    - **Learnings:**
        - Deleting `test_build_result_caption_album_truncates_long_overview` from `test_media_handler.py` dropped `src/bot/handlers/media/formatters.py` line 92 (album overview over 300 characters). No other test reached it. The test moved to `test_media_formatters.py` as `test_build_result_caption_album_long_overview_truncated`.
        - `test_build_result_caption_album_with_overview` was deleted: another test covers that branch.
        - `_request` returning `None` on a generic exception had a test only in the three client files. It now lives once in `test_base.py` as `test_request_returns_none_on_unexpected_exception`.
        - A small AST script (delete a top-level test by name, with decorators) avoided line-number errors when deleting 8 tests from one 2700-line file.
    - **Key Changes:**
        - `tests/test_api/test_base.py`: deleted `test_all_retries_exhausted_connection_error` and `test_no_retry_on_generic_exception`; added `test_request_returns_none_on_unexpected_exception`.
        - `tests/test_api/test_radarr.py`, `test_sonarr.py`: deleted the one-test `Test*MakeRequest` class and its header. `test_lidarr.py`: deleted `test_request_generic_exception`.
        - `tests/test_handlers/test_media_handler.py`: deleted `test_send_response_*` (3), `test_build_result_caption_with_index_total`, `_album`, `_song`, `_album_with_overview`, `_album_truncates_long_overview`, the `_send_response` section header and the unused `send_response` import.
        - `tests/test_handlers/test_media_formatters.py`: added `test_build_result_caption_album_long_overview_truncated`.
    - **Notes:** Net change in the API suite: 323 to 319 tests. The full suite with the gate runs in the preflight.
