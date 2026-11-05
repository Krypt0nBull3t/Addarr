---
title: "Bazarr subtitle search does not search"
labels: [bug, ux, priority:medium]
slice: 24
findings: [F130, F131, F132]
---

## Bug

- "Search Subtitles" never starts a subtitle search. It filters Bazarr's movie list by title and shows the matches. The issue-114 tasks are marked done and list methods that do not exist (`search_movie_subtitles`, `search_episode_subtitles`).
- The Bazarr conversation has no `allow_reentry`, so a second Search tap does nothing.
- The search prompt has no Cancel button, and `menu_cancel` is not in the fallbacks. Text typed later is searched.

## Steps to reproduce

1. Enable Bazarr, open `/subtitles`, tap "Search Subtitles", type a movie title.
2. The bot lists matching movies. No subtitle search starts in Bazarr.
3. Tap "Search Subtitles" again while the first prompt is open: nothing happens.
4. Tap Search, then tap Cancel in another menu (`menu_cancel`), then type any text: the text is searched as a Bazarr title.

## Expected behavior

The button starts a Bazarr subtitle search for the chosen movie, once per language. A second tap opens the prompt again. The prompt has Cancel, and `menu_cancel` ends the conversation.

## Fix

- [ ] **F130** Add the Bazarr call that starts a subtitle search for the chosen movie, per language. Wire the "Search Subtitles" button to it. Make `docs/issues/issue-114/TASKS.md:19` list only methods that exist (`src/api/bazarr.py:79-108`, `src/services/bazarr.py:53-71`, `src/bot/handlers/bazarr.py:156-173`, `docs/issues/issue-114/TASKS.md:19`)
- [ ] **F131** Set `allow_reentry=True` on the conversation (`src/bot/handlers/bazarr.py:57`)
- [ ] **F132** Add a `^menu_cancel$` fallback and a Cancel button on the prompt (`src/bot/handlers/bazarr.py:151`)

## Acceptance criteria

Each test fails before the fix and passes after:

- [ ] F130: `tests/test_api/test_bazarr.py` asserts the client sends one Bazarr subtitle search request per configured language for the chosen movie. `tests/test_services/test_bazarr_service.py` or `tests/test_handlers/test_bazarr_handler.py` asserts that picking a movie calls it with that movie's id.
- [ ] F131: an integration test taps `bazarr_search` twice and gets the prompt both times.
- [ ] F132: the prompt reply has a Cancel button; after `menu_cancel`, typed text does not call `BazarrService.search`.
- [ ] `pytest`, `flake8` and `mypy src/` pass.

## Notes

- Source: audit 2026-10-28, docs/issues/audit-2026-10-28/FINDINGS.md (F-ids F130, F131, F132).
- Priority: max P 18, sum P 48 (medium).
- Dependencies: none in the order of work.
- Related: `docs/issues/issue-114/TASKS.md` (Bazarr integration, task 1.1 marked done).
- Decided 2026-10-28: F130 build the subtitle search: a Bazarr call per language for the chosen movie, with tests.
