---
title: "Fix i18n code bugs: missing keys, wrong lookups, hard-coded English"
labels: [bug, i18n, python, priority:medium]
slice: 25
findings: [F204, F005, F200, F201, F202, F203, F205]
---

## Bug

Some screens show raw key names, English text or a doubled emoji in every language. The translation validator misses several kinds of errors, so CI does not catch them.

- **F204** `validate_translations` checks only `%{name}` placeholders, so `%(name)s` mismatches pass. It checks emoji only on top-level keys, so nested keys are skipped. It does not check that keys used in code exist. It does not flag values copied from English or duplicate keys (YAML keeps the last one without a warning). It reads `translations/` relative to the cwd.
- **F005** The /delete Cancel buttons use the key `StopDelete`, which exists in no locale. The buttons show the raw key "StopDelete".
- **F200** `addarr.en-us.yml` and the template have two `Settings` keys: a string and a mapping. YAML keeps the mapping. The other 8 locales have only the mapping. So `get_text('Settings')` gets a dict, logs an error and returns the English fallback. The main menu Settings button is English in every locale.
- **F201** `DeletePrompt` and `Canceled` are read at the top level, but the keys live under `messages.`.
- **F202** Labels are hard-coded in English: the add flow, the season and album pickers, the result card, the Transmission menu ("Turtle Mode"), settings ("Default Quality Profile") and the missing and queue filter tabs. Matching translation keys exist but are not used.
- **F203** Code adds an emoji that the translated string already has. For example, the Upcoming menu button shows the calendar emoji twice.
- **F205** In the template, the `History*` values are empty and the `Command*` block is in the file twice.

## Steps to reproduce

1. Send /delete and pick a type. The Cancel button under the list shows the raw key "StopDelete". Pick an item: the confirm view has the same button. (F005)
2. Set the language to de-de and send /start. The Settings button reads "Settings" in English. The log shows "Translation error for key 'Settings'". (F200)
3. Send /delete. The prompt is the code default "Select what you want to delete", not the `messages.DeletePrompt` value, in every language. (F201)
4. Send /start and tap Cancel. The reply is the raw key "Canceled". (F201)
5. Set the language to de-de. Send /series, pick a show and a quality profile. "Please select a quality profile:", "Season 1" and "Confirm Selection" are in English. Send /transmission: "Turtle Mode" is in English. (F202)
6. Send /start. The Upcoming button shows the calendar emoji twice. With an empty calendar, the /upcoming title shows it twice too. An empty /queue shows its title emoji twice. (F203)
7. Change a `%(name)s` placeholder in a locale, or remove the emoji from a nested value. Run `PYTHONIOENCODING=utf-8 python run.py --validate-i18n`: it passes. Run it from another directory: it cannot load the template. (F204)
8. Open `translations/addarr.template.yml`. Lines 319-326 are `""`. Lines 264-280 repeat lines 227-243. (F205)

## Expected behavior

- Every button and message uses a key that exists once in all 10 files, and shows in the user's language.
- No emoji shows twice.
- The validator fails on each defect in F204, from any working directory.
- The template has no empty values and no duplicate block.

## Fix

- [ ] **F204** Add validator checks: `%(name)s` placeholders next to `%{name}`; emoji on nested keys (walk the whole tree); every literal `get_text("...")`/`get_message("...")` key in `src/` exists in the template; values in other locales identical to en-us; duplicate keys. Resolve `translations/` from the repo root, not the cwd (`src/utils/validate_translations.py:107`, `:115`, `:130`)
- [ ] **F005** Use the existing `Cancel` key instead of `StopDelete` (`src/bot/handlers/delete.py:136`, `:194`)
- [ ] **F200** Read `Settings.Menu` in the main menu. Remove the duplicate string `Settings: Settings` from en-us and the template (`src/bot/keyboards.py:63`; `translations/addarr.en-us.yml:9`, `:166`; `translations/addarr.template.yml:13`, `:198`)
- [ ] **F201** Read `DeletePrompt` and `Canceled` with `get_message()` (`src/bot/handlers/delete.py:74`; `src/bot/handlers/start.py:93`, `:115`; `src/bot/handlers/media/handler.py:168`)
- [ ] **F202** Replace the hard-coded English with `get_text` and the existing keys (`src/bot/handlers/media/handler.py:475`, `:545-575`; `src/bot/handlers/media/season_picker.py:104-134`; `src/bot/handlers/media/album_picker.py:73`; `src/bot/handlers/media/formatters.py:121-196`; `src/bot/handlers/transmission.py:67-100`; `src/bot/handlers/settings.py:302`, `:390`, `:604`; `src/bot/keyboards.py:725-728`, `:855-858`)
- [ ] **F203** Remove the code-side emoji where the string already has one (`src/bot/keyboards.py:47`, `:443-500`; `src/bot/handlers/calendar.py:197`; title lines `src/bot/handlers/missing.py:185`, `src/bot/handlers/queue.py:155`, `src/bot/handlers/history.py:157`)
- [ ] **F205** Fill the `History*` values in the template and delete the second `Command*` block (`translations/addarr.template.yml:264-280`, `:319-326`)

## Acceptance criteria

- [ ] F204: `tests/test_utils/test_validate_translations.py` has one test per new check. Each writes a template and a locale with the defect to `tmp_path` and expects exit code 1: a `%(name)s` mismatch, a nested value without the template's emoji, a code key missing from the template, a value equal to en-us, a duplicate key. One more test runs `main()` from another cwd and expects exit code 0 on the shipped files. All fail before the fix.
- [ ] F005: `tests/test_handlers/test_delete_handler.py` asserts both Cancel buttons are built from the `Cancel` key and no button text contains `StopDelete`. Fails before the fix.
- [ ] F200: `tests/test_bot/test_keyboards.py` loads the shipped files (as `test_shipped_files_resolve_keys` in `tests/test_services/test_translation_service.py:253` does) and asserts the de-de Settings button text contains "Einstellungen". Fails before the fix.
- [ ] F201: tests in `test_delete_handler.py`, `test_start_handler.py` and `test_media_handler.py` load the shipped en-us file and assert the replies are the `messages.DeletePrompt` and `messages.Canceled` values. Fail before the fix.
- [ ] F202: for each listed screen, a handler or keyboard test with the shipped de-de file asserts the English literal is gone (for example no "Confirm Selection" in the season keyboard, no "Turtle Mode" in the Transmission status). Fail before the fix.
- [ ] F203: keyboard and handler tests with the shipped en-us file assert each listed button and title text equals its translation value, with no extra emoji in front. Fail before the fix.
- [ ] F205: the template has no `: ""` value and one `CommandStart` key. The F204 duplicate-key check passes on all 10 files.
- [ ] Any added or changed key follows the `i18n-key` skill (template plus all 9 locales).
- [ ] `pytest`, `flake8`, `mypy src/` and `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` pass.

## Notes

- Source: audit 2026-10-28, docs/issues/audit-2026-10-28/FINDINGS.md (F-ids F204, F005, F200, F201, F202, F203, F205).
- Priority: max P 16 (F204), sum P 93, `priority:medium`.
- The new F204 checks fail on F005, F200, F201 and F205. Land them in the same PR.
- The English-copy check reports the ~80 untranslated keys of F210 (slice 29). Land F210 first, or report English copies as warnings until it lands.
- The F204 code-key check is the same check as F245 in slice 21 (AST test over `get_text("...")` literals). Build it once.
- F202 touches the season keyboard that slice 28 (F064) merges into one builder in `keyboards.py`. Do F064 first or in the same PR.
- F005 touches the /delete keyboards that slice 1 (F002) changes.
- Slice 26 (F295) adds the `messages.`/`get_message()` note to the i18n-key skill; its absence caused F201.
- Related open issues: none.
