---
title: "Clean up tests: real log writes, dead fixtures, duplicate tests"
labels: [tech-debt, python, priority:medium, agent-ready]
slice: 30
findings: [F250, F251, F252, F253]
---

## Problem

- **F250** Tests write the real `logs/addarr.log` and `logs/error.log`. `LOG_PATH` is not redirected.
- **F251** Dead fixtures and files: `tests/fixtures/config_fixtures.py`, `tests/integration/api_mocks.py` (and its test), the `*_url` fixtures in `tests/test_api/conftest.py`, handler conftest fixtures (2 of them import classes that do not exist), `bazarr_service`, `filtered_service`, 6 `sample_data` constants and tests for dead models.
- **F252** Duplicate tests: `test_base.py:590` and `:651` copy `:316` and `:331`. The generic-exception test is repeated per client. The media handler tests copy formatter tests.
- **F253** `MockConfig` has `transmission.port` and `ssl`, which `config_example.yaml` lacks. The default-port path is never tested.

## Expected behavior

Tests write only to temporary paths. No dead fixture, file or duplicate test is left. `MockConfig` matches `config_example.yaml`.

## Fix

- [ ] **F250** Point `LOG_PATH` (and `ERROR_LOG_PATH`) to a tmp path before any `src` import (`tests/conftest.py:206`; paths from `src/definitions.py:25-26`)
- [ ] **F251** Delete `tests/fixtures/config_fixtures.py`, `tests/integration/api_mocks.py` and `tests/integration/test_api_mocks.py`, the `*_url` fixtures in `tests/test_api/conftest.py`, the dead fixtures in `tests/test_handlers/conftest.py:55`, `:163`, `:188`, `:211`, `:229`, `bazarr_service` (`tests/test_services/test_bazarr_service.py:30`), `filtered_service` (`tests/test_services/test_webhook_service.py:276`), the 6 unused constants in `tests/fixtures/sample_data.py`, and `tests/test_models/test_media.py` and `test_notification.py`
- [ ] **F252** Delete the duplicates: `tests/test_api/test_base.py:590`, `:651` (copies of `:316`, `:331`); the per-client generic-exception tests (`tests/test_api/test_radarr.py:71`, `test_sonarr.py:69`, `test_lidarr.py:85`); the formatter copies in `tests/test_handlers/test_media_handler.py:1211-1241`, `:1768`, `:2322-2394`
- [ ] **F253** Make the `transmission` block in `MockConfig` match `config_example.yaml`: no `port`, no `ssl` (`tests/conftest.py:66-70`)

## Acceptance criteria

- [ ] F250: delete `logs/addarr.log` and `logs/error.log`, run `pytest`. Neither file exists afterwards.
- [ ] F251: `tests/fixtures/config_fixtures.py`, `tests/integration/api_mocks.py`, `tests/integration/test_api_mocks.py`, `tests/test_models/test_media.py` and `tests/test_models/test_notification.py` are gone. `grep -rn "def radarr_url\|def bazarr_service\|def filtered_service" tests` returns nothing.
- [ ] F252: the listed duplicate tests are gone and coverage stays at 100%.
- [ ] F253: a test in `tests/test_api/test_transmission_api.py` builds `TransmissionClient` from the `config_example.yaml` block (no `port`, no `ssl`) and asserts `rpc_url == "http://localhost:9091/transmission/rpc"`. The `MockConfig` `transmission` keys equal the `config_example.yaml` keys.
- [ ] `pytest` (coverage stays at 100%), `flake8` and `mypy src/` pass.

## Notes

- Source: audit 2026-10-28, docs/issues/audit-2026-10-28/FINDINGS.md (F-ids F250, F251, F252, F253).
- Priority: max P 15 (F250), sum P 45, `priority:medium`.
- F251 deletes the tests for the dead models. Slice 31 (F260) deletes `src/models/media.py` and `src/models/notification.py`. Do both in one PR, or coverage falls below 100% and CI fails.
- Related open issues: none.
