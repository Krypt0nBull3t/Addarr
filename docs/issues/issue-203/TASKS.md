# Issue 203: Media add flow monitors or adds the wrong things (TASKS)

Plan: `docs/issues/issue-203/plan.md`. Issue: https://github.com/Krypt0nBull3t/Addarr/issues/203. Branch: `fix/203-media-add-flow-wrong-things`.

### Phase 1: Fix the media add flow (5 tasks)

**Goal:** The add flow monitors only the picked seasons, ends an abandoned search after 600 s, ignores quality buttons from old keyboards, and rate-limits every search and add path.

**Phase Context:**

- Why NOT decorate the picker and toggle callbacks with `@rate_limit("modify")`: `modify` allows 5 calls per 60 s, so one normal album add (result tap, quality tap, album toggles, confirm) would use it up. The check sits just before each add request instead.
- Why NOT remove the entry-point `@rate_limit("search")` decorators: the issue does not ask for it and tests pin them. One `/movie` search uses 2 of the `search` budget; accepted.

- [x] **1.1** F060: unticking a season after "All Seasons" leaves it unmonitored
    - **Context:**
        - **Why:** "All Seasons" sets `future_mode = "all"`. The single-season toggle edits `selected_seasons` but never clears `future_mode`, so `handle_season_confirm` (`future_mode == "all"`) monitors every season.
        - **Architecture:** `SeasonPickerMixin` in `src/bot/handlers/media/season_picker.py`; state lives in `context.user_data`.
        - **Key refs:** `season_picker.py:68-95` (toggle branches), `:169` (confirm treats `"all"` as everything), `tests/test_handlers/test_media_handler.py` (`test_handle_season_selection_all_toggle_on`, `test_handle_season_confirm_all_mode`)
        - **Watch out:** Clear `future_mode` only when it equals `"all"`. `future_seasons` and `future_episodes` keep their meaning when a single season is toggled.
    - **Scope:** One line in the single-season branch plus one test.
    - **Touches:** `src/bot/handlers/media/season_picker.py`, `tests/test_handlers/test_media_handler.py`
    - **Action items:**
        - [RED] Write `test_season_untick_after_all_seasons_monitors_only_remaining`: tap `season_all`, tap `season_1`, then `handle_season_confirm`; assert `seasons_data` has season 1 `monitored: False` and season 2 `monitored: True`
        - [GREEN] In the single-season branch, `if future_mode == "all": future_mode = None`
    - **Success:** the new test fails before the fix and passes after; `pytest tests/test_handlers/test_media_handler.py` passes; flake8 and mypy clean
    - **Completed:** 2026-11-04
    - **Learnings:**
        - The test drives the real sequence (`season_all`, `season_1`, `season_confirm`) through `handle_season_selection`, because the bug is state left behind between taps.
        - The red run showed season 1 `monitored: True`, so the test failed for the right reason.
    - **Key Changes:**
        - `src/bot/handlers/media/season_picker.py`: the single-season toggle sets `future_mode = None` when it was `"all"`.
        - `tests/test_handlers/test_media_handler.py`: `test_season_untick_after_all_seasons_monitors_only_remaining`.
    - **Notes:** `future_seasons` and `future_episodes` keep their meaning on a single-season toggle.

- [ ] **1.2** F062: a quality button acts only on the keyboard it was drawn for
    - **Context:**
        - **Why:** `handle_selection` draws the quality keyboard but stores no message id. `handle_quality_selection` acts on any `quality_` callback and overwrites `selected_profile_id`, so a tap on an old movie keyboard reaches the newest series selection.
        - **Architecture:** `MediaHandler` in `src/bot/handlers/media/handler.py`; `context.user_data` keys.
        - **Key refs:** `handler.py:473-488` (keyboard edit in `handle_selection`), `:507-538` (`handle_quality_selection`), existing `handle_quality_selection` tests around `test_media_handler.py:515-630`
        - **Watch out:** Check the id right after `query.answer()`, before the `quality_cancel` branch, so a stale cancel is ignored too. A missing stored id counts as a mismatch. Return `QUALITY_SELECT` so the state stays. Existing quality tests must set `quality_message_id` to the update's message id. If `#202` has moved this code into `MediaHandler._continue_with_profile`, store the id where the keyboard is still drawn.
    - **Scope:** Store the id, guard the callback, update existing tests, extend an integration test if the BotHarness fits.
    - **Touches:** `src/bot/handlers/media/handler.py`, `tests/test_handlers/test_media_handler.py`, `tests/integration/` (check for a media flow test)
    - **Action items:**
        - [RED] Write `test_handle_selection_stores_quality_message_id`
        - [RED] Write `test_stale_quality_callback_is_ignored` (stored id 7, callback from message 99: no add call, `selected_profile_id` not in `user_data`, result `QUALITY_SELECT`) and the same for `quality_cancel`
        - [GREEN] Store `context.user_data["quality_message_id"]` after the keyboard edit; add the guard at the top of `handle_quality_selection`
        - [GREEN] Update the existing quality tests to set the id
        - Integration: extend the media flow test in `tests/integration/` with a stale-button case when it exists and the BotHarness fits (flow rule, step 4)
    - **Success:** new tests fail before and pass after; media handler and integration tests pass; flake8 and mypy clean

- [ ] **1.3** F061: abandoned search ends after a timeout
    - **Context:**
        - **Why:** The media `ConversationHandler` has no timeout and is registered before Settings and Webhooks, so an open `SEARCHING` state takes their typed text ("8080" gets searched as a movie).
        - **Architecture:** `conversation_timeout=600` on the `ConversationHandler` in `MediaHandler.get_handler()`. PTB needs a job queue for it (APScheduler, from the `job-queue` extra). `Application.builder().build()` in `src/main.py:88` creates the job queue itself, so `main.py` needs no change.
        - **Key refs:** `handler.py:60-152`, `requirements.txt:7`, `tests/test_architecture/test_agent_tooling.py:312-318` (`test_requirements_are_pinned`), CLAUDE.md § Requirement pins
        - **Watch out:** One requirement line: `python-telegram-bot[job-queue]==22.8`. No separate APScheduler line. The regex in `test_requirements_are_pinned` must accept an `[extra]` but still require `==version`. #214 will change the pin on this same line later. Install the extra into this worktree's `.venv` only: `.venv/bin/python -m pip install 'python-telegram-bot[job-queue]==22.8'`. No `ConversationHandler.TIMEOUT` state or message (YAGNI).
    - **Scope:** Timeout, requirement line, test regex.
    - **Touches:** `src/bot/handlers/media/handler.py`, `requirements.txt`, `tests/test_architecture/test_agent_tooling.py`, `tests/test_handlers/test_media_handler.py`
    - **Action items:**
        - [RED] Write `test_media_conversation_has_timeout` (`get_handler()[0].conversation_timeout == 600`)
        - [RED] Write `test_requirements_ask_for_job_queue_extra` (the line exists in `requirements.txt`)
        - [RED] Widen the `test_requirements_are_pinned` regex to `[A-Za-z0-9._-]+(\[[A-Za-z0-9,_-]+\])?==[A-Za-z0-9.]+`
        - [GREEN] Set `conversation_timeout=600`; change the requirement line; install into `.venv`
        - Run the 3.10 dry-run pin check from CLAUDE.md for the new line
    - **Success:** new tests fail before and pass after; architecture tests pass; the 3.10 dry-run install succeeds

- [ ] **1.4** F063a: search and /upcoming are rate-limited; shared helper
    - **Context:**
        - **Why:** `handle_search` has no `@rate_limit`, so the menu path is unlimited. `show_upcoming` has none. The add check (task 1.5) needs the limit check as a plain call, not a decorator.
        - **Architecture:** New `async def enforce_rate_limit(update, category) -> bool` in `src/services/rate_limit.py`. It holds the body of today's `rate_limit` decorator, and `rate_limit()` calls it, so decorator behaviour stays the same.
        - **Key refs:** `src/services/rate_limit.py:113-157`, `tests/test_handlers/test_rate_limit_decorator.py` (patch `src.services.rate_limit.config` and `TranslationService`), `handler.py:236` (`handle_search`), `calendar.py:52` (`show_upcoming`)
        - **Watch out:** Disabled config returns `True` except for `auth`. No effective user returns `False`. A refusal sends the `RateLimitExceeded` reply and returns `False`. Keep the `# pragma: no cover` on the `msg is None` branch. Place `@rate_limit("modify")` below `@require_auth` on `show_upcoming`. A refused `handle_search` returns `None`, so the conversation keeps `SEARCHING`. No `@require_auth` is added to `handle_search`.
    - **Scope:** Helper, decorator refactor, two decorators, tests.
    - **Touches:** `src/services/rate_limit.py`, `src/bot/handlers/media/handler.py`, `src/bot/handlers/calendar.py`, `tests/test_handlers/test_rate_limit_decorator.py`, `tests/test_handlers/test_media_handler.py`, `tests/test_handlers/test_calendar_handler.py`
    - **Action items:**
        - [RED] Write helper tests: `True` under the limit, `False` plus a reply over it, `True` when disabled, `False` with no user
        - [RED] Write `handle_search` and `show_upcoming` tests: limit 1 per 60 s, the second call does nothing and replies `RateLimitExceeded`
        - [GREEN] Implement `enforce_rate_limit`; make `rate_limit()` call it
        - [GREEN] Add `@rate_limit("search")` to `handle_search` and `@rate_limit("modify")` to `show_upcoming`
    - **Success:** new tests fail before and pass after; all existing decorator tests pass unchanged; `scripts/test_runner.py services` and `handlers` pass with the coverage lines covered

- [ ] **1.5** F063b: modify limit checked before every add request
    - **Context:**
        - **Why:** Adds have no `modify` limit. Decorating picker or toggle callbacks would use up 5 calls per 60 s on one normal add, so the check goes just before each add request.
        - **Architecture:** `if not await enforce_rate_limit(update, "modify"): return None` just before the add call, outside the `try` so a refusal is not swallowed. `None` keeps the conversation state, and a retry of the same confirm works after the wait.
        - **Key refs:** add sites: `handler.py` `handle_quality_selection` (before `add_music_with_profile` for album or song, and before `_add_media_with_profile`; not before the series and artist branches, which only open pickers); `season_picker.py:184` `handle_season_confirm` (`add_series_with_profile`); `album_picker.py` `handle_album_monitor_mode` ("all"), `handle_album_selection` ("monitor_all"), `handle_album_confirm` (all `add_music_with_profile`). The `add_fn` call in `handle_selection` only fetches the profile list and gets no check.
        - **Watch out:** #202 (addarr-20) moves the add part of `handle_quality_selection` into `MediaHandler._continue_with_profile`. If #202 merged first, put the check inside `_continue_with_profile`, just before the add call. Whichever PR merges second rebases. `handle_season_confirm` and `handle_album_confirm` run from inside another callback that already answered the query, so the refusal reply goes through `update.effective_message`.
    - **Scope:** Five call sites plus tests.
    - **Touches:** `src/bot/handlers/media/handler.py`, `src/bot/handlers/media/season_picker.py`, `src/bot/handlers/media/album_picker.py`, `tests/test_handlers/test_media_handler.py`
    - **Action items:**
        - [RED] For each add site, write a test with limit 1 per 60 s: the second add is refused, the `add_*_with_profile` mock is awaited once, the user gets `RateLimitExceeded`
        - [RED] Write a test that five picker or toggle taps followed by an add still add (taps do not use the limit)
        - [GREEN] Add the `enforce_rate_limit(update, "modify")` call before each add request
    - **Success:** new tests fail before and pass after; `scripts/test_runner.py handlers --coverage` passes; flake8 and mypy clean
