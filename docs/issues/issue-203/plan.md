# Issue 203: Media add flow monitors or adds the wrong things

**Goal:** The movie, series and music add flow monitors only the seasons the user picked, ends an abandoned search after a timeout, ignores quality buttons from old keyboards, and rate-limits every search and add path.

**Issue:** https://github.com/Krypt0nBull3t/Addarr/issues/203 (F060, F061, F062, F063)

**Branch:** `fix/203-media-add-flow-wrong-things` (from `origin/development`)

## Context and root causes

Found by reading the source. Line numbers are from `origin/development` at `61069b0`.

- **F060** `src/bot/handlers/media/season_picker.py:68-95`. "All Seasons" sets `future_mode = "all"`. The single-season toggle (`else` branch, line 86) edits `selected_seasons` but never clears `future_mode`. `handle_season_confirm` (line 169) treats `future_mode == "all"` as "monitor every season" and ignores `selected_seasons`.
- **F061** `src/bot/handlers/media/handler.py:60-152`. The media `ConversationHandler` has no `conversation_timeout`. It is registered before Settings and Webhooks (`src/main.py:123-135`), so an open `SEARCHING` state takes their typed text. PTB raises at registration if `conversation_timeout` is set and the application has no job queue. `requirements.txt` has `python-telegram-bot==22.8` without the `job-queue` extra, and APScheduler is not in `.venv`. `Application.builder().build()` (`src/main.py:88`) creates the job queue by itself once APScheduler is installed, so `main.py` needs no change.
- **F062** `handler.py:507-538`. `handle_selection` draws the quality keyboard (`handler.py:473-488`) and stores no message id. `handle_quality_selection` acts on any `quality_` callback and overwrites `selected_profile_id`, so a tap on an old movie keyboard reaches the newest series selection.
- **F063** `handle_search` (`handler.py:236`) has no `@rate_limit`. The menu path (`handle_menu_callback` to `SEARCHING` to `handle_search`) is therefore unlimited. `CalendarHandler.show_upcoming` (`calendar.py:52`) has none. No add path uses the `modify` category.

## Decisions (approved)

- F061 requirement line: `python-telegram-bot[job-queue]==22.8`. No separate APScheduler line. `test_requirements_are_pinned` accepts an `[extra]` but still requires `==version`. #214 changes this same line later.
- F062: store `context.user_data["quality_message_id"]`. Ignore every `quality_` callback whose `message_id` differs, including `quality_cancel`. A missing stored id counts as a mismatch.
- F063: `@rate_limit("search")` on `handle_search`. `@rate_limit("modify")` on `show_upcoming`. For adds, do not decorate picker or toggle callbacks. Check the `modify` limit once, just before each add request, with one shared helper. Entry-point `@rate_limit("search")` decorators stay (one `/movie` search uses 2 of the `search` budget; accepted).
- A refused call returns `None`, so the PTB conversation keeps its state and the user can retry after the wait.
- No `ConversationHandler.TIMEOUT` state or message (YAGNI).

## Files

- Modify `src/bot/handlers/media/season_picker.py` (F060, F063 check before the add)
- Modify `src/bot/handlers/media/handler.py` (F061, F062, F063)
- Modify `src/bot/handlers/media/album_picker.py` (F063 check before three adds)
- Modify `src/bot/handlers/calendar.py` (F063)
- Modify `src/services/rate_limit.py` (shared helper, decorator uses it)
- Modify `requirements.txt`, `tests/test_architecture/test_agent_tooling.py` (F061)
- Tests: `tests/test_handlers/test_media_handler.py`, `tests/test_handlers/test_rate_limit_decorator.py`, `tests/test_handlers/test_calendar_handler.py`

## Tasks

### Task 1: F060 untick after All Seasons

- Test `test_season_untick_after_all_seasons_monitors_only_remaining` in `test_media_handler.py`: tap `season_all`, tap `season_1`, then `handle_season_confirm`. Assert `add_series_with_profile` received `seasons_data` with season 1 `monitored: False` and season 2 `monitored: True`. Run it, expect FAIL (season 1 is `True`).
- Fix in `season_picker.py` single-season branch: after toggling, `if future_mode == "all": future_mode = None`.
- Existing tests for the "all" toggle and confirm must still pass.

### Task 2: F062 stale quality keyboard

- Tests in `test_media_handler.py`:
  - `test_handle_selection_stores_quality_message_id`: after the quality keyboard is drawn, `user_data["quality_message_id"] == query.message.message_id`.
  - `test_stale_quality_callback_is_ignored`: stored id 7, callback from message 99. Assert no add call, `selected_profile_id` not in `user_data`, result is `QUALITY_SELECT`. Same for `quality_cancel`.
  - Run, expect FAIL.
- Fix in `handler.py`: store the id after the keyboard edit in `handle_selection`. In `handle_quality_selection`, right after `query.answer()`, return `QUALITY_SELECT` when `query.message.message_id != context.user_data.get("quality_message_id")`.
- Update existing `handle_quality_selection` tests so `quality_message_id` equals the update's message id.
- Integration: check `tests/integration/` for a media-flow test; extend it with a stale-button case when the BotHarness fits.

### Task 3: F061 conversation timeout

- Tests:
  - `test_media_conversation_has_timeout` in `test_media_handler.py`: `get_handler()[0].conversation_timeout == 600`.
  - `test_requirements_ask_for_job_queue_extra`: `requirements.txt` contains `python-telegram-bot[job-queue]==22.8`.
  - Widen `test_requirements_are_pinned` regex to `[A-Za-z0-9._-]+(\[[A-Za-z0-9,_-]+\])?==[A-Za-z0-9.]+`.
  - Run, expect FAIL (timeout is `None`, line missing).
- Fix: `conversation_timeout=600` on the `ConversationHandler`; change the requirements line.
- Local only: `.venv/bin/python -m pip install 'python-telegram-bot[job-queue]==22.8'` so PTB accepts the timeout when a test builds an `Application`.
- Check `pip install --dry-run --python-version 3.10 --only-binary=:all:` for the new pin (CLAUDE.md § Requirement pins).

### Task 4: F063 search and upcoming limits

- Helper `async def enforce_rate_limit(update, category) -> bool` in `src/services/rate_limit.py`. It holds the body of today's decorator: returns `True` when disabled (except `auth`), `False` with no user, otherwise runs `check`, sends the `RateLimitExceeded` reply on refusal, returns the result. `rate_limit()` calls it, so behaviour is unchanged.
- Tests (`test_rate_limit_decorator.py`): helper returns `True` under the limit, `False` plus a reply over it, `True` when disabled, `False` with no user. Existing decorator tests stay green.
- Tests (`test_media_handler.py`, `test_calendar_handler.py`): with limit 1 per 60 s patched into `src.services.rate_limit.config`, the second `handle_search` call and the second `show_upcoming` call do nothing and reply with `RateLimitExceeded`.
- Add `@rate_limit("search")` to `handle_search`. Add `@rate_limit("modify")` below `@require_auth` on `show_upcoming`.

### Task 5: F063 modify limit before every add request

Call sites (check just before each, outside the `try` so a refusal is not swallowed): in each, `if not await enforce_rate_limit(update, "modify"): return None`.

- `handler.py` `handle_quality_selection`: before `add_music_with_profile` (album or song) and before `_add_media_with_profile`. Not before the series and artist branches, which only open pickers.
- `season_picker.py` `handle_season_confirm`: before `add_series_with_profile`.
- `album_picker.py`: before `add_music_with_profile` in `handle_album_monitor_mode` ("all"), `handle_album_selection` ("monitor_all") and `handle_album_confirm`.
- Tests: for each site, with limit 1 per 60 s, a second add is refused: the `add_*_with_profile` mock is awaited once and the user gets `RateLimitExceeded`. A picker or toggle tap never consumes the limit (five toggles then an add still adds).

## Review focus

- Rate limiting disabled in config: no add or search is refused (existing tests cover the default).
- `effective_user` is `None`: refused without a crash.
- Stale `quality_cancel` is ignored too.
- A refused add keeps the conversation state, so a retry of the same confirm works after the wait.

## Verification

`pytest`, `flake8`, `mypy src/`, translations check, architecture tests, all through the suite lock via the preflight in the `addarr-workflow` skill.

## Risks

- One `/movie` search uses 2 of 10 `search` calls per 60 s (entry point plus `handle_search`).
- #202 (addarr-20) adds a direct-add path to `handle_selection`. If it uses the same add call, it needs the same check. The second PR to merge rebases on the first.
