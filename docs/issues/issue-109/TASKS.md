# Issue #109: External Links in Search Results

**Goal:** Add clickable IMDB/TMDB/TVDB/MusicBrainz links to search result captions.

**Plan:** See [plan.md](plan.md) for full context and design decisions.

---

### Phase 1: External Links Feature (2 tasks)

**Goal:** Surface external IDs from API responses and render them as clickable links in search result captions.

- [x] **1.1** Add `external_ids` to search result normalization
    - **Context:** See plan.md Tasks 1-3. Key refs: `src/services/media.py:108-267` (three search methods), `tests/fixtures/sample_data.py` (add `imdbId` to Radarr/Sonarr fixtures)
    - **Watch out:** `tmdbId` is already used as movie `id` — `external_ids.tmdb` stores the same value but keeps the formatter decoupled from ID semantics. Sonarr series may lack `imdbId` (must be `None`, not absent). Song `external_ids` uses the parent album's `foreignAlbumId`.
    - **Scope:** Add `external_ids` dict to movie, series, artist, album, and song normalization. Update fixtures with `imdbId` fields.
    - **Touches:** `src/services/media.py`, `tests/fixtures/sample_data.py`, `tests/test_services/test_media_service.py`
    - **Action items:**
        - [RED] Write tests asserting `external_ids` present in normalized movie results (imdb + tmdb)
        - [RED] Write tests asserting `external_ids` present in normalized series results (tvdb + optional imdb)
        - [RED] Write tests asserting `external_ids` present in normalized artist/album/song results (musicbrainz)
        - [GREEN] Add `external_ids` to movie normalization in `search_movies`
        - [GREEN] Add `external_ids` to series normalization in `search_series`
        - [GREEN] Add `external_ids` to artist/album/song normalization in `search_music`
        - [GREEN] Add `imdbId` to Radarr and Sonarr sample data fixtures
    - **Success:** `pytest tests/test_services/test_media_service.py -v` passes, all normalized results include correct `external_ids`
    - **Completed:** 2026-03-09
    - **Learnings:** `tmdbId` is an int in Radarr responses, not a string — stored as-is in `external_ids.tmdb` (consistent with raw API). `imdbId` is optional in both Radarr and Sonarr responses.
    - **Key Changes:** Added `external_ids` dict to all 5 normalization paths in `src/services/media.py`. Added `imdbId` to Radarr/Sonarr sample data fixtures. Added 7 tests covering all media types + missing ID edge cases.
    - **Notes:** None

- [x] **1.2** Build external links line in formatter
    - **Context:** See plan.md Task 4. Key refs: `src/bot/handlers/media/formatters.py:23-119` (`build_result_caption`), `tests/test_handlers/test_media_formatters.py` (existing formatter tests)
    - **Watch out:** Telegram Markdown v1 link syntax is `[text](url)`. Links line goes before the result counter. `_build_external_links` must gracefully return empty string when `external_ids` is missing or empty. MusicBrainz URL differs for artist vs album/song.
    - **Scope:** Add `_build_external_links()` helper, integrate into all three caption branches (album, song, movie/series).
    - **Touches:** `src/bot/handlers/media/formatters.py`, `tests/test_handlers/test_media_formatters.py`
    - **Action items:**
        - [RED] Write tests for `_build_external_links`: movie (IMDB+TMDB), series (TVDB+IMDB), series TVDB-only, album (MusicBrainz release-group), artist (MusicBrainz artist), song, no external_ids, empty external_ids
        - [RED] Write tests for `build_result_caption` with external_ids (movie, album, song captions include links line)
        - [GREEN] Implement `_build_external_links()` helper
        - [GREEN] Integrate into album, song, and movie/series caption branches
    - **Success:** `pytest tests/test_handlers/test_media_formatters.py -v` passes, captions contain clickable Markdown links in correct format
    - **Completed:** 2026-03-09
    - **Learnings:** Links line uses `\n` prefix for visual separation from preceding content. All 9 `_build_external_links` scenarios covered including edge cases (no key, empty dict, all None values).
    - **Key Changes:** Added `_build_external_links()` helper to `formatters.py`. Integrated into all 3 caption branches (album, song, movie/series). Added 12 new tests (9 for helper, 3 for caption integration).
    - **Notes:** None
