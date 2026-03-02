# Issue #82: Expand /music to Support Album and Song Search

> Plan: [plan.md](plan.md)

---

### Phase 1: API Client — Album Search and Selective Monitoring (1 task)

**Goal:** Add album search, track lookup, and album-selective artist add to `LidarrClient`.

- [x] **1.1** Add album search and selective monitoring to LidarrClient
    - **Context:**
        - **Why:** The `/music` command only searches artists. Need `search_albums()` for combined search results and `add_artist()` must support `albums_to_monitor` so users can selectively monitor specific albums instead of all.
        - **Architecture:** New methods on `LidarrClient` following existing `search()` / `add_artist()` patterns. Uses `_request()` helper from `BaseApiClient`. Album lookup uses same API version (`/api/v1/`).
        - **Key refs:** `src/api/lidarr.py:45` (`search()` method — pattern for `search_albums()`), `src/api/lidarr.py:94` (`add_artist()` — modify payload), `src/api/base.py` (`BaseApiClient._request`)
        - **Watch out:** `add_artist()` signature change must be backwards-compatible — default `albums_to_monitor=None` preserves existing behavior. When `albums_to_monitor` is provided, set `addOptions.monitor` to `"none"` and add `addOptions.albumsToMonitor` array. Album lookup endpoint: `GET /api/v1/album/lookup?term={query}`. Track data lives in album response's `media` array but may not always include track names (best-effort).
    - **Scope:** `search_albums()`, `get_album_tracks()` methods; modify `add_artist()` payload; sample data fixtures
    - **Touches:** `src/api/lidarr.py`, `tests/fixtures/sample_data.py`, `tests/test_api/test_lidarr.py`
    - **Action items:**
        - [RED] Tests for `search_albums()`: success returns album list, empty results returns `[]`, exception returns `[]`
        - [RED] Tests for `get_album_tracks()`: success returns track data from album's `media` array, album not found returns `[]`, exception returns `[]`
        - [RED] Tests for `add_artist()` with `albums_to_monitor=["album-id-1", "album-id-2"]`: verify POST payload has `addOptions.monitor: "none"` and `addOptions.albumsToMonitor: [...]`
        - [RED] Test `add_artist()` without `albums_to_monitor` (existing behavior): verify POST payload has `addOptions.monitor` from config (not `"none"`) and no `albumsToMonitor` key
        - [GREEN] Add `LIDARR_ALBUM_SEARCH_RESULTS` sample data to `tests/fixtures/sample_data.py` — list of album dicts with `foreignAlbumId`, `title`, `artist` (nested), `images`, `releaseDate`
        - [GREEN] Add `LIDARR_ALBUM_WITH_TRACKS` sample data — single album dict with `media` array containing track listings (`mediumNumber`, `mediumName`, `mediumFormat`, tracks array)
        - [GREEN] Implement `search_albums(term)` — `GET /api/v1/album/lookup?term={term}`, same error handling pattern as `search()`
        - [GREEN] Implement `get_album_tracks(foreign_album_id)` — lookup album, extract and return track info from `media` array; return `[]` if not found or no track data
        - [GREEN] Modify `add_artist()` — add `albums_to_monitor: List[str] = None` param; when provided, set `addOptions.monitor` to `"none"` and add `addOptions.albumsToMonitor` list to payload
    - **Success:** All existing Lidarr tests pass unchanged + new tests pass. `pytest tests/test_api/test_lidarr.py -v` green. `flake8 src/api/lidarr.py tests/test_api/test_lidarr.py` clean.
    - **Completed:** 2026-03-02
    - **Learnings:**
        - `_request()` passes endpoint path directly into URL string — use simple terms in tests to avoid URL encoding mismatches with `aioresponses`
        - Album lookup endpoint is `album/lookup?term={query}` (same API version `/api/v1/`)
        - Track data extraction from `media` array needs double iteration: medium → tracks (best-effort, tracks key may be absent)
        - `add_artist()` signature change is backwards-compatible via `albums_to_monitor: List[str] = None` default
    - **Key Changes:**
        - Added `search_albums(term)` and `get_album_tracks(foreign_album_id)` to `src/api/lidarr.py`
        - Modified `add_artist()` to accept `albums_to_monitor` param — when provided, sets `addOptions.monitor` to `"none"` and includes `addOptions.albumsToMonitor` array
        - Added `LIDARR_ALBUM_SEARCH_RESULTS` and `LIDARR_ALBUM_WITH_TRACKS` sample data to `tests/fixtures/sample_data.py`
        - Added 9 new tests across 3 test classes: `TestLidarrSearchAlbums` (3), `TestLidarrGetAlbumTracks` (4), `TestLidarrAddArtistAlbumMonitor` (2)
    - **Notes:** All 61 Lidarr tests pass (52 existing + 9 new). Flake8 clean.

---

### Phase 2: Service Layer — Combined Search and Album-Aware Add (1 task)

**Goal:** Extend `MediaService` to return combined artist+album+song results and pass `albums_to_monitor` through to `LidarrClient`.

- [x] **2.1** Add combined music search and album-aware add to MediaService
    - **Context:**
        - **Why:** Handler needs a unified result list with `music_type` discriminator (`"artist"`, `"album"`, `"song"`) so it can route selections differently. Service must also pass `albums_to_monitor` through to `LidarrClient.add_artist()`.
        - **Architecture:** `search_music()` uses `asyncio.gather()` to run artist search + album search in parallel. Results are merged with ordering: artists first, then albums, then songs. Album result IDs are prefixed with `album:` (e.g., `album:b1ae2a0f-...`) for handler routing — handler strips prefix before calling service. Song results are extracted from album track data (best-effort). `add_music_with_profile()` gains optional `albums_to_monitor` param.
        - **Key refs:** `src/services/media.py:179` (`search_music()` — rewrite for combined search), `src/services/media.py:406` (`add_music_with_profile()` — add param), `src/services/media.py:366` (`add_music()` — unchanged)
        - **Watch out:** Need `import asyncio` for `gather()`. Artist results must get `music_type: "artist"` added without changing other fields (backwards-compatible). Album results need `music_type`, `artist_id`, `album_id` fields for handler routing. Song results only appear when album track data matches the query — gracefully absent otherwise. Album IDs in result list must use `album:` prefix.
    - **Scope:** Modify `search_music()`, `add_music_with_profile()`; add `get_artist_albums()`
    - **Touches:** `src/services/media.py`, `tests/test_services/test_media_service.py`
    - **Action items:**
        - [RED] Test `search_music()` returns combined results with `music_type` field on each result (`"artist"`, `"album"`, or `"song"`)
        - [RED] Test album result IDs are prefixed with `album:` (e.g., `album:some-foreign-id`)
        - [RED] Test song results appear when album track data contains a track matching the query — result has `music_type: "song"`, `album_id`, `artist_id`
        - [RED] Test song results are gracefully absent when album responses have no track data in `media` array
        - [RED] Test artist-only results returned when album search returns empty; album-only when artist search returns empty
        - [RED] Test existing artist result fields are preserved (backwards compatibility) — `id`, `title`, `overview`, `poster`, etc. all still present
        - [RED] Test result ordering: artists first, then albums, then songs
        - [RED] Test `add_music_with_profile()` passes `albums_to_monitor` to `lidarr.add_artist()`
        - [RED] Test `add_music_with_profile()` without `albums_to_monitor` still calls `add_artist()` without it (backwards compatible)
        - [RED] Test `get_artist_albums(artist_id)` returns normalized album list from Lidarr
        - [RED] Test `get_artist_albums()` returns `[]` on exception
        - [GREEN] Add `import asyncio` to `src/services/media.py`
        - [GREEN] Modify `search_music()` — use `asyncio.gather()` for parallel artist + album search, normalize album results (add `music_type`, `artist_id`, `album_id`, prefix ID with `album:`), extract song matches from track data, merge with ordering: artists → albums → songs
        - [GREEN] Modify `add_music_with_profile()` — accept `albums_to_monitor: List[str] = None` param and pass through to `self.lidarr.add_artist()`
        - [GREEN] Add `get_artist_albums(artist_id)` — call `lidarr.search_albums()` or artist album endpoint, return normalized list of `{album_id, title, release_date}` dicts
    - **Success:** All existing service tests pass + new tests pass. `pytest tests/test_services/test_media_service.py -v` green. `flake8 src/services/media.py` clean.
    - **Completed:** 2026-03-02
    - **Learnings:**
        - `asyncio.gather()` works seamlessly with `AsyncMock` in tests — no special handling needed
        - Song extraction is inline (from album search results' `media` array), no extra API calls needed
        - Existing `test_search_music_success` test passed unchanged because conftest default `search_albums=AsyncMock(return_value=[])` means no album results, and `music_type: "artist"` is an additive field
        - `add_music_with_profile()` uses `**kwargs` pattern to only pass `albums_to_monitor` when provided, keeping backwards compatibility clean
    - **Key Changes:**
        - Rewrote `search_music()` in `src/services/media.py` to use `asyncio.gather()` for parallel artist+album search, with song extraction from track data
        - Modified `add_music_with_profile()` to accept and pass through `albums_to_monitor`
        - Added `get_artist_albums(artist_id)` returning normalized `{album_id, title, release_date}` dicts
        - Updated `tests/test_services/conftest.py` with `search_albums` and `get_album_tracks` mocks
        - Added 13 new tests across 3 test classes: `TestSearchMusicCombined` (8), `TestAddMusicWithProfileAlbums` (2), `TestGetArtistAlbums` (3)
    - **Notes:** All 106 service tests pass (93 existing + 13 new). Flake8 clean. Artist results now include `music_type: "artist"` field — handler code in Phase 3 should expect this.

---

### Phase 3: Handler, Keyboards, and State — Album Picker UI (1 task)

**Goal:** Wire up the complete album selection flow: new state, keyboard builders, handler methods, translation keys, and list view emoji.

- [x] **3.1** Add ALBUM_SELECT state, keyboards, and handler methods
    - **Context:**
        - **Why:** Users need to see combined results with type indicators (artist/album/song emoji), and after selecting an artist, choose between monitoring all albums or picking specific ones via an album picker.
        - **Architecture:** New `ALBUM_SELECT = 5` state in `states.py`. Two new keyboard builders in `keyboards.py`: `get_album_monitor_mode_keyboard()` for the "All Albums" / "Pick Specific" prompt, and `get_album_selection_keyboard()` mirroring the season picker toggle/confirm pattern. Three new handler methods: `handle_album_monitor_mode()`, `handle_album_selection()`, `handle_album_confirm()`. State machine flow:
            - **Artist path:** quality → monitor mode prompt (ALBUM_SELECT) → "All" adds directly (END) or "Pick" → album picker (ALBUM_SELECT) → confirm → END
            - **Album path:** quality → add with album pre-selected → END
            - **Song path:** quality → add artist with containing album monitored → END
        - **Key refs:** `src/bot/states.py:16` (`SEASON_SELECT = 4` — add `ALBUM_SELECT = 5` after), `src/bot/handlers/media.py:802` (`handle_season_selection` — pattern to mirror for album picker), `src/bot/handlers/media.py:709` (`handle_quality_selection` — branch point for music type), `src/bot/keyboards.py:295` (`get_search_results_list_keyboard` — emoji map to update), `src/bot/handlers/media.py:34` (state constants — add ALBUM_SELECT), `src/bot/handlers/media.py:54` (ConversationHandler state map — register ALBUM_SELECT)
        - **Watch out:**
            - ConversationHandler state map needs ALBUM_SELECT with both `album_monitor_mode_` and `albumsel_` callback patterns
            - Season picker keyboard is built inline in handler (lines 873-910) — album picker should use centralized `keyboards.py` function instead
            - List view emoji should show per-result type: 🎤 for artist, 💿 for album, 🎵 for song (currently generic 🎵 for all music)
            - `handle_selection()` must detect `album:` prefix in result ID, store `music_type`, `artist_id`, `album_id` in `user_data`
            - `handle_quality_selection()` must branch for music: artist → show monitor mode prompt, album/song → add with pre-selected album
            - Callback patterns: `album_monitor_mode_all`, `album_monitor_mode_pick`, `albumsel_{foreignAlbumId}`, `albumsel_all`, `albumsel_future`, `albumsel_monitor_all`, `albumsel_confirm`
    - **Scope:** State definition, keyboard builders, handler methods, caption updates, translation keys (10 locales + template), list view emoji, handler conftest update
    - **Touches:** `src/bot/states.py`, `src/bot/keyboards.py`, `src/bot/handlers/media.py`, `tests/test_handlers/test_media_handler.py`, `tests/test_handlers/conftest.py`, `translations/addarr.*.yml` (10 files + template)
    - **Action items:**
        - [RED] Test `States.ALBUM_SELECT == 5`
        - [RED] Tests for `get_album_monitor_mode_keyboard()`: returns keyboard with "All Albums" and "Pick Specific" buttons, correct callback data
        - [RED] Tests for `get_album_selection_keyboard()`: basic layout with album buttons, selected albums show checkmarks, `albumsel_all` toggles all, `albumsel_future` toggle, `albumsel_monitor_all` button present, `albumsel_confirm` button present
        - [RED] Tests for `_build_result_caption()` with `music_type: "album"` — shows album-specific format (artist name, release date)
        - [RED] Tests for `handle_selection()` with album result: detects `album:` prefix, stores `music_type`, `artist_id`, `album_id` in `user_data`
        - [RED] Tests for `handle_selection()` with song result: stores routing data + message indicates "Adding album X containing song Y"
        - [RED] Tests for `handle_quality_selection()` with music artist: returns `ALBUM_SELECT` and shows monitor mode prompt
        - [RED] Tests for `handle_quality_selection()` with music album/song: adds with pre-selected album, returns `END`
        - [RED] Tests for `handle_album_monitor_mode()`: "all" calls add and returns `END`, "pick" calls `get_artist_albums` and shows picker staying in `ALBUM_SELECT`
        - [RED] Tests for `handle_album_selection()`: toggle individual album, toggle all, toggle future mode, `monitor_all` auto-confirms, cancel returns `END`
        - [RED] Tests for `handle_album_confirm()`: passes `albums_to_monitor` list to service, `monitor_all` passes `None`, error handling returns `END`
        - [GREEN] Add `ALBUM_SELECT = 5` to `src/bot/states.py`
        - [GREEN] Add `get_album_monitor_mode_keyboard()` to `src/bot/keyboards.py` — two buttons: "All Albums" (`album_monitor_mode_all`) and "Pick Specific Albums" (`album_monitor_mode_pick`)
        - [GREEN] Add `get_album_selection_keyboard(albums, selected_albums, future_mode)` to `src/bot/keyboards.py` — toggle buttons for each album with checkmarks, monitor_all, all, future, confirm, cancel
        - [GREEN] Add translation keys to all 10 locale files + template: `AlbumMonitorAll`, `AlbumMonitorPick`, `AlbumSelectPrompt`, `AlbumConfirm`, `AddingAlbumContainingSong`, `FutureAlbums`
        - [GREEN] Update `_build_result_caption()` — when `music_type` is `"album"`, show album title, artist name, release date; when `"song"`, show song name + album
        - [GREEN] Update `get_search_results_list_keyboard()` emoji — when `search_type == "music"`, use per-result `music_type` for emoji: 🎤 artist, 💿 album, 🎵 song
        - [GREEN] Modify `handle_selection()` — detect `album:` prefix in selected ID, strip prefix, store `music_type`, `artist_id`, `album_id` in `context.user_data`
        - [GREEN] Modify `handle_quality_selection()` — after quality selected for music: if `music_type == "artist"`, show monitor mode keyboard (return `ALBUM_SELECT`); if album/song, call `_add_media_with_profile` with pre-selected album (return `END`)
        - [GREEN] Add `handle_album_monitor_mode()` — "all" calls add directly (return `END`), "pick" fetches artist albums via `media_service.get_artist_albums()`, shows album picker keyboard (return `ALBUM_SELECT`)
        - [GREEN] Add `handle_album_selection()` — toggle individual albums, toggle all, future mode, monitor_all auto-confirms, cancel exits
        - [GREEN] Add `handle_album_confirm()` — collect selected `albums_to_monitor` list, call `media_service.add_music_with_profile()` with it
        - [GREEN] Register `ALBUM_SELECT` state in ConversationHandler state map with `CallbackQueryHandler` for `album_monitor_mode_` and `albumsel_` patterns
        - [GREEN] Update `ALBUM_SELECT = 5` constant at module level in `media.py` (line 34 area)
        - [GREEN] Add `get_artist_albums` mock to handler conftest's `mock_media_service` fixture
    - **Success:** Full conversation flow works for all three paths (artist→mode→add, artist→mode→picker→confirm, album→quality→add, song→quality→add). All existing tests pass + new tests pass. `pytest --tb=short -q` all green. `flake8 .` clean.
    - **Completed:** 2026-03-02
    - **Learnings:**
        - `handle_selection()` needs to strip `album:` prefix before API calls but keep routing data (music_type, artist_id, album_id) in user_data for downstream handlers
        - Music quality selection branching works cleanly: artist → ALBUM_SELECT (monitor mode), album/song → add directly with pre-selected album via `albums_to_monitor`
        - Album selection keyboard mirrors season picker pattern but uses centralized `keyboards.py` functions (unlike season picker which builds inline)
        - Per-result emoji in list view works via `music_type` field on each result dict — falls back to generic emoji when field absent (backwards compatible)
        - ConversationHandler ALBUM_SELECT state needs both `album_monitor_mode_` and `albumsel_` patterns since the same state handles two sub-flows
    - **Key Changes:**
        - Added `ALBUM_SELECT = 5` to `src/bot/states.py` and `src/bot/handlers/media.py`
        - Added `get_album_monitor_mode_keyboard()` and `get_album_selection_keyboard()` to `src/bot/keyboards.py`
        - Modified `handle_selection()` to detect `album:` prefix, strip for API calls, store music_type/artist_id/album_id routing data
        - Modified `handle_quality_selection()` to branch for music: artist → ALBUM_SELECT, album/song → add with pre-selected album
        - Added `handle_album_monitor_mode()`, `handle_album_selection()`, `handle_album_confirm()` handler methods
        - Updated `_build_result_caption()` for album (artist name, release date) and song (album title, artist) types
        - Updated `get_search_results_list_keyboard()` for per-result music_type emoji (🎤 artist, 💿 album, 🎵 song)
        - Registered `ALBUM_SELECT` state in ConversationHandler with both callback patterns
        - Added `get_artist_albums` mock to handler conftest's `mock_media_service`
        - Added translation keys (AlbumMonitorAll, AlbumMonitorPick, AlbumSelectPrompt, AlbumConfirm, FutureAlbums) to all 10 locale files + template
        - Added 15 keyboard tests + 19 handler tests = 34 new tests
    - **Notes:** All 1220 tests pass (1186 existing + 34 new). Flake8 clean. `--validate-i18n` has a pre-existing Windows encoding issue (cp1252/colorama) unrelated to these changes — YAML files validated via Python yaml.safe_load.

---

## Verification

```bash
# Phase 1
pytest tests/test_api/test_lidarr.py -v

# Phase 2
pytest tests/test_services/test_media_service.py -v

# Phase 3
pytest tests/test_handlers/test_media_handler.py -v

# Full suite
pytest --tb=short -q
pytest --cov=src --cov-report=term-missing

# Lint
flake8 .

# Translation validation
python run.py --validate-i18n
```
