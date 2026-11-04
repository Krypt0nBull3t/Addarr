# Issue #200: Lidarr adds monitor the wrong albums - Tasks

Source: `docs/issues/issue-200/plan.md`. Issue: https://github.com/Krypt0nBull3t/Addarr/issues/200.

### Phase 1: Lidarr client follows the Lidarr API (6 tasks)

**Goal:** Adds pick the right artist, monitor the right albums, and no code reads fields Lidarr does not have.

**Phase Context:**

- Why NOT keep the `results[0]` fallback: it adds an artist the user did not pick.
- Why NOT edit the song branches in `formatters.py` and `keyboards.py`: the issue deletes only the extraction, `get_album_tracks`, its fixture and its tests. The branches become dead code and stay.
- Why NOT touch `Artist.album_folder` in `src/models/media.py`: #226 deletes that file.
- Risk for the PR body: `monitorNewItems: "none"` is sent whenever `future_albums` is false, also with config `monitorOption: all`. `monitorOption` selects existing albums, a separate setting.

- [x] **1.1** F051 + F054: `add_artist` request body and `albumFolder` removal
    - **Context:**
        - **Why:** Lidarr uses its default (`all`) for new releases because `monitorNewItems` is never sent. `albumFolder` is not in `ArtistResource`, so the wizard question has no effect.
        - **Architecture:** `LidarrClient.add_artist` builds the POST body in `data`. `monitorNewItems` is a top-level `ArtistResource` field, not part of `addOptions`.
        - **Key refs:** `src/api/lidarr.py:145-212` (`add_artist`), `src/setup/prompts.py:291`, `src/setup/service_config.py:78`, `config_example.yaml:71`, `tests/conftest.py:60` (`MockConfig`), `tests/test_api/test_lidarr.py:478` (`test_add_artist_includes_album_folder_from_config`), `tests/test_setup/test_prompts.py:351`, `tests/test_setup/test_service_config.py:66`
        - **Watch out:** With `future_albums=True` send no `monitorNewItems` (Lidarr default is `all`). The prompt test mocks two confirm answers (search, albumFolder); after the change only one confirm remains.
    - **Scope:** One new body field, one removed field, one removed wizard prompt and its config lines.
    - **Touches:** `src/api/lidarr.py`, `src/setup/prompts.py`, `src/setup/service_config.py`, `config_example.yaml`, `tests/conftest.py`, `tests/test_api/test_lidarr.py`, `tests/test_setup/test_prompts.py`, `tests/test_setup/test_service_config.py`
    - **Action items:**
        - [RED] `test_add_artist_sends_monitor_new_items_none_when_future_albums_off`: `add_artist(..., future_albums=False)` posts `monitorNewItems == "none"`, also with `albums_to_monitor`
        - [RED] `test_add_artist_future_albums_omits_monitor_new_items`: `future_albums=True` has no `monitorNewItems` key
        - [RED] Replace the albumFolder test with `test_add_artist_body_has_no_album_folder`
        - [RED] `test_lidarr_has_monitor_option` in `test_prompts.py` (one confirm, `"albumFolder" not in result`); `test_service_config.py` asserts `"albumFolder" not in config["features"]`
        - [GREEN] Edit `add_artist`: drop `album_folder` and the `albumFolder` key, set `data["monitorNewItems"] = "none"` when `not future_albums`
        - [GREEN] Delete the wizard prompt, the `service_config.py` line, the `config_example.yaml` line and the `MockConfig` entry
    - **Success:** `scripts/test_runner.py api` and `setup` pass with coverage, flake8 and mypy clean

    - **Completed:** 2026-11-04
    - **Learnings:** monitorNewItems is a top-level ArtistResource field, not in addOptions. The wizard test mocked two confirm answers; one remains.
    - **Key Changes:** src/api/lidarr.py add_artist sends monitorNewItems none when future_albums is false and no albumFolder. Removed albumFolder from prompts.py, service_config.py, config_example.yaml, tests/conftest.py.
    - **Notes:** Existing user config.yaml files may still hold albumFolder; it is ignored.

- [x] **1.2** F052: exact id match only
    - **Context:**
        - **Why:** If `artist/lookup?term=lidarr:<mbid>` is empty, the free-text fallback returns other artists and the bot adds `results[0]`.
        - **Architecture:** Keep the free-text fallback lookup. Accept only a result whose `foreignArtistId` equals the id.
        - **Key refs:** `src/api/lidarr.py:133-136` (`get_artist`), `:164-170` (`add_artist`), `tests/test_api/test_lidarr.py:178` and `:312` (tests that pin the old fallback), `LIDARR_SEARCH_RESULTS` in `tests/fixtures/sample_data.py`
        - **Watch out:** `add_artist` already returns `(False, "Artist not found")` when `artist` is falsy. `test_add_artist_falsy_first_element` must still pass. No POST may be sent on no match (assert with `aio_mock`).
    - **Scope:** Delete two "use first result" blocks, flip two tests, add two tests.
    - **Touches:** `src/api/lidarr.py`, `tests/test_api/test_lidarr.py`
    - **Action items:**
        - [RED] `test_add_artist_lidarr_lookup_empty_and_fallback_other_artist`: `(False, "Artist not found")`, no POST recorded
        - [RED] `test_get_artist_fallback_no_exact_match_returns_none`
        - [RED] Rewrite `test_add_artist_no_exact_match_uses_first` and `test_get_artist_fallback_no_exact_match_uses_first` to expect not found
        - [GREEN] Remove the `results[0]` fallback in `get_artist` and `add_artist`
    - **Success:** `scripts/test_runner.py api --coverage` passes

    - **Completed:** 2026-11-04
    - **Learnings:** The first lidarr: lookup in get_artist still returns results[0] unchecked; the lidarr: term is an exact id lookup, so only the free-text fallback needed the match.
    - **Key Changes:** src/api/lidarr.py get_artist and add_artist: removed both results[0] fallbacks. Tests flipped to expect not found, plus a no-POST assertion via aio_mock.requests.
    - **Notes:** add_artist matches foreignArtistId on both lookups.

- [x] **1.3** F050: album picker lists the picked artist's albums
    - **Context:**
        - **Why:** `album/lookup` treats the MBID as free text, returns nothing, and Done adds the artist with nothing monitored. Only the `lidarr:` and `mbid:` prefixes are id lookups.
        - **Architecture:** `MediaService.get_artist_albums` calls `LidarrClient.search_albums`. Search by artist name, keep albums whose `artist.foreignArtistId` equals the picked MBID.
        - **Key refs:** `src/services/media.py:479-501`, `src/bot/handlers/media/album_picker.py:64`, `tests/test_services/test_media_service.py` (`TestGetArtistAlbums`, `SAMPLE_ALBUM`), `tests/test_handlers/test_media_handler.py:2655` and `:3045`
        - **Watch out:** The new signature is `get_artist_albums(self, artist_id: str, artist_name: str) -> List[Dict]`. Keep the `[]` on disabled and on exception. Existing tests in `TestGetArtistAlbums` call with one argument.
    - **Scope:** Signature change, filter, one caller.
    - **Touches:** `src/services/media.py`, `src/bot/handlers/media/album_picker.py`, `tests/test_services/test_media_service.py`, `tests/test_handlers/test_media_handler.py`
    - **Action items:**
        - [RED] `test_searches_by_artist_name_and_keeps_only_picked_artist` (two artists in the results, `search_albums` awaited with the name)
        - [RED] Update the other `TestGetArtistAlbums` tests to two arguments; assert the handler pick test awaits `get_artist_albums("artist-1", "Test Artist")`
        - [GREEN] Change `get_artist_albums`; pass `selected["id"], selected["title"]` in `album_picker.py`
    - **Success:** `scripts/test_runner.py services` and `handlers` pass with coverage

    - **Completed:** 2026-11-04
    - **Learnings:** album/lookup treats a bare MBID as free text. The scoped services run shows rate_limit.py below 100% because its tests live elsewhere; the full-suite gate covers it.
    - **Key Changes:** MediaService.get_artist_albums(artist_id, artist_name) searches by name and filters on album.artist.foreignArtistId. album_picker.py passes selected id and title.
    - **Notes:** Albums without an artist object are dropped by the filter.

- [x] **1.4** F053: delete the dead song search
    - **Context:**
        - **Why:** `MediumResource` has only `mediumNumber`, `mediumName` and `mediumFormat`, so the song loop finds 0 songs. `get_album_tracks` has no callers.
        - **Architecture:** `search_music` returns `artists + albums`. Song branches in `formatters.py:100` and `keyboards.py:344` and their tests stay (decision A).
        - **Key refs:** `src/services/media.py:243-264`, `src/api/lidarr.py:77-111`, `tests/fixtures/sample_data.py:165` (`LIDARR_ALBUM_WITH_TRACKS`), `tests/test_api/test_lidarr.py:21` (import) and `:886-945` (4 tests), `tests/test_services/test_media_service.py:89` (`SAMPLE_ALBUM_WITH_TRACKS`) and its users at `:353`, `:1224`, `:1242`, `:1317`, `tests/test_services/conftest.py:59`, `.claude/skills/addarr-testing/references/fixtures.md:190`
        - **Watch out:** `tests/test_architecture/test_skills.py` reads the skill docs, so fix `fixtures.md` too. `test_result_ordering` must switch to `SAMPLE_ALBUM` and drop its song checks. Update the `search_music` docstring ("artists, albums, and songs").
    - **Scope:** Pure deletion plus test cleanup. No new test.
    - **Touches:** `src/services/media.py`, `src/api/lidarr.py`, the test files above, `fixtures.md`
    - **Action items:**
        - [RED] Delete the song tests first and confirm the suite still passes (no red step: pure deletion)
        - [GREEN] Remove the song loop and `songs` list; delete `get_album_tracks`
        - [GREEN] Delete the fixtures, the 4 `TestLidarrGetAlbumTracks` tests, the conftest mock and the `fixtures.md` mention
    - **Success:** `scripts/test_runner.py api services` pass with coverage; `pytest tests/test_architecture` passes

    - **Completed:** 2026-11-04
    - **Learnings:** Song tests also lived in test_media_service.py (3 tests plus a fixture), beyond the 4 get_album_tracks tests in test_lidarr.py. test_architecture reads fixtures.md, so the doc line had to go too.
    - **Key Changes:** Removed LidarrClient.get_album_tracks, the song loop in MediaService.search_music, LIDARR_ALBUM_WITH_TRACKS, SAMPLE_ALBUM_WITH_TRACKS, the get_album_tracks mock and 7 tests. test_result_ordering now asserts [artist, album].
    - **Notes:** Song branches in formatters.py and keyboards.py stay as dead code (decision A).

- [x] **1.5** F055: no fake year, no dead poster URLs
    - **Context:**
        - **Why:** `statistics.yearStart` does not exist, so year is always N/A. The coverartarchive URL uses an artist MBID as a release-group id (404). The audioscrobbler branch is unreachable.
        - **Architecture:** Drop the `year` key from artist results; `formatters.py:120` prints a year only when the key exists. `poster` is the first poster or cover `remoteUrl`, else `None`.
        - **Key refs:** `src/services/media.py:181-210`, `tests/test_services/test_media_service.py:67` (`SAMPLE_ARTIST`), `tests/fixtures/sample_data.py:119,130`, `src/bot/handlers/media/formatters.py:120`
        - **Watch out:** Remove `yearStart` from the fixtures. Check that a formatter test covers a missing `year` key for a music artist; add one if not.
    - **Scope:** Remove one key, simplify one expression, fixture cleanup.
    - **Touches:** `src/services/media.py`, `tests/test_services/test_media_service.py`, `tests/fixtures/sample_data.py`, `tests/test_handlers/test_media_formatters.py`
    - **Action items:**
        - [RED] `test_artist_without_images_has_no_poster` (`result["poster"] is None`)
        - [RED] `test_artist_result_has_no_year_key`
        - [RED] A formatter test: an artist result without `year` has no "Year" line
        - [GREEN] Edit the artist normalization in `search_music`
    - **Success:** `scripts/test_runner.py services handlers` pass with coverage

    - **Completed:** 2026-11-04
    - **Learnings:** The caption formatter already skips the year line when the key is missing, so the formatter test is a guard that passed before the change.
    - **Key Changes:** search_music artist results lose the year key and the coverartarchive and audioscrobbler poster fallbacks; poster is the first poster or cover image URL or None. Removed yearStart from three fixtures.
    - **Notes:** Artist cards show no year line.

- [ ] **1.6** F056: webhook quality from `trackFiles`
    - **Context:**
        - **Why:** Lidarr Download and Upgrade payloads have no `release.quality`; the quality is in `trackFiles[].quality`. The notification shows "Unknown".
        - **Architecture:** In `parse_lidarr_event`, keep `release.quality` first, then fall back to `trackFiles[0].quality`, else "Unknown".
        - **Key refs:** `src/models/webhook.py:209-213`, `tests/test_models/test_webhook_models.py:288` (`TestParseLidarrEvent`)
        - **Watch out:** `trackFiles` may be missing, `null` or empty. Guard with `or []`. The shape comes from the Lidarr source, not the spec.
    - **Scope:** One fallback.
    - **Touches:** `src/models/webhook.py`, `tests/test_models/test_webhook_models.py`
    - **Action items:**
        - [RED] `test_download_event_quality_from_track_files` (`"FLAC"`, no `release`)
        - [RED] `test_release_quality_wins_over_track_files`
        - [RED] `test_download_event_without_quality_is_unknown` (empty `trackFiles`)
        - [GREEN] Implement the fallback
    - **Success:** `scripts/test_runner.py models --coverage` passes
