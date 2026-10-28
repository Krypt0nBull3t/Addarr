---
title: "Fix /help command list, post-auth menu and History labels"
labels: [bug, ux, i18n, priority:medium, agent-ready]
slice: 27
findings: [F120, F093, F121, F122]
---

## Bug

- **F120** /help omits 7 registered commands: `/preferences`, `/webhooks`, `/upcoming`, `/missing`, `/queue`, `/history`, `/downloads`. It lists `/library`, which has no handler.
- **F093** After a correct password the bot sends the text `/start`. Bots do not receive their own messages, so no menu opens.
- **F121** The /status and Details texts use `*bold*` (`*System Status*`, `*Health Monitor*`, `*Services*`, `*Service Details*`, `*Media Services*`, `*Download Clients*`) but are sent without `parse_mode`, so the asterisks show. Disk Space already passes `parse_mode`.
- **F122** The History Refresh button is labelled "Search". The active History filter is marked with a bullet, where other screens use a check mark.

## Steps to reproduce

1. Enable Radarr and SABnzbd. Send /help. `/preferences`, `/webhooks`, `/upcoming`, `/missing`, `/queue`, `/history` and `/downloads` are missing, and `/library` is listed. Send /library: nothing happens. (F120)
2. Send /auth and the correct password. The bot posts "/start" as text and no menu opens. (F093)
3. Send /status. The title shows as `*System Status*`. Tap Details: `*Service Details*` shows with asterisks. (F121)
4. Send /history. The refresh button reads "Search". The active filter tab starts with a bullet. (F122)

## Expected behavior

- /help lists every command the bot registers for the user, gated the same way, and no command without a handler.
- After a correct password the main menu opens.
- The disk space title is bold, with no asterisks.
- The History refresh button says Refresh. The active filter has a check mark, as on the other screens.

## Fix

- [ ] **F120** Add the 7 commands to the help text, gated as `build_authenticated_commands()` gates them (`src/bot/commands.py:57-81`). Remove `/library` from `HelpBasicCommands` in all 10 files, or add a `/library` handler (`translations/*.yml` `HelpBasicCommands`, en-us `:140-158`; `src/bot/commands.py:31`; `src/bot/handlers/help.py:38-57`)
- [ ] **F093** Send the main menu with `get_main_menu_keyboard()` instead of the text `/start` (`src/bot/handlers/auth.py:221-225`)
- [ ] **F121** Send the status and details texts with `parse_mode="Markdown"` and escape service error text, or switch these texts to HTML (`src/bot/handlers/system.py:84-91`, `:130-134`, `:150-153`; texts built at `:202-237`)
- [ ] **F122** Relabel the History refresh button as Refresh, like the other screens. Mark the active filter with the check mark (`✓`) used elsewhere (`src/bot/keyboards.py:1120`, `:1167`, `:1184`)

## Acceptance criteria

- [ ] F120: `tests/test_handlers/test_help_handler.py` loads the shipped en-us file, enables all services and asserts the help text has each of the 7 commands and no `/library`. Fails before the fix. A second case with all *arr apps and download clients off asserts `/upcoming`, `/missing`, `/queue`, `/history` and `/downloads` are absent.
- [ ] F093: `tests/test_handlers/test_auth_handler.py` asserts that after a correct password the bot sends a message whose `reply_markup` is the main menu keyboard, and never sends the text "/start". Fails before the fix.
- [ ] F121: tests in `tests/test_handlers/test_system_handler.py` assert `parse_mode` on the `show_status`, refresh and details `edit_text`/`reply_text` calls, and a details text with `_` or `*` in an error message does not break parsing. Fails before the fix.
- [ ] F122: `tests/test_bot/test_keyboards.py` asserts the History refresh button is not built from the `Search` key, and the active filter tab starts with the check mark. Fails before the fix.
- [ ] `HelpBasicCommands` changes follow the `i18n-key` skill (template plus all 9 locales).
- [ ] `pytest`, `flake8`, `mypy src/` and `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` pass.

## Notes

- Source: audit 2026-10-28, docs/issues/audit-2026-10-28/FINDINGS.md (F-ids F120, F093, F121, F122).
- Priority: max P 16 (F120), sum P 51, `priority:medium`.
- F121: Disk Space (`src/bot/handlers/system.py:170-174`) already passes `parse_mode="Markdown"` since 7f189b1. The status and details messages do not. Service error text can contain `_` or `*`, so escape it or use HTML.
- F120: removing `/library` is the smaller change. A `/library` handler would be new work.
- F120 edits `Help*` keys that slice 29 (F210) translates. Coordinate the two.
- Related open issues: none.
