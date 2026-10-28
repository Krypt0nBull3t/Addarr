---
title: "Lidarr adds monitor the wrong albums"
labels: [bug, agent-ready, priority:critical]
slice: 5
findings: [F051, F052, F050, F053, F054, F055, F056]
---

## Bug

The Lidarr client does not follow the Lidarr API. Adds can pick the wrong artist and monitor the wrong albums. Several fields the bot reads or sends do not exist.

- **F051** `monitorNewItems` is never sent. Lidarr uses its default, so new releases are monitored even with "future albums" off. The spec has the field.
- **F052** If the exact `lidarr:<mbid>` lookup is empty, the free-text fallback adds `results[0]` even when its id differs. That adds the wrong artist.
- **F050** The album picker sends the artist MBID to `album/lookup` as free text. Only the `lidarr:` and `mbid:` prefixes are id lookups, so the result is empty. Done then adds the artist with nothing monitored.
- **F053** Song search reads `tracks` on `MediumResource`, which has only mediumNumber, mediumName and mediumFormat. It always finds 0 songs. `get_album_tracks` has no callers.
- **F054** `albumFolder` is not in Lidarr `ArtistResource`. The wizard still asks for it.
- **F055** Lidarr `statistics.yearStart` does not exist, so the year is always N/A. The coverartarchive fallback uses the artist MBID as a release-group id (404). The audioscrobbler branch is unreachable.
- **F056** Lidarr webhook Download and Upgrade quality is always "Unknown". The quality is in `trackFiles[].quality` (from the Lidarr source, not a spec).

## Steps to reproduce

F051:

1. Send /music, pick an artist, pick some albums with "future albums" off, and tap Done.
2. The POST body has no `monitorNewItems`.
3. In Lidarr, new releases of that artist are monitored.

F052:

1. Add an artist whose `artist/lookup?term=lidarr:<mbid>` returns nothing.
2. The fallback `artist/lookup?term=<mbid>` returns other artists.
3. The bot adds the first of them, a different artist.

F050:

1. Send /music, pick an artist, and choose to pick albums.
2. `album/lookup?term=<artist mbid>` returns nothing, so the picker has no albums.
3. Tap Done. The artist is added with nothing monitored.

F053:

1. Send /music and search for a song title.
2. The results never contain a song.

F054:

1. Run the wizard and answer "Organize tracks in album folders?".
2. The answer has no effect in Lidarr.

F055:

1. Send /music and search for an artist without a poster image.
2. The card shows year N/A, and the poster URL returns 404.

F056:

1. Let Lidarr send a Download webhook.
2. The notification shows quality "Unknown".

## Expected behavior

- With "future albums" off, Lidarr does not monitor new releases.
- The bot adds the artist the user picked, or says "not found".
- The album picker lists the albums of the picked artist.
- Search results contain no dead song matches. Config has no `albumFolder`.
- Artist cards show a real year or none, and only poster URLs that work.
- Lidarr webhook notifications show the track quality.

## Fix

- [ ] **F051** Send `"monitorNewItems": "none"` when `future_albums` is off (`src/api/lidarr.py:181-199`)
- [ ] **F052** Return "not found" when no result matches the id exactly (`src/api/lidarr.py:133-136`, `:164-166`)
- [ ] **F050** Search by artist name and keep only albums whose artist MBID matches (`src/services/media.py:489`, `src/bot/handlers/media/album_picker.py:64`)
- [ ] **F053** Delete the song extraction, `get_album_tracks`, its fixture and its 4 tests (`src/services/media.py:246`, `src/api/lidarr.py:77`)
- [ ] **F054** Remove the `albumFolder` key, the wizard prompt, the config line and the test (`src/api/lidarr.py:175`, `:197`; `src/setup/prompts.py:291`; `config_example.yaml:71`)
- [ ] **F055** Drop the coverartarchive and audioscrobbler fallbacks. Use a real year field or omit the year (`src/services/media.py:186-196`)
- [ ] **F056** Fall back to `trackFiles[0].quality` and test it (`src/models/webhook.py:211`)

## Acceptance criteria

Each test below fails before the fix and passes after it. Fixtures use the shapes from the Lidarr OpenAPI spec.

- **F051** `tests/test_api/test_lidarr.py`: `add_artist(..., future_albums=False)` sends a POST body with `monitorNewItems == "none"`.
- **F052** `tests/test_api/test_lidarr.py`: the `lidarr:` lookup returns `[]` and the free-text lookup returns an artist with another `foreignArtistId`. `add_artist` returns `(False, "Artist not found")` and sends no POST. `get_artist` returns `None` in the same case.
- **F050** `tests/test_services/test_media_service.py`: `get_artist_albums` searches by the artist name, not the MBID. From results of two artists it returns only the albums of the picked artist.
- **F053** The song extraction, `get_album_tracks`, its fixture and its 4 tests are gone. No new test.
- **F054** `tests/test_api/test_lidarr.py`: the POST body has no `albumFolder` key. `tests/test_setup/test_prompts.py` no longer expects the prompt.
- **F055** `tests/test_services/test_media_service.py`: an artist without images gets `poster` `None`. The year comes from a real field or is left out.
- **F056** `tests/test_models/test_webhook_models.py`: a Lidarr Download payload with `trackFiles[0].quality` and no `release.quality` yields that quality.
- `pytest`, `flake8` and `mypy src/` pass.

## Notes

- Source: audit 2026-10-28, docs/issues/audit-2026-10-28/FINDINGS.md (F-ids F051, F052, F050, F053, F054, F055, F056).
- Priority: max P 40, sum P 145 (critical).
- Dependencies: slices 1-8 go first. F246 (slice 21) moves the Lidarr fixtures (`tracks`, `statistics.yearStart`) to spec shapes together with this slice.
- Related: #103 (Lidarr album track details in search results). F053 removes the broken track code that #103 is about.
- No owner decision needed.
