---
title: "Fix stuck spinners and dead ends in Telegram navigation"
labels: [bug, ux, agent-ready, priority:medium]
slice: 22
findings: [F110, F115, F113, F114, F112, F111]
---

## Bug

- Several handlers call `edit_text` before `query.answer()`. On a re-tap, Telegram raises "Message is not modified" and the spinner hangs.
- Filters: `setdefault` keeps an old filter. An empty filtered view drops the filter row, so the only exit is to run the command again. Cutoff then Movies filters the cached cutoff list.
- Help, the library list and the Bazarr wanted lists have no Back button. The `bazarr_menu` handler has no button.
- Cancel on a poster message: `start.py` calls `edit_text` on a photo and gets BadRequest.
- Back from SAB speed or default quality goes to the settings root. Back from Settings ends with "The process has ended" and no keyboard.
- `handle_menu_callback` never calls `query.answer()` on the Movie path.

## Steps to reproduce

1. Open `/queue`, tap a filter tab, tap the same tab again: the spinner hangs. The same happens with the missing and history filters, downloads refresh and tabs, SAB pause twice, and system Details and Disk Space.
2. Open `/missing`, tap Movies, then run `/missing` again: the Movies filter is still active.
3. Pick a filter with no items: the filter row is gone.
4. In `/missing`, tap Cutoff, then Movies: the list shows cutoff movies, not missing movies.
5. Open Help from the menu, the library list or a Bazarr wanted list: there is no Back button.
6. Open a search result with a poster and tap Cancel: BadRequest, the message stays.
7. In `/settings`, open SAB speed or default quality and tap Back: you land on the settings root. Tap Back on Settings: "The process has ended" with no keyboard.
8. From the main menu, tap Movie: the button spinner keeps running.

## Expected behavior

Every tap stops the spinner. Every screen has a way back to its parent. Filters start at "all" and keep their row when empty. Cancel works on photo messages.

## Fix

- [ ] **F110** Call `answer()` first; use `edit_text_ignoring_unmodified` (`src/bot/handlers/queue.py:104`, `missing.py:110`, `history.py:105`, `downloads.py:323`, `settings.py:644`, `system.py:150`, `:170`)
- [ ] **F115** Reset the filter to "all" on entry; keep the filter row on empty views; refetch on movie/series (`src/bot/handlers/queue.py:48`, `:158`; `missing.py:48`, `:98-108`, `:188`; `history.py:160`)
- [ ] **F113** Add Back buttons; give `bazarr_menu` a button (`src/bot/handlers/help.py:73`, `library.py:214`, `bazarr.py:82`, `:190`, `:220`)
- [ ] **F114** Use `formatters.send_response` for Cancel (`src/bot/handlers/start.py:92`)
- [ ] **F112** Use parent callbacks for Back; edit to the main menu before END (`src/bot/handlers/settings.py:115`, `:150`, `:706`)
- [ ] **F111** Call `query.answer()` at the top of `handle_menu_callback` (`src/bot/handlers/media/handler.py:155-190`)

## Acceptance criteria

Each test fails before the fix and passes after:

- [ ] F110: in `tests/test_handlers/test_queue_handler.py`, `test_missing_handler.py`, `test_history_handler.py`, `test_downloads_handler.py`, `test_settings_handler.py` and `test_system_handler.py`, `edit_text` raises `BadRequest("Message is not modified")` and `query.answer()` is still awaited.
- [ ] F115: in `test_missing_handler.py` and `test_queue_handler.py`, a stored `movie` filter is reset to `all` on the command; an empty filtered view still has the filter row; Cutoff then Movies calls `get_missing_media` again. In `test_history_handler.py`, an empty filtered view keeps the filter row.
- [ ] F113: the Help callback reply, the library list keyboard and both Bazarr wanted replies contain a Back button; a keyboard has a `bazarr_menu` button (`test_help_handler.py`, `test_library_handler.py`, `test_bazarr_handler.py`).
- [ ] F114: in `tests/test_handlers/test_start_handler.py`, Cancel on a message with a photo edits the caption, not the text.
- [ ] F112: in `test_settings_handler.py`, Back from SAB speed and from default quality returns the parent state; Back from Settings edits the message to the main menu keyboard before END.
- [ ] F111: in `tests/test_handlers/test_media_handler.py`, `handle_menu_callback` with `menu_movie` awaits `query.answer()`.
- [ ] `pytest`, `flake8` and `mypy src/` pass.

## Notes

- Source: audit 2026-10-28, docs/issues/audit-2026-10-28/FINDINGS.md (F-ids F110, F115, F113, F114, F112, F111).
- Priority: max P 20, sum P 88 (medium).
- Dependencies: slice 28 (F265) gives F115 its shared pagination helper. Do slice 28 first.
- `edit_text_ignoring_unmodified` already exists in `src/utils/chat.py`.
