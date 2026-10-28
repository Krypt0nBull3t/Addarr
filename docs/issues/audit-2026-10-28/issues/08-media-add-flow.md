---
title: "Media add flow monitors or adds the wrong things"
labels: [bug, ux, agent-ready, priority:critical]
slice: 8
findings: [F060, F061, F062, F063]
---

## Bug

The movie, series and music add flow can monitor seasons the user unticked, add with a stale quality profile, and swallow text meant for other flows.

- **F060** Season picker: tap "All Seasons", then untick a season. `future_mode` stays "all", and confirm monitors every season.
- **F061** The media conversation has no timeout and is registered before webhooks and Bazarr. An abandoned search takes their typed text: a port "8080" is searched as a movie.
- **F062** Old `quality_` buttons apply to the newest selection. A Radarr profile id can reach Sonarr.
- **F063** The rate limit covers only /movie, /series and /music. The menu path is unlimited, adds have no "modify" limit, and /upcoming has none.

## Steps to reproduce

F060:

1. Send /series, pick a series and a quality profile.
2. Tap "All Seasons".
3. Untick season 1.
4. Confirm. Sonarr monitors every season, season 1 too.

F061:

1. Send /movie and leave the search prompt unanswered.
2. Open /webhooks and start setting the port.
3. Type `8080`.
4. The bot searches for a movie named "8080".

F062:

1. Send /movie and pick a movie. A keyboard with Radarr profiles appears.
2. Send /series and pick a series. A new quality keyboard appears.
3. Tap a profile on the first (movie) keyboard.
4. The series is added with the Radarr profile id.

F063:

1. Open the main menu and start searches through the menu buttons, again and again.
2. No limit applies. Add confirms and /upcoming have no limit either.

## Expected behavior

- Unticking a season after "All Seasons" leaves that season unmonitored.
- An abandoned search ends after a timeout, and other flows get their own text.
- A quality button acts only on the selection it was drawn for.
- Every search path is rate-limited as "search". Adds and /upcoming are rate-limited as "modify".

## Fix

- [ ] **F060** In the single-season branch, add `if future_mode == "all": future_mode = None` (`src/bot/handlers/media/season_picker.py:86-93`, `:169`)
- [ ] **F061** Set `conversation_timeout=600` on the media conversation. This needs `python-telegram-bot[job-queue]` (`src/bot/handlers/media/handler.py:60-152`, `src/main.py:123-135`, `:181`)
- [ ] **F062** Store the quality keyboard's message_id and ignore callbacks from other messages (`src/bot/handlers/media/handler.py:536`)
- [ ] **F063** Add `@rate_limit("search")` to `handle_search`, and `@rate_limit("modify")` to the add confirm and to `show_upcoming` (`src/bot/handlers/media/handler.py:155-236`, `src/bot/handlers/calendar.py:52-74`)

## Acceptance criteria

Each test below fails before the fix and passes after it.

- **F060** `tests/test_handlers/test_media_handler.py`: tap "All Seasons", untick season 1, confirm. The `seasons_data` sent to the add call has season 1 with `monitored: False`.
- **F061** `tests/test_handlers/test_media_handler.py`: the media `ConversationHandler` has `conversation_timeout == 600`. `requirements.txt` asks for `python-telegram-bot[job-queue]`.
- **F062** `tests/test_handlers/test_media_handler.py`: a `quality_` callback from a message other than the stored keyboard message adds nothing and does not change `selected_profile_id`.
- **F063** `tests/test_handlers/test_rate_limit_decorator.py` or the handler tests: `handle_search`, the add confirm and `show_upcoming` refuse a call once their limit is used up.
- `pytest`, `flake8` and `mypy src/` pass.

## Notes

- Source: audit 2026-10-28, docs/issues/audit-2026-10-28/FINDINGS.md (F-ids F060, F061, F062, F063).
- Priority: max P 40, sum P 99 (critical).
- Dependencies: slices 1-8 go first. F061 adds the `job-queue` extra to `python-telegram-bot`. Slice 19 (F151) pins that package to `~=22.8`. Keep both changes on the same requirement line.
- No owner decision needed.
