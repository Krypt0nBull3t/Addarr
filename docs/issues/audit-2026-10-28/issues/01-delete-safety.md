---
title: "Delete can erase the wrong media and its files"
labels: [bug, security, i18n, agent-ready, priority:critical]
slice: 1
findings: [F003, F001, F002, F004]
---

## Bug

/delete can remove a different item than the one the user tapped. It also deletes the files on disk without saying so.

- **F003** The confirm text has no title. It says only "Is this the series you want to delete?". The handler passes `title=`, but `ThisDelete` has no `%{title}` placeholder.
- **F001** Every delete sends `deleteFiles=true`. The prompt never says that files are erased. With `enableAdmin: false` (the default in `config_example.yaml`), any authenticated user can delete.
- **F002** Delete buttons carry only an id (`delete_item_<id>`, `delete_confirm`). The media type and the item come from `user_data`. Tapping an item on an older /delete list after opening another type deletes a different item. Radarr and Sonarr ids collide.
- **F004** /delete makes one button per library item. Telegram caps an inline keyboard at about 100 buttons (secondary sources; unverified live). Large libraries get `MediaListError`.

## Steps to reproduce

F002 (wrong item):

1. Send /delete and tap Movies. Keep this list open.
2. Send /delete again and tap Series. `user_data["delete_type"]` is now `series`.
3. In the first list, tap the movie with id 42.
4. The bot loads the series with id 42 and asks "Is this the series you want to delete?" with no title (F003).
5. Tap Delete. Sonarr deletes series 42 and its files.

F003 and F001 (prompt):

1. Send /delete, tap Series, then tap any series.
2. The prompt names no title and does not say that files are deleted.
3. Tap Delete. Sonarr receives `DELETE series/<id>?deleteFiles=true`.

F004 (large library):

1. Use a Radarr library with more than about 100 movies.
2. Send /delete and tap Movies.
3. The bot replies with `MediaListError` instead of a list.

## Expected behavior

- The confirm text names the title and says that the files on disk are deleted too.
- A button acts on the exact type and item it was drawn for, whatever other /delete lists are open.
- A large library shows a paged list.

## Fix

- [ ] **F003** Add `%{title}` and "and its files on disk" to `ThisDelete` in all 9 locales and the template (`translations/addarr.en-us.yml:59`, `:71` in the other 8 locales, `translations/addarr.template.yml:63`; caller `src/bot/handlers/delete.py:200-206`)
- [ ] **F001** Make the confirm text show the title and say that the files on disk are deleted too (done by F003). Keep `deleteFiles=true`, the config and the `enableAdmin` default as they are. Add no "keep files" option (`src/api/radarr.py:321`, `src/api/sonarr.py:332`, `src/api/lidarr.py:322`)
- [ ] **F002** Put the type and id in callback_data (`delete_item_movie_42`, `delete_confirm_movie_42`) and read them from there, not from `user_data` (`src/bot/handlers/delete.py:102`, `:152-170`, `:214-232`)
- [ ] **F004** Paginate the item list with the shared helper from slice 28 (`src/bot/handlers/delete.py:124-132`)

## Acceptance criteria

Each test below fails before the fix and passes after it.

- **F003** A test loads every real `translations/addarr.*.yml` file and asserts that `ThisDelete` contains `%{title}`. The autouse translation mock cannot catch this, so the test must read the files.
- **F001** The same test asserts that the en-us `ThisDelete` says the files on disk are deleted too.
- **F002** `tests/test_handlers/test_delete_handler.py`: with `user_data["delete_type"] = "series"`, tapping `delete_item_movie_42` calls `get_movie` with 42 and never `get_series`. Tapping `delete_confirm_movie_42` calls `delete_movie` with 42, whatever `user_data` holds.
- **F004** `tests/test_handlers/test_delete_handler.py`: with 150 movies, the keyboard holds one page of item buttons plus a nav row, and the bot does not send `MediaListError`.
- `pytest`, `flake8`, `mypy src/` and `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` pass.

## Notes

- Source: audit 2026-10-28, docs/issues/audit-2026-10-28/FINDINGS.md (F-ids F003, F001, F002, F004).
- Priority: max P 45, sum P 153 (critical).
- Dependencies: slices 1-8 go first. F004 needs the shared pagination helper from slice 28 (F265). Build that helper first, or build it here and let slice 28 reuse it.
- Related: F211 (slice 29) rewrites `ThisDelete` in fr, it, pt and de. F005 (slice 25) fixes the `StopDelete` label on the same keyboards.
- Decided 2026-10-28: F001 clear prompt only (title plus "files on disk are deleted too"). No config change, no keep-files option, `enableAdmin` default unchanged.
