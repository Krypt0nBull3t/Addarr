# Issue 225: Clean up tests (real log writes, dead fixtures, duplicate tests)

Issue: https://github.com/Krypt0nBull3t/Addarr/issues/225 (audit findings F250 to F253).
Branch: `refactor/225-clean-up-tests-logs-fixtures-duplicates`, from `origin/development` (cf51f57).

## Context

Tests only. No `src/` change. No design doc: each finding has one clear fix.

The line numbers in the issue are stale for `tests/test_handlers/test_media_handler.py` (merged fixes moved
code). This plan names tests by name, and the names were checked on this branch.

### Decided by the orchestrator

- `tests/test_models/test_media.py` and `tests/test_models/test_notification.py` stay. Issue #226 (worker addarr-7)
  deletes them together with `src/models/media.py` and `src/models/notification.py`. The PR body says the F251
  acceptance item for those two files is met by the #226 PR.
- Unused fixtures and constants found by the scan below are part of F251.

### Scan results (AST scan of `tests/`, fixtures not used as a parameter or in `usefixtures`)

Dead fixtures:
- `tests/test_api/conftest.py`: `radarr_url`, `sonarr_url`, `lidarr_url`, `bazarr_url`, `transmission_url`
- `tests/test_handlers/conftest.py`: `mock_notification_service`, `transmission_handler`, `auth_handler`, `help_handler`
- `tests/test_services/test_bazarr_service.py`: `bazarr_service` (used again after the merge, kept)
- `tests/test_services/test_webhook_service.py`: `filtered_service`

Unused `tests/fixtures/sample_data.py` constants: `RADARR_ROOT_FOLDERS`, `SONARR_SEASONS`, `SABNZBD_QUEUE`,
`SABNZBD_VERSION`, `SABNZBD_HISTORY`. The audit counts 6; Task 4 re-runs the scan after the file deletions and
removes any constant that only the deleted files used.

Duplicate tests in `tests/test_handlers/test_media_handler.py` (the twin is in `tests/test_handlers/test_media_formatters.py`):

| Handler-file test | Twin |
|-|-|
| `test_send_response_with_photo`, `_without_photo`, `_fallback_on_error` | same names in the formatters file |
| `test_build_result_caption_with_index_total` | `test_build_result_caption_with_index` |
| `test_build_result_caption_album`, `_song` | same names in the formatters file |
| `test_build_result_caption_album_with_overview`, `_album_truncates_long_overview` | no exact twin: Task 5 checks the formatter coverage and moves them if a branch would be lost |

## Tasks

Run every pytest, flake8 and mypy command through the suite lock. Use `.venv/bin/python`.

### Task 1: F253 `MockConfig` matches `config_example.yaml` (transmission)

Files: `tests/conftest.py` (lines 66-70), `tests/test_api/test_transmission_api.py`, new `tests/test_config/test_mock_config_parity.py`.

1. RED: in `test_mock_config_parity.py` add `test_mock_transmission_keys_match_config_example`. It loads
   `CONFIG_EXAMPLE_PATH` (from `src.definitions`) with `yaml.safe_load` and asserts
   `set(MOCK_CONFIG_DATA["transmission"]) == set(example["transmission"])`. Run it: fails on `port`, `ssl`.
2. In `tests/conftest.py` drop `"port": 9091` and `"ssl": False` from `MOCK_CONFIG_DATA["transmission"]`.
3. In `test_transmission_api.py`, rewrite `test_init_ssl_url` to set `ssl` with
   `patch.dict(_mock_config._config["transmission"], {"ssl": True})` (the key no longer exists, so no read of the original).
4. Add `test_init_default_port_from_config_example` to `TestTransmissionInit`. It builds
   `MockConfig({"transmission": example["transmission"]})` from the `config_example.yaml` block, patches
   `src.api.transmission.config` with it, builds `TransmissionClient()`, and asserts
   `rpc_url == "http://localhost:9091/transmission/rpc"`. It also asserts `port` and `ssl` are not in the block.
5. Run `tests/test_config/test_mock_config_parity.py`, `tests/test_api/test_transmission_api.py` and
   `scripts/test_runner.py api --coverage`. Check other tests that read `transmission.port` or `.ssl`: none found by grep.
6. Commit: `test: match MockConfig transmission block to config_example (#225, task 1)`.

### Task 2: F250 redirect log paths to a tmp dir

Files: `tests/conftest.py` (after the `sys.modules` injection, before any `src.utils` import), `tests/test_utils/test_logger.py`.

1. RED: add `test_log_paths_are_outside_repo_logs_dir` in `tests/test_utils/test_logger.py`. It imports `src.definitions`
   and `src.utils.logger` and asserts that `LOG_PATH` and `ERROR_LOG_PATH` in both modules are equal and do not start
   with `os.path.join(ROOT_DIR, "logs")`. Run it: fails.
2. In `tests/conftest.py`, create `_log_dir = tempfile.mkdtemp(prefix="addarr-test-logs-")`, register
   `atexit.register(shutil.rmtree, _log_dir, ignore_errors=True)`, import `src.definitions as _definitions` and set
   `_definitions.LOG_PATH` and `_definitions.ERROR_LOG_PATH` to files in that dir. This runs before `src.utils.logger`
   imports (`from ..definitions import LOG_PATH, ERROR_LOG_PATH` binds at import). One comment on the why: logger binds the path at import.
3. Check the acceptance criterion: delete `logs/addarr.log` and `logs/error.log` if present, run the full unit suite,
   confirm neither file exists. Also check `src/setup/wizard.py:38` (imports `LOG_PATH` for the dirname only, and its test patches it).
4. Commit: `test: write test logs to a temporary directory (#225, task 2)`.

### Task 3: F251 delete dead files

1. `git rm tests/fixtures/config_fixtures.py tests/integration/api_mocks.py tests/integration/test_api_mocks.py`.
2. Grep for the three names across `tests/`, `.claude/`, `docs/` (excluding `docs/issues/audit-*`), `CLAUDE.md`, `.github/`.
   Fix any reference (the architecture tests `test_skills.py` and `test_repo_docs.py` check paths named in skills and CLAUDE.md).
3. Run `scripts/test_runner.py all`-scoped checks for `tests/integration` and `tests/test_architecture`.
4. Commit: `test: delete unused config fixtures and API mock helpers (#225, task 3)`.

### Task 4: F251 delete dead fixtures and constants

1. `tests/test_api/conftest.py`: delete the five `*_url` fixtures.
2. `tests/test_handlers/conftest.py`: delete `mock_notification_service`, `transmission_handler`, `auth_handler`,
   `help_handler`, and any import or helper only they used (two of them import classes that do not exist).
3. Delete `filtered_service` (`test_webhook_service.py`), with unused imports. `bazarr_service` was dead too, but the merge of `origin/development` brought two tests that use it, so it stays.
4. Delete the unused `sample_data.py` constants. Re-run the scan script after Tasks 3 and 4; the scan must report no
   unused fixture (autouse fixtures are expected false positives) and no unused constant.
5. Check: `grep -rn "def radarr_url\|def filtered_service" tests` returns nothing. `flake8` clean (unused imports).
6. Run the full unit suite; coverage stays 100%.
7. Commit: `test: delete dead fixtures and unused sample data (#225, task 4)`.

### Task 5: F252 delete duplicate tests

1. `tests/test_api/test_base.py`: delete `test_all_retries_exhausted_connection_error` and `test_no_retry_on_generic_exception`
   (copies of `test_make_request_connection_error` and `test_make_request_unexpected_exception`). Before deleting, read both
   pairs and confirm each assertion in the copy is in the original; if one is not, move it into the original.
2. Delete `test_request_generic_exception` from `test_radarr.py`, `test_sonarr.py`, `test_lidarr.py` (the generic path is
   covered once in `test_base.py`).
3. In `test_media_handler.py` delete the tests in the table above (send_response x3, `with_index_total`, album, song).
4. Run `pytest --cov=src.bot.handlers.media.formatters --cov-report=term-missing` on `test_media_formatters.py` plus
   `test_media_handler.py` after deleting `album_with_overview` and `album_truncates_long_overview`. If a formatter branch
   is lost, move those two tests into `test_media_formatters.py` (use `build_result_caption(result)` without the
   `media_handler` fixture) instead of deleting them. Check `src/api/base.py` coverage the same way after step 1-2.
5. Run the full unit suite; coverage stays 100%.
6. Commit: `test: delete duplicate API and media formatter tests (#225, task 5)`.

## Verification

Preflight (`addarr-workflow` flow): flake8, `mypy src/`, `--validate-i18n`, unit tests with the 100% coverage gate,
integration tests, architecture tests. Acceptance checks per finding are in Tasks 1 to 4.

Known risk: deleting tests can drop coverage under 100%. Each deletion task runs the coverage gate before its commit.
