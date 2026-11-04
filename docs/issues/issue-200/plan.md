# Issue #200: Lidarr adds monitor the wrong albums

**Goal:** Make the Lidarr client follow the Lidarr API: add the artist the user picked, monitor the right albums, and drop code that reads fields Lidarr does not have.

**Issue:** https://github.com/Krypt0nBull3t/Addarr/issues/200 (findings F050 to F056 of audit 2026-10-28).

**Branch:** `fix/200-lidarr-adds-monitor-wrong-albums`, PR targets `development`.

## Context and root causes

Read from the code, all as the issue states:

| Finding | Root cause |
|-|-|
| F051 | `LidarrClient.add_artist` (`src/api/lidarr.py:177-200`) never sets `monitorNewItems`. Lidarr defaults to `all`. |
| F052 | `get_artist` (`:133-136`) and `add_artist` (`:164-166`) take `results[0]` when no `foreignArtistId` matches. |
| F050 | `MediaService.get_artist_albums` (`src/services/media.py:489`) sends the artist MBID to `album/lookup` as free text. Only `lidarr:` and `mbid:` prefixes are id lookups. |
| F053 | `MediaService.search_music` (`:243-261`) reads `media[].tracks`. `MediumResource` has no `tracks`. `LidarrClient.get_album_tracks` has no callers. |
| F054 | `albumFolder` is not in `ArtistResource`. The wizard, default config, example config and `add_artist` still use it. |
| F055 | `statistics.yearStart` does not exist. The coverartarchive URL uses an artist MBID as a release-group id. The audioscrobbler branch is unreachable (the coverartarchive branch always wins). |
| F056 | `parse_lidarr_event` (`src/models/webhook.py:209-213`) reads only `release.quality`. Download and Upgrade payloads carry `trackFiles[].quality`. |

## Decisions (confirmed by the orchestrator)

- A: Leave the song branches in `formatters.py`, `keyboards.py` and their tests. They become dead code. The issue deletes only the extraction, `get_album_tracks`, its fixture and its 4 tests.
- B: Remove `albumFolder` from the wizard, `service_config.py`, `config_example.yaml`, `tests/conftest.py` and `test_service_config.py`. Keep `Artist.album_folder` in `src/models/media.py` (#226 deletes that file).
- C: Drop the `year` key from artist results. The card then shows no year line (`formatters.py:120` prints a year only when the key exists). `poster` is `None` when the artist has no poster or cover image.
- D: `get_artist_albums(artist_id, artist_name)` searches `album/lookup` by name and keeps albums whose `artist.foreignArtistId == artist_id`.
- E: No `results[0]` fallback in `get_artist` and `add_artist`.
- F051: `monitorNewItems` is a top-level field of `ArtistResource`. Send `"none"` whenever `future_albums` is false. When `future_albums` is true, send nothing (Lidarr default is `all`).

## Risk

With `future_albums` false, new releases are never monitored, even with config `monitorOption: all`. This is what the acceptance test pins. Note it in the PR body.

## Tasks

TDD order. Each task: write the failing tests, run them red, change `src/`, run the layer check, commit.

### Task 1: F051 and F054, `add_artist` request body

Files: `src/api/lidarr.py`, `tests/test_api/test_lidarr.py`, `src/setup/prompts.py`, `src/setup/service_config.py`, `config_example.yaml`, `tests/conftest.py`, `tests/test_setup/test_prompts.py`, `tests/test_setup/test_service_config.py`.

Tests:
- `test_api/test_lidarr.py`: `test_add_artist_sends_monitor_new_items_none_when_future_albums_off`: `add_artist(ARTIST_ID, "/music", 1, future_albums=False)` posts a body with `monitorNewItems == "none"`. Also assert it for the `albums_to_monitor=[...]` call.
- `test_add_artist_future_albums_omits_monitor_new_items`: with `future_albums=True` the body has no `monitorNewItems` key.
- Replace `test_add_artist_includes_album_folder_from_config` with `test_add_artist_body_has_no_album_folder`: the POST body has no `albumFolder` key.
- `test_setup/test_prompts.py`: rename `test_lidarr_has_album_folder_and_monitor` to `test_lidarr_has_monitor_option`; one confirm answer (search); assert `"albumFolder" not in result`.
- `test_setup/test_service_config.py:66`: assert `"albumFolder" not in config["features"]`.

Code:
- `add_artist`: delete `album_folder` and the `"albumFolder"` key. Add `data["monitorNewItems"] = "none"` when `not future_albums`.
- Delete the `albumFolder` confirm in `src/setup/prompts.py:291`, the line in `service_config.py:78`, `config_example.yaml:71`, and `albumFolder` from `MockConfig` in `tests/conftest.py:60`.

Check: `scripts/test_runner.py api setup --coverage`, `--validate-i18n` not needed.

### Task 2: F052, exact id match only

Files: `src/api/lidarr.py`, `tests/test_api/test_lidarr.py`.

Tests (fixture `LIDARR_SEARCH_RESULTS` has two other artists):
- `test_add_artist_lidarr_lookup_empty_and_fallback_other_artist`: `lidarr:` lookup returns `[]`, free-text lookup returns an artist with another `foreignArtistId`. Assert `(False, "Artist not found")` and no POST request recorded.
- `test_get_artist_fallback_no_exact_match_returns_none`: same lookups, `get_artist` returns `None`.
- Rewrite `test_add_artist_no_exact_match_uses_first` (lidarr: lookup returns other artists) to expect `(False, "Artist not found")` and no POST. Rewrite `test_get_artist_fallback_no_exact_match_uses_first` to expect `None`.

Code: in `get_artist` delete the `results[0]` fallback block. In `add_artist` delete the "use first result" block. `if not artist` already returns `"Artist not found"`.

Check: `scripts/test_runner.py api --coverage`.

### Task 3: F050, album picker lists the picked artist's albums

Files: `src/services/media.py`, `src/bot/handlers/media/album_picker.py`, `tests/test_services/test_media_service.py`, `tests/test_handlers/test_media_handler.py`.

Tests:
- `test_media_service.py::TestGetArtistAlbums`: `test_searches_by_artist_name_and_keeps_only_picked_artist`: `search_albums` returns albums of two artists (`some-mbid-123` and `other-mbid-456`). Call `get_artist_albums("some-mbid-123", "Radiohead")`. Assert `search_albums` was awaited with `"Radiohead"` and only the albums of `some-mbid-123` come back. Update the other tests in the class to the two-argument call.
- `test_media_handler.py` (pick test near line 2655): assert `get_artist_albums` awaited with `("artist-1", "Test Artist")`.

Code: `async def get_artist_albums(self, artist_id: str, artist_name: str) -> List[Dict]`. Call `self.lidarr.search_albums(artist_name)`. Filter `album.get("artist", {}).get("foreignArtistId") == artist_id`. `album_picker.py:64` passes `selected["id"], selected["title"]`.

Check: `scripts/test_runner.py services handlers --coverage`.

### Task 4: F053, delete the dead song search

Files: `src/services/media.py`, `src/api/lidarr.py`, `tests/fixtures/sample_data.py`, `tests/test_api/test_lidarr.py`, `tests/test_services/test_media_service.py`, `tests/test_services/conftest.py`, `.claude/skills/addarr-testing/references/fixtures.md`.

No new test. Delete:
- the `songs` list and the track loop in `search_music`; return `artists + albums`; fix the comment and docstring ("artists, albums, and songs").
- `LidarrClient.get_album_tracks`.
- `LIDARR_ALBUM_WITH_TRACKS` and its import in `test_lidarr.py`; the 4 `TestLidarrGetAlbumTracks` tests.
- `SAMPLE_ALBUM_WITH_TRACKS`, `test_search_music_song_external_ids`, `test_song_results_from_track_data`, `test_no_song_when_no_track_data`. In `test_result_ordering` use `SAMPLE_ALBUM` and drop the song index checks; rename its docstring to artists before albums.
- `client.get_album_tracks` in `tests/test_services/conftest.py:59`; `get_album_tracks()` in `fixtures.md:190`.

Check: `scripts/test_runner.py api services --coverage` and `pytest tests/test_architecture` (skill accuracy test reads `fixtures.md`).

### Task 5: F055, no fake year, no dead poster URLs

Files: `src/services/media.py`, `tests/test_services/test_media_service.py`, `tests/fixtures/sample_data.py`.

Tests (`TestSearchMusicCombined`):
- `test_artist_without_images_has_no_poster`: `SAMPLE_ARTIST` has `images: []`. Assert `result["poster"] is None`.
- `test_artist_result_has_no_year_key`: assert `"year" not in result`.
- Remove `statistics.yearStart` from `SAMPLE_ARTIST` (`test_media_service.py:67`) and `LIDARR_SEARCH_RESULTS` (`sample_data.py:119,130`).

Code: in the artist normalization of `search_music`, delete the `"year"` entry. Set `"poster"` to the first `poster` or `cover` image `remoteUrl`, else `None`.

Check: `scripts/test_runner.py services handlers --coverage` (formatter tests cover a missing year key; add one if none does).

### Task 6: F056, webhook quality from `trackFiles`

Files: `src/models/webhook.py`, `tests/test_models/test_webhook_models.py`.

Tests (`TestParseLidarrEvent`):
- `test_download_event_quality_from_track_files`: payload `{"eventType": "Download", "artist": {"name": "Pink Floyd"}, "album": {"title": "..."}, "trackFiles": [{"quality": "FLAC"}]}` gives `event.details["quality"] == "FLAC"`.
- `test_release_quality_wins_over_track_files`: both set, `release.quality` is used.
- `test_download_event_without_quality_is_unknown`: no `release`, empty `trackFiles` gives `"Unknown"`.

Code: after the `release.quality` check, fall back to `payload.get("trackFiles")[0].get("quality")` when the list is non-empty. Guard with `or []`.

Check: `scripts/test_runner.py models --coverage`.

## Verification

- Preflight (`/addarr pr` step 5): flake8, mypy, translations, unit tests with the 100% gate, integration, architecture tests, all through the suite lock.
- create-pr step 1 runs `arr-api-contract-checker` because `src/api/lidarr.py` changes. It checks `monitorNewItems`, the dropped `albumFolder` and `album/lookup` use.
- Each acceptance test in the issue maps to a test above and is shown red before its fix.
