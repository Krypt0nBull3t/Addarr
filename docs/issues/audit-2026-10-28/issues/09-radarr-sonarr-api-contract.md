---
title: "Radarr and Sonarr API calls miss data and hit missing endpoints"
labels: [bug, agent-ready, priority:high]
slice: 9
findings: [F040, F041, F042, F043, F044, F045]
---
## Bug

Several Radarr and Sonarr calls do not match the official Servarr OpenAPI specs.

- **F040** The queue, history, wanted/missing, cutoff and calendar calls do not send `includeSeries`, `includeEpisode` or `includeMovie`. The spec default is false. Radarr history titles are "" and Sonarr rows have no series name.
- **F041** The history filter tabs send `eventType=grabbed`, `downloadFolderImported` and `downloadFailed`. The spec wants an int array, so the filtered tabs are empty.
- **F043** On Sonarr v3, `add_series` sends no `languageProfileId`. Sonarr answers "Language profile does not exist".
- **F042** `movie/lookup/tmdb/{id}` and `series/lookup/tvdb/{id}` do not exist. Every add gets a 404 and an ERROR log line. One series add makes 1 failing lookup and 3 identical lookups.
- **F044** Sonarr has no `ratings.tmdb` and no `studio`. The series card always shows an N/A rating and "Network: AMC (N/A)".
- **F045** `remotePoster` is already a full URL. When `images` has no poster, the code adds a second prefix.

## Steps to reproduce

1. **F040** With Radarr, open /history: movie rows have an empty title. With Sonarr, open /queue, /missing, /history or /upcoming: rows have no series name.
2. **F041** Open /history and tap Grabbed, Imported or Failed. The list is empty, although the All tab shows such events.
3. **F043** Connect Sonarr v3. Search a series and add it. Sonarr answers "Language profile does not exist".
4. **F042** Add a movie or a series. The log has a 404 ERROR for `movie/lookup/tmdb/{id}` or `series/lookup/tvdb/{id}`.
5. **F044** Search a series. The card shows the rating as N/A and "Network: AMC (N/A)".
6. **F045** Search a title whose lookup result has `remotePoster` but no poster in `images`. The poster URL has two prefixes and does not load.

## Expected behavior

History, queue, missing, cutoff and calendar rows show the movie or series name. The filter tabs show the matching events. README and config_example.yaml say that Sonarr v4 is required. Each add makes one lookup and no failing call. The series card shows the real rating and no fake studio. Posters load.

## Fix

- [ ] **F040** Add the `includeSeries`/`includeEpisode`/`includeMovie` flags to the 7 query strings (`src/api/sonarr.py:175`, `:195`, `:215`, `:255`, `:274`; `src/api/radarr.py:184`, `:263`)
- [ ] **F041** Map the filter tabs to the spec's int event types 1, 3, 4 (`src/bot/keyboards.py:1114-1117`, `src/api/radarr.py:267`, `src/api/sonarr.py:278`)
- [ ] **F043** Document "Sonarr v4 required" in `README.md` and `config_example.yaml`. No code change for Sonarr v3 (`src/api/sonarr.py:116-125` stays as is)
- [ ] **F042** Call `lookup?term=tmdb:` / `lookup?term=tvdb:` once and pass the result on (`src/api/radarr.py:63`, `src/api/sonarr.py:106`, `:151`, `src/services/media.py:350-354`)
- [ ] **F044** Read `ratings.value`; drop the studio line (`src/services/media.py:147`, `:151`, `src/bot/handlers/media/formatters.py:142-150`)
- [ ] **F045** Use `remotePoster` as is (`src/services/media.py:96-101`, `:136-145`)

## Acceptance criteria

Each test fails before its fix and passes after:

- **F040** `tests/test_api/test_sonarr.py` and `tests/test_api/test_radarr.py` assert that each of the 7 request URLs carries its include flag.
- **F041** `tests/test_api/test_radarr.py` and `tests/test_api/test_sonarr.py` assert that the Grabbed, Imported and Failed tabs send `eventType` 1, 3 and 4.
- **F043** Docs only, no test. `README.md` and the Sonarr section of `config_example.yaml` say "Sonarr v4 required".
- **F042** `tests/test_api/test_radarr.py` and `tests/test_api/test_sonarr.py`: no request goes to `movie/lookup/tmdb/` or `series/lookup/tvdb/`. `tests/test_services/test_media_service.py`: one series add makes one lookup request.
- **F044** `tests/test_services/test_media_service.py`: a Sonarr result with `ratings.value` gives that rating. `tests/test_handlers/test_media_formatters.py`: the network line has no "(N/A)".
- **F045** `tests/test_services/test_media_service.py`: for Radarr and Sonarr, a full `remotePoster` URL with no poster in `images` comes back unchanged.
- `pytest`, `flake8` and `mypy src/` pass.

## Notes

- Source: audit 2026-10-28, docs/issues/audit-2026-10-28/FINDINGS.md (F-ids F040, F041, F042, F043, F044, F045).
- Priority: max P 35, sum P 120 (high).
- Order: do slices 1-8 first. Slice 21 (F246) moves the test fixtures to spec shapes (Sonarr `ratings.tmdb` and `studio`) together with this slice.
- Decided 2026-10-28: F043 document "Sonarr v4 required" in README and config_example.yaml. No code change for v3.
