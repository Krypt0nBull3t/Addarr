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

- [x] **1.2** F062: a quality button acts only on the keyboard it was drawn for
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
    - **Completed:** 2026-11-04
    - **Learnings:**
        - The BotHarness `tap_button(..., message_id=...)` already takes a message id, so the stale-button case needed no harness change. Existing integration taps use the default id 100, which is also the id the keyboard edit stores, so those tests passed unchanged.
        - The `make_message` factory gives `message.message_id` as an auto attribute. Unit tests set it to an int when they compare it.
        - Reverted the guard once to watch the integration test fail (`add_movie_with_profile` awaited once), then restored it.
    - **Key Changes:**
        - `src/bot/handlers/media/handler.py`: `handle_selection` stores `quality_message_id` after the keyboard edit; `handle_quality_selection` returns `QUALITY_SELECT` for any callback from another message, `quality_cancel` included.
        - `tests/test_handlers/test_media_handler.py`: two new tests (stores the id, ignores stale `quality_1` and `quality_cancel`); eight existing `handle_quality_selection` tests set `quality_message_id` from the update's message.
        - `tests/integration/test_media_flow.py`: `test_stale_quality_button_is_ignored`.
    - **Notes:** A missing stored id counts as a mismatch. #202 moves the add part of `handle_quality_selection` into `_continue_with_profile`; the guard stays at the top of `handle_quality_selection`, so a rebase keeps it.

- [x] **1.3** F061: abandoned search ends after a timeout
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
    - **Completed:** 2026-11-04
    - **Learnings:**
        - Without APScheduler PTB only warns ("No `JobQueue` set up") and ignores `conversation_timeout`, so the timeout would fail silently. The test suite turns that warning into an error. `test_application_has_job_queue` pins that the dependency is installed.
        - PTB 22.8 `JobQueue.start()` and `stop()` are coroutines. The integration `BotHarness` never calls `Application.start()`, so with a timeout every media test failed ("JobQueue is not running") until `_make_harness` awaited `job_queue.start()` and `stop(wait=False)`.
        - `PreRunChecker.parse_requirements` kept the `[job-queue]` suffix, so the startup check would have reported `python-telegram-bot[job-queue]` as missing on every start. It now strips extras.
    - **Key Changes:**
        - `requirements.txt`: `python-telegram-bot[job-queue]==22.8` (one line, no APScheduler line).
        - `src/bot/handlers/media/handler.py`: `conversation_timeout=600` on the media `ConversationHandler`.
        - `src/utils/prerun.py`: `parse_requirements` strips `[extras]`.
        - `tests/test_architecture/test_agent_tooling.py`: pinned-requirements regex accepts an `[extra]`; new `test_requirements_ask_for_job_queue_extra`.
        - `tests/test_handlers/test_media_handler.py`: `test_media_conversation_has_timeout`. `tests/test_main.py`: `test_application_has_job_queue`. `tests/test_utils/test_prerun.py`: `test_strips_extras`. `tests/integration/conftest.py`: harness starts and stops the job queue.
    - **Notes:** The 3.10 dry-run install of both requirement files exits 0. Install the extra into a worktree `.venv` with `pip install 'python-telegram-bot[job-queue]==22.8'`. #214 changes the pin on this same requirements line.

- [x] **1.4** F063a: search and /upcoming are rate-limited; shared helper
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
    - **Completed:** 2026-11-04
    - **Learnings:**
        - The decorator tests live in `tests/test_handlers/`, so `scripts/test_runner.py services --coverage` alone shows `rate_limit.py` at 81%. The `handlers` run (and the full gate) covers it at 100%.
        - A `# pragma: no cover` on an `if x is not None:` line would hide the whole reply block. Keep it on the `if msg is None: return False` guard, as the decorator had it.
        - For a command update, `update.message` and `update.effective_message` are the same mock in `make_update`, so assert the reply once on either.
    - **Key Changes:**
        - `src/services/rate_limit.py`: new `enforce_rate_limit(update, category) -> bool`; `rate_limit()` now calls it.
        - `src/bot/handlers/media/handler.py`: `@rate_limit("search")` on `handle_search`.
        - `src/bot/handlers/calendar.py`: `@rate_limit("modify")` on `show_upcoming`, below `@require_auth`.
        - Tests: three `enforce_rate_limit` tests, `test_handle_search_refuses_once_search_limit_is_used_up`, `test_show_upcoming_refuses_once_modify_limit_is_used_up`.
    - **Notes:** `enforce_rate_limit` is the call task 1.5 puts before each add request.

- [x] **1.5** F063b: modify limit checked before every add request
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
    - **Completed:** 2026-11-04
    - **Learnings:**
        - A test that calls `handle_quality_selection` twice must reuse the same update. A new update has a new message id, and the F062 guard would ignore it before the rate limit runs.
        - A refused `handle_season_confirm` returns `None` through `handle_season_selection` (including the "Monitor All" auto-submit), so the conversation keeps `SEASON_SELECT` and a retry of the same confirm works after the wait.
        - Six sites call an add request: the movie or other-media add and the music album or song add in `handle_quality_selection`, `handle_season_confirm`, and three in `album_picker.py`. The `add_fn` call in `handle_selection` only fetches the profile list and gets no check.
    - **Key Changes:**
        - `src/bot/handlers/media/handler.py`, `season_picker.py`, `album_picker.py`: `if not await enforce_rate_limit(update, "modify"): return None` just before each add request, outside the `try`.
        - `tests/test_handlers/test_media_add_rate_limit.py` (new): a parametrized test with one case per add site (second add refused, reply `RateLimitExceeded`), and a test that a quality tap, five season toggles and the confirm use one `modify` call.
    - **Notes:** #202 merged first (`4d593ff`) and moved the add part of `handle_quality_selection` into `MediaHandler._continue_with_profile`. After the merge of `origin/development` the two checks sit inside `_continue_with_profile`, just before each add call. It now takes `update` (it read `query` before), because `enforce_rate_limit` needs the update. The default-profile path in `handle_selection` calls it too, so it has the limit; `test_handle_selection_default_profile_add_is_rate_limited` covers that path.
