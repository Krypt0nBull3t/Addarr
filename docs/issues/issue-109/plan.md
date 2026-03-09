# External Links in Search Results — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add clickable IMDB/TMDB/TVDB/MusicBrainz links to search result captions so users can research media before adding it.

**Architecture:** Two-layer change — (1) expose external IDs in the normalized result dict during search normalization, (2) build a links line in the caption formatter. No new dependencies, no config changes, no i18n keys.

**Tech Stack:** Python, python-telegram-bot Markdown formatting (`[text](url)`)

---

## Context

### Current State
- Search results are normalized in `src/services/media.py` into dicts with fields like `id`, `title`, `overview`, `poster`, `ratings`, `data` (raw API response)
- Captions are built by `build_result_caption()` in `src/bot/handlers/media/formatters.py`
- External IDs exist in the raw API data (`result["data"]`) but aren't surfaced in the normalized dict

### Design Decision: Surface IDs in Normalization
Rather than reaching into `result["data"]` in the formatter (coupling formatter to raw API structure), we'll add `external_ids` to the normalized result dict in `media.py`. This keeps the formatter clean and testable.

### URL Templates
| Service | URL Pattern |
|---------|-------------|
| IMDB | `https://www.imdb.com/title/{imdbId}/` |
| TMDB (movie) | `https://www.themoviedb.org/movie/{tmdbId}` |
| TMDB (series) | `https://www.themoviedb.org/tv/{tmdbId}` (uses tmdb rating votes ID from Sonarr) |
| TVDB | `https://thetvdb.com/?id={tvdbId}&tab=series` |
| MusicBrainz (artist) | `https://musicbrainz.org/artist/{foreignArtistId}` |
| MusicBrainz (album) | `https://musicbrainz.org/release-group/{foreignAlbumId}` |

### Telegram Markdown Links
Telegram Markdown v1 (used by this codebase): `[Link Text](url)`

Special characters in URLs don't need escaping since URLs don't contain Markdown-special chars. The link line will be appended before the result counter.

---

## Task 1: Add `external_ids` to Movie Normalization

**Files:**
- Modify: `src/services/media.py:108-135` (search_movies normalization)
- Modify: `tests/fixtures/sample_data.py:1-26` (add imdbId to Radarr fixtures)
- Test: `tests/test_services/test_media_service.py`

**What:** Add an `external_ids` dict to the normalized movie result containing `imdbId` and `tmdbId`.

**Normalization change** (inside the list comprehension in `search_movies`):
```python
"external_ids": {
    "imdb": movie.get("imdbId"),
    "tmdb": movie.get("tmdbId"),
},
```

**Fixture change** — add `"imdbId": "tt0137523"` to Fight Club and `"imdbId": "tt0110912"` to Pulp Fiction in `RADARR_SEARCH_RESULTS`.

**Test:** Assert `external_ids` is present and correct in normalized movie results.

---

## Task 2: Add `external_ids` to Series Normalization

**Files:**
- Modify: `src/services/media.py:140-176` (search_series normalization)
- Modify: `tests/fixtures/sample_data.py:52-86` (add imdbId to Sonarr fixtures)
- Test: `tests/test_services/test_media_service.py`

**What:** Add an `external_ids` dict to the normalized series result containing `tvdbId` and optionally `imdbId`.

**Normalization change** (inside the list comprehension in `search_series`):
```python
"external_ids": {
    "tvdb": series.get("tvdbId"),
    "imdb": series.get("imdbId"),
},
```

**Fixture change** — add `"imdbId": "tt0903747"` to Breaking Bad in `SONARR_SEARCH_RESULTS`. Severance gets no `imdbId` (tests the optional case).

**Test:** Assert `external_ids` is present, `tvdb` is always set, `imdb` is `None` when absent.

---

## Task 3: Add `external_ids` to Music Normalization

**Files:**
- Modify: `src/services/media.py:181-267` (search_music normalization — artists, albums, songs)
- Test: `tests/test_services/test_media_service.py`

**What:** Add `external_ids` to all three music result types.

**Artist normalization:**
```python
"external_ids": {
    "musicbrainz": artist.get("foreignArtistId"),
},
```

**Album normalization:**
```python
"external_ids": {
    "musicbrainz": album.get("foreignAlbumId"),
},
```

**Song normalization:**
```python
"external_ids": {
    "musicbrainz": album.get("foreignAlbumId"),
},
```

**Test:** Assert `external_ids.musicbrainz` matches the expected MusicBrainz ID for each music type.

---

## Task 4: Build External Links in Formatter

**Files:**
- Modify: `src/bot/handlers/media/formatters.py:23-119` (build_result_caption)
- Test: `tests/test_handlers/test_media_formatters.py`

**What:** Add a `_build_external_links()` helper and call it from `build_result_caption()` to append a links line before the result counter.

**New helper function** (in formatters.py, before `build_result_caption`):
```python
def _build_external_links(result):
    """Build a line of clickable external links for a search result.

    Returns an empty string if no external IDs are available.
    """
    external_ids = result.get("external_ids", {})
    if not external_ids:
        return ""

    music_type = result.get("music_type")
    links = []

    imdb_id = external_ids.get("imdb")
    if imdb_id:
        links.append(f"[IMDB](https://www.imdb.com/title/{imdb_id}/)")

    tmdb_id = external_ids.get("tmdb")
    if tmdb_id:
        links.append(f"[TMDB](https://www.themoviedb.org/movie/{tmdb_id})")

    tvdb_id = external_ids.get("tvdb")
    if tvdb_id:
        links.append(f"[TVDB](https://thetvdb.com/?id={tvdb_id}&tab=series)")

    mb_id = external_ids.get("musicbrainz")
    if mb_id:
        if music_type == "artist":
            mb_url = f"https://musicbrainz.org/artist/{mb_id}"
        else:
            mb_url = f"https://musicbrainz.org/release-group/{mb_id}"
        links.append(f"[MusicBrainz]({mb_url})")

    if not links:
        return ""

    return "🔗 " + " | ".join(links) + "\n"
```

**Integration into `build_result_caption`:**

For album captions (line ~48, before the counter):
```python
caption += _build_external_links(result)
```

For song captions (line ~60, before the counter):
```python
caption += _build_external_links(result)
```

For movie/series captions (line ~115, after genres, before counter):
```python
caption += _build_external_links(result)
```

**Tests to add:**
1. Movie with both IMDB and TMDB links
2. Series with TVDB and IMDB links
3. Series with TVDB only (no IMDB)
4. Album with MusicBrainz link (release-group URL)
5. Artist with MusicBrainz link (artist URL)
6. Song with MusicBrainz link
7. Result with no `external_ids` key (graceful no-op)
8. Result with empty `external_ids` dict (graceful no-op)

---

## Task 5: Update Sample Data Fixtures

**Files:**
- Modify: `tests/fixtures/sample_data.py`

**What:** Ensure all Radarr and Sonarr sample data includes `imdbId` fields so that any test using these fixtures gets realistic data. This was partially done in Tasks 1-2 for search results; this task covers `RADARR_MOVIE_DETAIL`, `SONARR_SERIES_DETAIL`, and any other fixtures that should have the field.

---

## Verification

After all tasks:
1. `pytest --tb=short -q` — full suite passes
2. `pytest --cov=src.bot.handlers.media.formatters --cov=src.services.media --cov-report=term-missing` — 100% on changed lines
3. `python -m flake8 .` — no lint errors
4. Manual review: captions include clickable links in correct Markdown format
