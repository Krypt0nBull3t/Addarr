# Plan: Lidarr Album Track Details in Search Results (#103)

## Context

`LidarrClient.get_album_tracks()` was implemented in issue #82 but is never called from any handler or service. When users browse album search results, they see title/artist/release date but no track listing. The goal is to surface track details (number, title, duration) in the album/song detail view during search.

### What already exists
- `LidarrClient.get_album_tracks(foreign_album_id)` — fetches tracks via `album/lookup?term=lidarr:{id}`, extracts from `media[].tracks[]`
- `MediaService.get_artist_albums()` — pattern for a thin service wrapper
- `build_result_caption()` — formats album/song captions; currently no track data
- `show_result()` / `show_list_detail()` — async display functions that call `build_result_caption()`
- Track fixture `LIDARR_ALBUM_WITH_TRACKS` with `{trackNumber, title, duration}` fields (duration in ms)

### Constraints
- Telegram photo captions: 1024 char limit — must cap track listing
- Architecture rule: handlers may import services (no violation)
- Formatters are in `src/bot/handlers/media/` — handler layer, may import services

## Target Structure

| File | Change |
|------|--------|
| `src/services/media.py` | Add `get_album_tracks(album_id)` — thin wrapper around `LidarrClient.get_album_tracks()` |
| `src/bot/handlers/media/formatters.py` | Add `_format_track_listing()`, update `build_result_caption()` to include tracks, update `show_result()` + `show_list_detail()` to fetch tracks for album/song |
| `tests/test_services/test_media_service.py` | Add `TestGetAlbumTracks` class |
| `tests/test_handlers/test_media_formatters.py` | Add tests for `_format_track_listing()` and track listing in captions |

## Design Decisions

1. **Fetch in display functions, not search** — fetching tracks per-album during `search_music()` would add N extra API calls per search. Instead, fetch on demand when displaying a result card or list detail.

2. **Embed tracks in result dict** — `show_result()` and `show_list_detail()` fetch tracks for album/song types and create a copy of the result dict with `"tracks"` key before calling `build_result_caption()`. This keeps `build_result_caption()` synchronous.

3. **Graceful degradation** — if `get_album_tracks()` returns `[]` (Lidarr disabled, network error, no track data), the caption renders without the track section. No user-visible error.

4. **Cap at 8 tracks** — avoids hitting the 1024 char caption limit. Show count suffix `...and N more` when there are more. Truncate long track titles at 28 chars.

5. **Duration format** — `m:ss` (e.g. `3:05`). Duration is in ms from Lidarr API.

## Track Listing Format

```
🎵 Tracks:
01. Papercut (3:05)
02. One Step Closer (2:36)
03. With You (3:23)
```

Appears between the overview/details and the external links in album captions.

## Phased Approach

### Phase 1 — Service layer
Add `MediaService.get_album_tracks()` with tests.

### Phase 2 — Formatter helpers
Add `_format_track_listing()` (pure function, sync, testable) with tests.
Update `build_result_caption()` to include tracks from `result.get("tracks", [])`.

### Phase 3 — Display integration
Update `show_result()` and `show_list_detail()` to fetch + embed tracks for album/song results.
Add integration-level tests for the display functions.

## Verification Steps
1. `python -m pytest tests/test_services/test_media_service.py -k "AlbumTracks" -v` — green
2. `python -m pytest tests/test_handlers/test_media_formatters.py -v` — all green
3. `python -m pytest --tb=short -q` — full suite green
4. `python -m flake8 .` — no new violations
5. `python -m mypy src/` — no new errors
