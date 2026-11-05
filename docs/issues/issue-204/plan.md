# Issue 204: Radarr and Sonarr API calls miss data and hit missing endpoints

**Goal:** History, queue, missing, cutoff and calendar rows show the movie or series name. The history filter tabs show the matching events. Each add makes one lookup and no failing call. The series card shows the real rating and no fake studio. Posters load.

**Issue:** https://github.com/Krypt0nBull3t/Addarr/issues/204 (F040 to F045)

**Branch:** `fix/204-servarr-api-spec-mismatch` (from `origin/development` at `cf51f57`)

Design decisions: see `design.md` (approved).

## Context and root causes

Found by reading the source at `cf51f57`. The line numbers in the issue have moved.

- **F040** The requests in `src/api/sonarr.py` (`get_missing`, `get_queue`, `get_cutoff_unmet`, `get_calendar`, `get_history`) and `src/api/radarr.py` (`get_queue`, `get_history`) send no include flag. The spec default is false, so the records carry no `series`, `episode` or `movie`. `MediaService._normalize_radarr_history` and `_normalize_sonarr_history` (`src/services/media.py`) then read empty dicts. Radarr `wanted/missing`, `wanted/cutoff` and `calendar` return movie objects, so they need no flag.
- **F041** `get_history_items_keyboard` (`src/bot/keyboards.py`) names the filters `grabbed`, `downloadFolderImported`, `downloadFailed`. `get_history` in both API clients puts that string in `eventType`. The spec wants an int array: grabbed 1, downloadFolderImported 3, downloadFailed 4.
- **F042** `RadarrClient.get_movie` and `SonarrClient.get_series` call the missing path `movie/lookup/tmdb/{id}` or `series/lookup/tvdb/{id}` first (404 and an ERROR log), then fall back to `lookup?term=`. `MediaService.add_series` then calls `get_seasons` (another lookup). `SonarrClient.add_series` and `RadarrClient.add_movie` look up again. One series add makes 1 failing and 3 identical lookups.
- **F043** Sonarr v3 needs `languageProfileId`. Decision: document "Sonarr v4 required", no code change.
- **F044** `search_series` in `src/services/media.py` reads `ratings.tmdb.value` and `studio`. Sonarr sends `ratings.value` and `ratings.votes`, and no `studio`. The formatter `show_result` in `src/bot/handlers/media/formatters.py` then shows N/A and "Network: AMC (N/A)".
- **F045** `remotePoster` is already a full URL. `search_movies` and `search_series` add a second prefix when `images` has no poster.

## Files

- Modify `src/api/base.py` (history event map)
- Modify `src/api/sonarr.py`, `src/api/radarr.py` (F040, F041, F042)
- Modify `src/services/media.py` (F042, F044, F045)
- Modify `src/bot/handlers/media/handler.py` (F042: pass the lookup result to the add)
- Modify `src/bot/handlers/media/season_picker.py` (F042: pass the lookup result to the add)
- Modify `src/bot/handlers/media/formatters.py` (F044)
- Modify `README.md`, `config_example.yaml` (F043)
- Tests: `tests/test_api/test_sonarr.py`, `tests/test_api/test_radarr.py`, `tests/test_services/test_media_service.py`, `tests/test_handlers/test_media_formatters.py`, `tests/test_handlers/test_media_handler.py`, `tests/test_handlers/test_history_handler.py` (only if a call signature changes)

## Tasks

### Task 1: F040 include flags (7 requests)

- Tests first (RED), in `test_sonarr.py` and `test_radarr.py`. Each asserts that the request URL carries the flag. Update the existing mocked URLs to the new query strings.
  - Sonarr `wanted/missing`: `&includeSeries=true`. `wanted/cutoff`: `&includeSeries=true`. `calendar`: `&includeSeries=true`. `queue`: `&includeSeries=true&includeEpisode=true`. `history`: `&includeSeries=true&includeEpisode=true`.
  - Radarr `queue`: `&includeMovie=true`. `history`: `&includeMovie=true`.
- Implement: append the flags in the 7 endpoint strings.

### Task 2: F041 history event types

- Add to `src/api/base.py` `HISTORY_EVENT_TYPES = {"grabbed": 1, "downloadFolderImported": 3, "downloadFailed": 4}`.
- Tests first: `test_get_history_with_event_type` in both API test files, for `grabbed`, `downloadFolderImported` and `downloadFailed`, asserts the URL has `eventType=1`, `3` and `4`. An unknown name returns `[]` (the existing exception path logs the error).
- Implement: `endpoint += f"&eventType={HISTORY_EVENT_TYPES[event_type]}"` in both clients. Keyboard, callbacks and handler stay the same.

### Task 3: F042 one lookup

- Tests first:
  - `test_radarr.py`, `test_sonarr.py`: `get_movie` and `get_series` request only `lookup?term=tmdb:`/`tvdb:`, never the `lookup/tmdb/` or `lookup/tvdb/` path (the old mocks of those paths go away). `add_movie` and `add_series` with a `lookup` dict make no lookup request and POST the dict's `tmdbId`/`tvdbId` and title. Without `lookup` they still look up.
  - `test_media_service.py`: `MediaService.add_series("81189")` makes one lookup request and its `seasons` come from the series dict. `add_series_with_profile` and `add_movie_with_profile` pass `lookup` on to the API client.
  - `test_media_handler.py`: the quality-select and season-confirm paths pass `quality_data["movie"]` / `quality_data["series"]` as `lookup`.
- Implement:
  - `get_movie` and `get_series`: one `lookup?term=` call, return the first result.
  - Remove `SonarrClient.get_seasons` and its three tests (no other caller).
  - `MediaService.add_series`: `seasons = series.get("seasons")`, with the existing "No seasons found" message when empty.
  - `add_movie(..., lookup: Optional[Dict] = None)` and `add_series(..., lookup=None)`: skip the lookup when `lookup` is given. `MediaService.add_movie_with_profile` and `add_series_with_profile` take `lookup=None` and pass it on.
  - `handler._add_media_with_profile` takes `lookup` and `handle_quality_selection` passes `quality_data.get(media_type)`; `season_picker` passes `quality_data.get("series")`. `_add_media_with_profile` adds the keyword only when it is not None, so `add_music_with_profile` keeps its signature.

### Task 4: F044 and F045 service and card

- Tests first, in `test_media_service.py` and `test_media_formatters.py`:
  - `search_series`: a Sonarr result with `ratings: {"votes": 120, "value": 8.1}` gives `ratings` `{"value": 8.1, "votes": 120}`. No `studio` key in the series result.
  - `show_result` for a series: the caption has "Network: AMC", no "(N/A)", no studio, and a "Rating:" line. A movie still has "Studio:".
  - `search_movies` and `search_series`: `remotePoster` full URL with `images` empty comes back unchanged.
- Implement: use `remotePoster` as is in both; `search_series` reads `ratings.value` and `ratings.votes` and drops `studio`; the formatter shows `Network: <network>` for a series, `Studio:` for a movie, and `Rating: x/10 (n votes)` for `ratings.value`.
- Update fixtures in these tests to the spec shape where the test touches them.

### Task 5: F043 docs

- `README.md` Prerequisites: add "Sonarr v4 (v3 is not supported)". `config_example.yaml` Sonarr section: comment "Sonarr v4 is required".
- Check `tests/test_architecture/test_repo_docs.py` and `config` validation still pass.

## Verification

- Scoped runs per task (`api`, `services`, `handlers`), then the preflight (flake8, mypy, translations, 100% coverage gate, integration, architecture).
- create-pr step 1 runs `arr-api-contract-checker` on the changed requests.
- Search for other callers of `get_seasons`, `get_movie` and `get_series` before the removal (graph and grep).
