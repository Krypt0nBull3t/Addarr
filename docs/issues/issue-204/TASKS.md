# Issue 204 Tasks: Radarr and Sonarr API calls match the Servarr specs

Source: `plan.md` and `design.md` in this folder. Issue: https://github.com/Krypt0nBull3t/Addarr/issues/204 (F040 to F045).
Branch: `fix/204-servarr-api-spec-mismatch`. Line numbers are from `origin/development` at `cf51f57`.

### Phase 1: API requests (2 tasks)

**Goal:** The Radarr and Sonarr requests carry the spec's include flags and int event types.

- [x] **1.1** F040 include flags on 7 requests
    - **Context:**
        - **Why:** The spec default for `includeSeries`, `includeEpisode` and `includeMovie` is false. History titles are "" and Sonarr rows have no series name.
        - **Architecture:** String endpoints built in each client method, sent through `self._request()`. No new helper.
        - **Key refs:** `src/api/sonarr.py` `get_missing` (~l.170), `get_queue` (~l.190), `get_cutoff_unmet` (~l.210), `get_calendar` (~l.251), `get_history` (~l.268). `src/api/radarr.py` `get_queue` (~l.179), `get_history` (~l.257). Tests: `tests/test_api/test_sonarr.py` (missing ~l.752, cutoff ~l.802, queue ~l.889, history ~l.939, calendar ~l.700), `tests/test_api/test_radarr.py` (queue ~l.824, history ~l.924).
        - **Watch out:** `aioresponses` matches the full URL with query string, so every existing mocked URL for these 7 requests changes. Radarr `wanted/missing`, `wanted/cutoff` and `calendar` return movie objects: add no flag there.
    - **Scope:** Add the flags to the 7 endpoint strings and update the mocked URLs.
    - **Touches:** `src/api/sonarr.py`, `src/api/radarr.py`, `tests/test_api/test_sonarr.py`, `tests/test_api/test_radarr.py`
    - **Action items:**
        - [RED] Sonarr tests: `wanted/missing`, `wanted/cutoff` and `calendar` URLs carry `includeSeries=true`. `queue` and `history` carry `includeSeries=true&includeEpisode=true`.
        - [RED] Radarr tests: `queue` and `history` URLs carry `includeMovie=true`.
        - [GREEN] Append the flags in the 7 endpoint strings.
    - **Success:** `scripts/test_runner.py api --coverage` passes, flake8 and mypy clean.
    - **Completed:** 2026-11-05
    - **Learnings:**
        - `aioresponses` matches the whole URL, so updating the mocked URL is the assertion. The 9 `*_success` and history tests failed before the fix. The `*_empty` tests passed before the fix too, because an unmatched URL also returns `[]`.
        - Radarr `wanted/missing`, `wanted/cutoff` and `calendar` return movie objects, so they got no flag.
    - **Key Changes:**
        - `src/api/sonarr.py`: `includeSeries=true` on missing, cutoff, calendar. `includeSeries=true&includeEpisode=true` on queue and history.
        - `src/api/radarr.py`: `includeMovie=true` on queue and history.
        - `tests/test_api/test_sonarr.py`, `tests/test_api/test_radarr.py`: mocked URLs carry the flags.
    - **Notes:** The flags sit before `eventType` in the history URL. Task 1.2 changes the `eventType` value only.

- [x] **1.2** F041 history event types as ints
    - **Context:**
        - **Why:** The spec wants `eventType` as an int array. The string names make the Grabbed, Imported and Failed tabs empty.
        - **Architecture:** The keyboard, callback data and `HistoryHandler` keep the string names. The API client owns the wire format (design.md).
        - **Key refs:** `src/api/base.py` (module level), `src/api/sonarr.py` `get_history`, `src/api/radarr.py` `get_history`, `src/bot/keyboards.py` `get_history_items_keyboard` (names), tests `test_get_history_with_event_type` in both API test files.
        - **Watch out:** Map: grabbed 1, downloadFolderImported 3, downloadFailed 4. `get_history` catches exceptions and returns `[]`, so an unknown name (KeyError) returns `[]` with a logged error. Task 1.1 already changed the history URL. `src/api/` must not import services or handlers.
    - **Scope:** `HISTORY_EVENT_TYPES` in `src/api/base.py`, used by both `get_history` methods.
    - **Touches:** `src/api/base.py`, `src/api/sonarr.py`, `src/api/radarr.py`, both API test files
    - **Action items:**
        - [RED] For each client, tests that `grabbed`, `downloadFolderImported` and `downloadFailed` send `eventType=1`, `3` and `4`.
        - [RED] For each client, a test that an unknown name returns `[]`.
        - [GREEN] Add `HISTORY_EVENT_TYPES` and use it in both clients.
    - **Success:** API scoped run passes, flake8 and mypy clean.
    - **Completed:** 2026-11-05
    - **Learnings:**
        - The unknown-name test only fails before the fix when the bogus URL is mocked with records: an unmocked URL also returns `[]`.
        - An unknown name raises `KeyError` inside `get_history`, and the existing `except Exception` logs it and returns `[]`.
    - **Key Changes:**
        - `src/api/base.py`: `HISTORY_EVENT_TYPES` (grabbed 1, downloadFolderImported 3, downloadFailed 4).
        - `src/api/sonarr.py`, `src/api/radarr.py`: `get_history` sends `eventType=<int>`.
        - Both API test files: parametrized `test_get_history_with_event_type` and `test_get_history_unknown_event_type`.
    - **Notes:** Keyboard, callback data and `HistoryHandler` still use the string names. Sonarr `seriesFolderImported` (2) has no tab, so it is not mapped.

### Phase 2: One lookup per add (1 task)

**Goal:** Each add makes one lookup and no failing call.

- [x] **2.1** F042 single lookup, pass the result on
    - **Context:**
        - **Why:** `movie/lookup/tmdb/{id}` and `series/lookup/tvdb/{id}` do not exist (404 and an ERROR log). One series add makes 1 failing and 3 identical lookups.
        - **Architecture:** `get_movie` and `get_series` do one `lookup?term=` call. `MediaService.add_series` reads seasons from `series["seasons"]`. `add_movie` and `add_series` take an optional `lookup` dict. Layer rule: handlers call `MediaService`, never an API client.
        - **Key refs:** `src/api/radarr.py` `get_movie` (~l.59) and `add_movie` (~l.121). `src/api/sonarr.py` `get_seasons` (~l.83), `add_series` (~l.102), `get_series` (~l.147). `src/services/media.py` `add_movie` (~l.248), `add_movie_with_profile` (~l.282), `add_series` (~l.310), `add_series_with_profile` (~l.350). `src/bot/handlers/media/handler.py` `_add_media_with_profile` (~l.669) and the quality-select path (~l.560-660). `src/bot/handlers/media/season_picker.py` (~l.191). Tests: `tests/test_api/test_radarr.py` (~l.140-170), `tests/test_api/test_sonarr.py` (~l.259-343), `tests/test_services/test_media_service.py` (~l.903 `test_get_series_single_lookup`), `tests/test_handlers/test_media_handler.py`.
        - **Watch out:** `_add_media_with_profile` serves movie, series and music through `MEDIA_CONFIG`: add the `lookup` keyword only when it is not None, so `add_music_with_profile` keeps its signature. `test_media_config_dispatch_integrity` checks method names only. `quality_data` holds the dict under `"movie"` and `"series"`. Check callers of `get_seasons`, `get_movie` and `get_series` with the graph or grep before removing `get_seasons`.
    - **Scope:** API clients, `MediaService`, the quality-select handler and the season picker.
    - **Touches:** `src/api/radarr.py`, `src/api/sonarr.py`, `src/services/media.py`, `src/bot/handlers/media/handler.py`, `src/bot/handlers/media/season_picker.py`, the four test files above
    - **Action items:**
        - [RED] API tests: `get_movie` and `get_series` request only `lookup?term=tmdb:` or `tvdb:` and never the `lookup/tmdb/` or `lookup/tvdb/` path. `add_movie` and `add_series` with `lookup` make no lookup request and POST the dict's ids and title. Without `lookup` they still look up.
        - [RED] Service tests: `MediaService.add_series` makes one lookup request and returns `seasons` from the series dict, and "No seasons found" when empty. `add_movie_with_profile` and `add_series_with_profile` pass `lookup` to the client.
        - [RED] Handler tests: the quality-select and season-confirm paths pass `quality_data["movie"]` and `quality_data["series"]` as `lookup`.
        - [GREEN] Implement the single lookup, the optional `lookup` parameters and the handler changes. Remove `SonarrClient.get_seasons` and its three tests (`test_get_seasons`, `_empty`, `_exception`).
    - **Success:** api, services and handlers scoped runs pass, integration tests pass, flake8 and mypy clean, no request to `lookup/tmdb/` or `lookup/tvdb/` remains in `src/` or `tests/`.
    - **Completed:** 2026-11-05
    - **Learnings:**
        - `get_movie` and `get_series` swallow errors and return None, so `add_movie` and `add_series` now report "not found" for a failed lookup. Their outer `except` is reached only by the POST path, so the two `*_outer_exception` tests pass `lookup=` to reach it.
        - `aioresponses` records a request in `.requests` before it matches a mock. Asserting on `.requests` proves that no request went to the old path.
        - `.venv` needs `python-telegram-bot[job-queue]` (APScheduler): without it every integration test errors in `app.job_queue`. Reinstall requirements after merging `origin/development`.
        - In the `services` scoped run `src/services/rate_limit.py` shows 80%: handler tests cover it.
    - **Key Changes:**
        - `src/api/radarr.py`, `src/api/sonarr.py`: `get_movie` and `get_series` do one `lookup?term=` call. `add_movie` and `add_series` take `lookup`. `SonarrClient.get_seasons` is removed.
        - `src/services/media.py`: `add_series` reads seasons from `series["seasons"]`. `add_movie_with_profile` and `add_series_with_profile` take `lookup` and pass it on.
        - `src/bot/handlers/media/handler.py`, `season_picker.py`: pass `quality_data[...]` as `lookup`.
        - Tests: API, service, handler and two integration assertions. `.claude/skills/addarr-testing/references/fixtures.md` no longer lists `get_seasons`.
    - **Notes:** `MediaService.add_series` is the one lookup of a series add. The confirm step passes that result, so a confirmed add makes no lookup. The movie and series dicts in `quality_data` are the lookup results.

### Phase 3: Cards and docs (2 tasks)

**Goal:** The series card shows the real rating and no fake studio, posters load, and the docs say Sonarr v4 is required.

- [ ] **3.1** F044 and F045 search results and cards
    - **Context:**
        - **Why:** Sonarr sends `ratings.value` and `ratings.votes` and no `studio`. The card shows N/A and "Network: AMC (N/A)". `remotePoster` is already a full URL, so the code adds a second prefix.
        - **Architecture:** `MediaService.search_movies` and `search_series` normalize results. `show_result` and `build_result_caption` in `src/bot/handlers/media/formatters.py` render them. Decisions: series card drops studio and shows `Network:`, the movie card keeps `Studio:`, the series rating label is `Rating` (design.md).
        - **Key refs:** `src/services/media.py` `search_movies` (~l.90-125), `search_series` (~l.127-170). `src/bot/handlers/media/formatters.py` (~l.120-155). Tests: `tests/test_services/test_media_service.py` (fixtures with `"studio"` ~l.24-54), `tests/test_handlers/test_media_formatters.py`, `tests/test_handlers/test_media_handler.py` (`test_show_result_tmdb_rating` ~l.1440).
        - **Watch out:** The `ratings` key `"tmdb"` becomes `"value"`, so update every test that reads it. The formatter hard-codes English labels, so no translation key changes. Keep `float()` formatting and the vote count format `{votes:,}`.
    - **Scope:** Service normalization, the card text, and the fixtures these tests touch.
    - **Touches:** `src/services/media.py`, `src/bot/handlers/media/formatters.py`, the three test files above
    - **Action items:**
        - [RED] `search_series` with `ratings: {"votes": 120, "value": 8.1}` returns `ratings` with `value` 8.1 and `votes` 120, and no `studio` key.
        - [RED] `show_result` for a series: caption has `Network: AMC`, no `(N/A)`, no studio, and a `Rating:` line. A movie caption keeps `Studio:`.
        - [RED] `search_movies` and `search_series` with a full `remotePoster` URL and empty `images` return that URL unchanged.
        - [GREEN] Implement the three changes and update the existing tests and fixtures they break.
    - **Success:** services and handlers scoped runs pass, flake8 and mypy clean.

- [ ] **3.2** F043 document "Sonarr v4 required"
    - **Context:**
        - **Why:** Sonarr v3 needs `languageProfileId`. Decided 2026-10-28: document v4, no code change (`src/api/sonarr.py` `add_series` stays).
        - **Architecture:** Docs only.
        - **Key refs:** `README.md` Prerequisites (~l.205), `config_example.yaml` Sonarr section (~l.36), `tests/test_architecture/test_repo_docs.py`.
        - **Watch out:** `config_example.yaml` is also the validation reference: add a comment only, no key.
    - **Scope:** One line in README Prerequisites and one comment in the Sonarr section of `config_example.yaml`.
    - **Touches:** `README.md`, `config_example.yaml`
    - **Action items:**
        - [GREEN] Add "Sonarr v4 (v3 is not supported)" to the README prerequisites and a "Sonarr v4 is required" comment to `config_example.yaml`.
    - **Success:** architecture tests pass, `run.py --validate-i18n` unaffected, `config_example.yaml` still loads.
