# Issue 103: Lidarr Album Track Details in Search Results

## Overview

Surface track listings (number, title, duration) in album/song detail views during music search. `LidarrClient.get_album_tracks()` exists but is never called — wire it through the service and display layers.

---

### Phase 1: Service + Formatter Layers (2 tasks)

**Goal:** Add `MediaService.get_album_tracks()` and all formatter logic including the track listing section in album/song captions.

- [x] **1.1** Add `MediaService.get_album_tracks()` with tests
    - **Context:** See plan.md Phase 1. Pattern: `get_artist_albums()` at `src/services/media.py:508`. Mock fixture already has `client.get_album_tracks = AsyncMock(return_value=[])` in `tests/test_services/conftest.py:61`. Test class pattern: `TestGetArtistAlbums` at `tests/test_services/test_media_service.py:1695`.
    - **Watch out:** Three cases — returns tracks, exception → `[]`, Lidarr disabled → `[]`.
    - **Scope:** New method in `MediaService`; test class in service tests
    - **Touches:** `src/services/media.py`, `tests/test_services/test_media_service.py`
    - **Action items:**
        - [RED] Write `TestGetAlbumTracks` class: test delegates to `lidarr.get_album_tracks()` and returns raw result, test returns `[]` on exception, test returns `[]` when `_lidarr is None`
        - [GREEN] Implement `get_album_tracks(self, album_id: str) -> List[Dict]` wrapping `self.lidarr.get_album_tracks(album_id)`
    - **Success:** `pytest tests/test_services/test_media_service.py -k "AlbumTracks" -v` green; full suite green
    - **Completed:** 2026-03-30
    - **Learnings:** `get_artist_albums()` is the direct pattern template — same structure (guard on `self.lidarr`, try/except returning `[]`).
    - **Key Changes:** `src/services/media.py` — added `get_album_tracks()`; `tests/test_services/test_media_service.py` — added `TestGetAlbumTracks` (3 tests)
    - **Notes:** `mock_lidarr_client` fixture in `tests/test_services/conftest.py` already has `get_album_tracks = AsyncMock(return_value=[])` pre-configured.

- [ ] **1.2** Add track listing formatter + integrate into captions + display functions
    - **Context:** See plan.md Phase 2 & 3. `_format_track_listing()` is a pure sync helper; tracks come from `result.get("tracks", [])`. `show_result()` and `show_list_detail()` are async — add track fetch there for `music_type in ("album", "song")`. Key refs: `src/bot/handlers/media/formatters.py:65` (`build_result_caption`), `:168` (`show_result`), `:264` (`show_list_detail`). Track data shape: `{"trackNumber": "1", "title": "Papercut", "duration": 185000}` (duration in ms). See `tests/fixtures/sample_data.py:167` for `LIDARR_ALBUM_WITH_TRACKS`.
    - **Watch out:** Photo captions capped at 1024 chars — cap tracks at 8, truncate titles at 28 chars. Track listing goes between overview/details and external links. Add `from src.services.media import MediaService` import in formatters — handler layer importing service is allowed by architecture rules. Don't mutate the input result dict; use `{**result, "tracks": tracks}`.
    - **Scope:** `_format_track_listing()` helper, `build_result_caption()` album/song branches, `show_result()` + `show_list_detail()` fetch logic
    - **Touches:** `src/bot/handlers/media/formatters.py`, `tests/test_handlers/test_media_formatters.py`
    - **Action items:**
        - [RED] Test `_format_track_listing()`: full list with duration, truncates titles >28 chars, caps at 8 with "and N more" suffix, zero-pads track numbers, returns `""` for empty list, handles missing duration (0ms → `0:00`)
        - [RED] Test `build_result_caption()` album with tracks: track listing section present, between details and links
        - [RED] Test `build_result_caption()` album without tracks (missing key): no track section, no crash
        - [RED] Test `build_result_caption()` song with tracks: track listing present
        - [RED] Test `show_result()` for album: calls `MediaService().get_album_tracks(album_id)` and embeds tracks
        - [RED] Test `show_result()` for non-music result: does NOT call `get_album_tracks`
        - [RED] Test `show_list_detail()` for album: calls `get_album_tracks` and embeds tracks
        - [GREEN] Add `_format_track_listing(tracks, max_tracks=8)` to `formatters.py`
        - [GREEN] Update `build_result_caption()` album/song branches to call `_format_track_listing(result.get("tracks", []))` and insert after release date / artist line
        - [GREEN] Update `show_result()` and `show_list_detail()` to fetch+embed tracks for album/song types
        - [GREEN] Export `_format_track_listing` in formatters (or keep private; tests import it directly)
    - **Success:** All new tests green; `pytest tests/test_handlers/test_media_formatters.py -v` fully green; full suite green
