# Issue #82: Expand /music to Support Album and Song Search

## Context

The `/music` command currently only searches for artists via Lidarr's `artist/lookup` endpoint. When a user adds an artist, Lidarr monitors **all** their albums based on the global `monitorOption` config setting. Users who want a specific album or song have no way to narrow down.

This feature expands `/music` to query artists, albums, and tracks in parallel, display combined results with type indicators, and offer an album picker (mirroring the season picker) for selective monitoring.

## Design Decisions

1. **New state `ALBUM_SELECT = 5`** — Dedicated state rather than reusing `SEASON_SELECT`. Album picker has different data shapes (foreignAlbumId strings vs integer season numbers) and different Lidarr API semantics.

2. **`addOptions.albumsToMonitor` approach** — When adding an artist with selective albums, set `addOptions.monitor` to `"none"` and pass `addOptions.albumsToMonitor` as an array of foreignAlbumId strings. Single POST — cleaner than adding then PUTting individual albums.

3. **Album result IDs prefixed with `album:`** — e.g., `album:b1ae2a0f-...` to distinguish from artist IDs (`f59c5520-...`) in the same result list. The handler strips the prefix before calling the service.

4. **Song discovery is best-effort** — Lidarr has no dedicated track search. We search albums and check track listings in the response's `media` array. If track data isn't available, only artist and album results are shown.

5. **Artist selection adds monitoring mode prompt** — After quality profile, artists get a "All Albums" / "Pick Specific Albums" choice before the album picker. Albums/songs skip this and go straight to add (with the relevant album pre-selected).

## State Machine (Updated Music Flow)

```
/music → SEARCHING → SELECTING → QUALITY_SELECT
                                      │
                              ┌───────┴────────┐
                              │ music_type?     │
                              ├─────┬─────┬────┘
                         artist   album   song
                              │     │      │
                     ALBUM_SELECT   │   add artist + album
                     (mode prompt)  │   "Adding album X
                      all │ pick   │    containing Y"
                       │    │      │      → END
                       │    └──┬───┘
                       │       │
                       │    ALBUM_SELECT (picker)
                       │       │
                       │    confirm → add with albums_to_monitor
                       │       │
                       └───┬───┘
                           │
                          END
```

**Artist path:** quality → monitor mode prompt → "All Albums" (add directly) or "Pick Specific" → album picker → confirm
**Album path:** quality → album picker (pre-selected) → confirm
**Song path:** quality → add artist with containing album monitored (auto, no picker)

## Files Changed

| File | Action | Description |
|------|--------|-------------|
| `src/bot/states.py` | Edit | Add `ALBUM_SELECT = 5` |
| `src/api/lidarr.py` | Edit | Add `search_albums()`, `get_album_tracks()`; modify `add_artist()` for `albums_to_monitor` param |
| `src/services/media.py` | Edit | Modify `search_music()` for combined search; modify `add_music_with_profile()` for album param; add `get_artist_albums()` |
| `src/bot/keyboards.py` | Edit | Add `get_album_monitor_mode_keyboard()`, `get_album_selection_keyboard()` |
| `src/bot/handlers/media.py` | Edit | Add `ALBUM_SELECT` state + handlers; modify `handle_selection()`, `handle_quality_selection()`, `_build_result_caption()`; update list view emoji |
| `tests/fixtures/sample_data.py` | Edit | Add `LIDARR_ALBUM_SEARCH_RESULTS` |
| `tests/test_api/test_lidarr.py` | Edit | Tests for new API methods |
| `tests/test_services/test_media_service.py` | Edit | Tests for combined search, album-aware add |
| `tests/test_handlers/conftest.py` | Edit | Add `get_artist_albums` to mock |
| `tests/test_handlers/test_media_handler.py` | Edit | Tests for album picker flow |
| `translations/addarr.*.yml` (10 files + template) | Edit | New keys for album picker |

---

## Phase 1: API Client — Album Search and Selective Monitoring (1 task)

**Goal:** Add album search and album-selective artist add to `LidarrClient`.

- [ ] **1.1** Add album search and selective monitoring to LidarrClient
    - **Context:**
        - **Why:** Need `search_albums()` for combined search, and `add_artist()` must support `albums_to_monitor` for selective monitoring
        - **Architecture:** New methods on `LidarrClient` following existing `search()` / `add_artist()` patterns. Uses `_request()` helper from `BaseApiClient`.
        - **Key refs:** `src/api/lidarr.py:28` (search method), `src/api/lidarr.py:94` (add_artist), `src/api/base.py` (BaseApiClient._request)
        - **Watch out:** `add_artist()` signature change must be backwards-compatible (default `albums_to_monitor=None` preserves existing behavior). Album lookup uses same API version (`/api/v1/`).
    - **Scope:** `search_albums()`, `get_album_tracks()` methods; modify `add_artist()` payload; sample data
    - **Touches:** `src/api/lidarr.py`, `tests/fixtures/sample_data.py`, `tests/test_api/test_lidarr.py`
    - **Action items:**
        - [RED] Tests for `search_albums()`: success (returns albums), empty results, exception handling
        - [RED] Tests for `get_album_tracks()`: success (returns track data from album lookup), not found, exception
        - [RED] Tests for `add_artist()` with `albums_to_monitor`: verify payload has `monitor: "none"` + `albumsToMonitor` array
        - [RED] Test `add_artist()` without `albums_to_monitor` still works unchanged
        - [GREEN] Add `LIDARR_ALBUM_SEARCH_RESULTS` and `LIDARR_ALBUM_WITH_TRACKS` sample data (album with `media` array containing track listings)
        - [GREEN] Implement `search_albums()` — `GET /api/v1/album/lookup?term={query}`
        - [GREEN] Implement `get_album_tracks()` — lookup album by foreignAlbumId, return track info from `media` array (best-effort: data may not include track names depending on Lidarr version)
        - [GREEN] Modify `add_artist()` — add `albums_to_monitor: List[str] = None` param, conditionally set `addOptions.monitor` to `"none"` and include `albumsToMonitor`
    - **Success:** All existing Lidarr tests pass + new tests pass. `flake8 .` clean.

---

## Phase 2: Service Layer — Combined Search and Album-Aware Add (1 task)

**Goal:** Extend `MediaService` to return combined artist+album results and support album-selective adds.

- [ ] **2.1** Add combined music search and album-aware add to MediaService
    - **Context:**
        - **Why:** Handler needs a unified result list with `music_type` discriminator, and must pass `albums_to_monitor` through to LidarrClient
        - **Architecture:** `search_music()` uses `asyncio.gather()` for parallel artist+album search. Album result IDs prefixed with `album:` for handler routing. `add_music_with_profile()` gains optional `albums_to_monitor` param.
        - **Key refs:** `src/services/media.py:179` (search_music), `src/services/media.py:406` (add_music_with_profile), `src/services/media.py:366` (add_music)
        - **Watch out:** `asyncio` import needed for `gather()`. Album results must include `music_type`, `artist_id`, `album_id` fields for handler routing. Existing artist result format must be preserved (add `music_type: "artist"` without changing other fields).
    - **Scope:** Modify `search_music()`, `add_music_with_profile()`; add `get_artist_albums()`
    - **Touches:** `src/services/media.py`, `tests/test_services/test_media_service.py`
    - **Action items:**
        - [RED] Test `search_music()` returns combined artist+album results with `music_type` field
        - [RED] Test album result IDs are prefixed `album:`
        - [RED] Test song results: when album track data matches query, `music_type: "song"` results with `album_id` and `artist_id`
        - [RED] Test song results gracefully absent when no track data in album responses
        - [RED] Test artists-only when no album results; albums-only when no artist results
        - [RED] Test existing artist result fields are preserved (backwards compatibility)
        - [RED] Test `add_music_with_profile()` passes `albums_to_monitor` to client
        - [RED] Test `add_music_with_profile()` without albums still works unchanged
        - [RED] Test `get_artist_albums()` returns normalized album list
        - [RED] Test `get_artist_albums()` returns [] on error
        - [GREEN] Modify `search_music()` — parallel search via `asyncio.gather`, normalize album results, extract song matches from track data (best-effort), merge with ordering: artists → albums → songs
        - [GREEN] Modify `add_music_with_profile()` — accept and pass through `albums_to_monitor`
        - [GREEN] Add `get_artist_albums()` — fetch albums for artist by ID
    - **Success:** All existing service tests pass + new tests pass. `flake8 .` clean.

---

## Phase 3: Handler, Keyboards, and State — Album Picker UI (1 task)

**Goal:** Wire up the complete album selection flow in the handler with new state, keyboards, and callbacks.

- [ ] **3.1** Add ALBUM_SELECT state, keyboards, and handler methods
    - **Context:**
        - **Why:** Users need to see combined results with type indicators, and after selecting an artist, choose between full monitoring or picking specific albums
        - **Architecture:** New `ALBUM_SELECT = 5` state in `states.py`. Two new keyboard builders: `get_album_monitor_mode_keyboard()` for the "All Albums" / "Pick Specific" prompt, and `get_album_selection_keyboard()` mirroring the season picker toggle/confirm pattern. Handler methods: `handle_album_monitor_mode()`, `handle_album_selection()`, `handle_album_confirm()`.
        - **Key refs:** `src/bot/states.py:16` (SEASON_SELECT=4), `src/bot/handlers/media.py:802` (handle_season_selection pattern to mirror), `src/bot/handlers/media.py:709` (handle_quality_selection — branch point for music), `src/bot/keyboards.py:295` (get_search_results_list_keyboard — emoji logic to update)
        - **Watch out:** ConversationHandler state map needs ALBUM_SELECT with both `album_monitor_mode_` and `albumsel_` callback patterns. Season picker keyboard is built inline in handler (lines 873-910) — album picker should use centralized keyboard function in `keyboards.py`. List view emoji should show 🎤/💿 per-result `music_type` instead of generic 🎵.
    - **Scope:** State definition, keyboard builders, handler methods, caption updates, translation keys, list view emoji
    - **Touches:** `src/bot/states.py`, `src/bot/keyboards.py`, `src/bot/handlers/media.py`, `tests/test_handlers/test_media_handler.py`, `tests/test_handlers/conftest.py`, `translations/addarr.*.yml`
    - **Action items:**
        - [RED] Test `States.ALBUM_SELECT == 5`
        - [RED] Tests for `get_album_monitor_mode_keyboard()`: returns 2 buttons with correct callbacks
        - [RED] Tests for `get_album_selection_keyboard()`: basic layout, selected checkmarks, monitor_all, future mode
        - [RED] Tests for `_build_result_caption()` with album music_type shows album-specific format
        - [RED] Tests for `handle_selection()`: album result stores `music_type`, `artist_id`, `album_id` in user_data; song result stores same + shows "Adding album X which contains Y" message
        - [RED] Tests for `handle_quality_selection()`: music artist shows monitor mode prompt (ALBUM_SELECT); music album/song adds with pre-selected album (END)
        - [RED] Tests for `handle_album_monitor_mode()`: "all" adds directly (END), "pick" shows picker (ALBUM_SELECT)
        - [RED] Tests for `handle_album_selection()`: toggle individual, toggle all, future mode, monitor_all auto-confirms, cancel
        - [RED] Tests for `handle_album_confirm()`: passes `albums_to_monitor` to service, monitor_all passes None, error handling
        - [GREEN] Add `ALBUM_SELECT = 5` to `src/bot/states.py`
        - [GREEN] Add `get_album_monitor_mode_keyboard()` and `get_album_selection_keyboard()` to `src/bot/keyboards.py`
        - [GREEN] Add translation keys to all locale files
        - [GREEN] Update `_build_result_caption()` for album type indicator
        - [GREEN] Update `get_search_results_list_keyboard()` to use per-result emoji for music
        - [GREEN] Modify `handle_selection()` — detect `album:` prefix, store routing data
        - [GREEN] Modify `handle_quality_selection()` — branch for music: artist→monitor mode, album→picker
        - [GREEN] Add `handle_album_monitor_mode()`, `handle_album_selection()`, `handle_album_confirm()`
        - [GREEN] Register ALBUM_SELECT state in ConversationHandler state map
        - [GREEN] Update handler conftest with `get_artist_albums` mock
    - **Success:** Full conversation flow works for all three paths (artist→mode→add, artist→mode→picker→confirm, album→quality→add). All existing tests pass + new tests pass. `pytest --tb=short -q` all green. `flake8 .` clean.

---

## Callback Pattern Reference

| Pattern | Handler | Description |
|---------|---------|-------------|
| `album_monitor_mode_all` | `handle_album_monitor_mode` | Add artist, monitor everything |
| `album_monitor_mode_pick` | `handle_album_monitor_mode` | Show album picker |
| `albumsel_{foreignAlbumId}` | `handle_album_selection` | Toggle individual album |
| `albumsel_all` | `handle_album_selection` | Toggle all albums |
| `albumsel_future` | `handle_album_selection` | Toggle future releases mode |
| `albumsel_monitor_all` | `handle_album_selection` | Select all + auto-confirm |
| `albumsel_confirm` | `handle_album_selection` | Confirm album selection |

## Verification

```bash
# Phase 1 check
pytest tests/test_api/test_lidarr.py -v

# Phase 2 check
pytest tests/test_services/test_media_service.py -v

# Phase 3 check
pytest tests/test_handlers/test_media_handler.py -v

# Full suite
pytest --tb=short -q
pytest --cov=src --cov-report=term-missing

# Lint
flake8 .

# Translation validation
python run.py --validate-i18n
```
