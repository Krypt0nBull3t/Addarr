---
title: "Make unit tests assert arguments and content so they can fail"
labels: [tech-debt, python, priority:medium]
slice: 21
findings: [F242, F244, F240, F241, F243, F245, F246]
---

## Problem

Many unit tests check that a call happened, not what it carried. They pass when the code sends the wrong body, id or text.

- **API tests** never assert POST bodies or params: add bodies (`tvdbId`/`tmdbId`, `qualityProfileId`, `rootFolderPath`, `seasons`), command names, Transmission alt-speed and the session-id header, SABnzbd query params. The `seasonFolder` test sets the default value, so it proves nothing.
- **Media handler tests** do not check the dropped `reply_markup`, season `seasons_data`, album args, `edit_reply_markup` or the "no edit" case.
- **Handler tests** check calls, not content: delete mocks always return True (a wrong id passes), add args, the wrong-password reply, webhooks save, the alt-speed toggle, filter output, library sort, page args, toasts and refresh, the SAB settings guard. The delete `reply_markup` check is always true.
- **Service tests** do not pin: webhook formatter `title=` (translation mocked), the health alert `await`, request headers and ssl, calendar dates, history sort, music type order, Transmission paused and speed, the exact rate-limit `retry_after`, the webhook port, the health task lifecycle, Sonarr webhook quality.
- **Bot, setup and utils tests**: keyboard toggle texts are unasserted, 17 validation tests have no assert, wizard output and `save_config` args are unchecked.
- **Translation mock**: the autouse mock returns the key or default, so a typo in a key passes. No test checks that every literal `get_text` key exists in en-us.
- **Fixtures** use shapes the APIs never send: Sonarr `ratings.tmdb` and studio; Lidarr `tracks` and `statistics.yearStart`; SABnzbd `size` as the remaining size.

## Expected behavior

Each test fails when the code sends a wrong value. Fixtures match the Servarr, Transmission and SABnzbd API shapes.

## Fix

- [ ] **F242** Capture request JSON and params and assert the keys (`tests/test_api/test_sonarr.py:373`, `:537`, `:851`; `tests/test_api/test_radarr.py:373`, `:786`; `tests/test_api/test_lidarr.py:225`; `tests/test_api/test_transmission_api.py:85`, `:140-153`; `tests/test_services/test_sabnzbd_service.py:23`)
- [ ] **F244** Use `assert_awaited_once_with(...)` with exact values (`tests/test_handlers/test_media_handler.py:919`, `:952`, `:979`, `:1211`, `:2435`, `:2471`, `:2593`, `:2622`, `:2631`, `:2777`; `tests/test_handlers/test_media_formatters.py:440`)
- [ ] **F240** Assert call args and reply content (`tests/test_handlers/test_delete_handler.py:28`, `:276`; `test_auth_handler.py:617`; `test_webhooks_handler.py:170-273`; `test_settings_handler.py:501`, `:687-718`; `test_transmission_handler.py:125`; `test_missing_handler.py:121-152`, `:337`, `:358`; `test_queue_handler.py:131-179`; `test_library_handler.py:220`; `test_history_handler.py:195`; `test_downloads_handler.py:358-447`, `:534`; `tests/integration/test_auth_flow.py:35`)
- [ ] **F241** Use `assert_awaited_*`, a mocked clock and exact values (`tests/test_services/test_webhook_formatter.py:131`; `test_health_service.py:568`, `:863`, `:891`, `:1086`, `:1231`; `test_media_service.py:1333`, `:1525`, `:2313`; `test_transmission_service.py:262`; `test_rate_limit_service.py:75`; `test_webhook_service.py:413`; `tests/test_models/test_webhook_models.py:182`, `:196`)
- [ ] **F243** Assert texts and output; use `capsys` for wizard output (`tests/test_bot/test_keyboards.py:357-522`; `tests/test_utils/test_validation.py:52`; `tests/test_setup/test_wizard.py:136`, `:160`)
- [ ] **F245** Add an AST test over all `get_text("...")` literals in `src/` that checks each key exists in en-us (`tests/conftest.py:303`, `tests/test_services/test_translation_service.py:253`)
- [ ] **F246** Use spec shapes in fixtures (`tests/fixtures/sample_data.py:61`, `:78`, `:179`; `tests/test_services/test_media_service.py:67`; `tests/test_services/test_sabnzbd_service.py:284`, `:329`)

## Acceptance criteria

Each improved test must fail on a planted defect:

- [ ] F242: dropping `qualityProfileId` from the Sonarr `add_series` POST body (`src/api/sonarr.py`) makes the add test fail.
- [ ] F244: dropping `reply_markup` from the season keyboard edit in the media handler makes the season selection test fail.
- [ ] F240: passing the wrong id to the service delete call in `src/bot/handlers/delete.py` makes `test_handle_delete_confirm_success` fail.
- [ ] F241: returning the full window instead of the remaining time as `retry_after` in the rate-limit service makes the rate-limit test fail.
- [ ] F243: swapping the on and off toggle texts in `get_transmission_settings_keyboard` makes the keyboard test fail.
- [ ] F245: a typo in one `get_text("...")` key in a handler (for example `BazarrNoResult`) makes the new AST test fail.
- [ ] F246: with spec-shaped fixtures, reading `ratings.tmdb` for Sonarr (`src/services/media.py:147`) makes the rating test fail.
- [ ] `pytest`, `flake8` and `mypy src/` pass.

## Notes

- Source: audit 2026-10-28, docs/issues/audit-2026-10-28/FINDINGS.md (F-ids F242, F244, F240, F241, F243, F245, F246).
- Priority: max P 24, sum P 128 (medium).
- Dependencies: F246 goes with slices 5 (Lidarr), 9 (Radarr/Sonarr) and 12 (download clients), which fix the code that reads these shapes.
