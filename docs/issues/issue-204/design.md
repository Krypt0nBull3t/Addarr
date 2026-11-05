# Issue 204 design: Radarr and Sonarr calls match the Servarr specs

**Issue:** https://github.com/Krypt0nBull3t/Addarr/issues/204 (F040 to F045)

## Decisions (approved by the developer through the orchestrator)

- **F042 (Q1 a):** `get_movie` and `get_series` make one `lookup?term=` call and drop the dead direct path. The add flow reads seasons from `series["seasons"]`, so `get_seasons` leaves the add flow. `add_movie` and `add_series` take an optional `lookup` dict and skip their own lookup when the caller passes it. When the caller passes nothing, they look up as before.
- **F041 (Q2 a):** The keyboard, the callback data and the history handler keep the string names `grabbed`, `downloadFolderImported` and `downloadFailed`. The API clients map them to the spec ints 1, 3 and 4. The API client owns the wire format.
- **F044 (Q3 a):** The series card drops the studio line and shows `Network: <network>`. The movie card keeps `Studio:`, because a Radarr movie has a real `studio` field.
- **F044 (Q4 a):** The series rating shows as `Rating`, not `TMDB`. Sonarr `ratings.value` states no source.
- **F043:** Docs only. README and `config_example.yaml` say that Sonarr v4 is required. `src/api/sonarr.py` `add_series` stays as is for v3.

## Non-goals

- No `languageProfileId` code path for Sonarr v3.
- No include flag on Radarr `wanted/missing`, `wanted/cutoff` or `calendar`: they return movie objects directly. The `arr-api-contract-checker` agent confirms this against the spec in create-pr.
- No change to fixtures beyond the shapes this fix touches. Slice #216 (F246) moves the rest to spec shapes.
