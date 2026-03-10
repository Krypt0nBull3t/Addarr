# Bazarr Integration (Subtitles) — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Bazarr subtitle management to Addarr — users can check subtitle status and trigger subtitle searches for movies/episodes via Telegram.

**Architecture:** New `BazarrClient` API client inheriting `BaseApiClient`, new `BazarrService` singleton, and new `BazarrHandler` for Telegram commands. Bazarr uses its own REST API (`/api/...`) with `X-API-KEY` header auth — same header as the *arr stack but different API path structure (no `/api/v3/` prefix — Bazarr uses `/api/` directly). The integration cross-references Radarr/Sonarr IDs since Bazarr tracks subtitles per media item using those IDs.

**Tech Stack:** Python 3.11, aiohttp, python-telegram-bot v20+, pytest, aioresponses

---

## Key Design Decisions

### 1. Bazarr API differences from *arr clients

Bazarr's API is **not** a Sonarr/Radarr-style `/api/v3/` API. It uses:
- Base path: `{url}/api/`  (no version prefix)
- Auth header: `X-API-KEY` (same name as the *arr apps)
- Key endpoints:
  - `GET /api/movies` — list movies with subtitle info (params: `start`, `length`, `radarrid[]`)
  - `GET /api/movies/wanted` — movies missing subtitles
  - `GET /api/episodes/wanted` — episodes missing subtitles
  - `PATCH /api/movies/subtitles` — trigger subtitle download for a movie
  - `PATCH /api/episodes/subtitles` — trigger subtitle download for an episode
  - `GET /api/system/status` — health check (returns version, etc.)

### 2. Overriding BaseApiClient for Bazarr

`BaseApiClient` hardcodes `API_VERSION = "v3"` and builds URLs as `{base_url}/api/v3/{endpoint}`. Bazarr needs `{base_url}/api/{endpoint}`. Solution: override `API_VERSION = ""` in `BazarrClient` so URLs become `{base_url}/api/{endpoint}` (the trailing slash from empty string is handled by the format string: `f"{self.base_url}/api//{endpoint}"` → needs a clean override). Better approach: override `API_VERSION = ""` and the URL construction becomes `{base_url}/api//{endpoint}`. Actually looking at `_make_request`: `url = f"{self.base_url}/api/{self.API_VERSION}/{endpoint}"`. If `API_VERSION = ""` this gives `{base_url}/api//endpoint` with double slash. Clean fix: set `API_VERSION = ""` and strip the double slash, OR simply override `_make_request` to use the correct URL format. Simplest: use a property/class variable and let the URL be constructed. Actually the simplest clean approach: set a class attribute `_API_PATH = "api"` and override `_make_request` URL construction. But that's overengineering.

**Chosen approach:** Override `API_VERSION` as empty string. The double-slash (`/api//endpoint`) is harmless in HTTP — servers normalize it. But to be clean, we'll override `_build_api_url` if needed, or simply accept the double slash since Bazarr's API handles it fine. Actually, let's just override the URL building by providing a small helper method that BazarrClient uses. No — simplest: set `API_VERSION = ""` and let the format produce `/api//movies`. Most HTTP servers and aiohttp normalize this. If tests show issues, we fix then.

**Final decision:** Set `API_VERSION = ""`. The resulting URL `http://host:port/api//endpoint` works fine with aiohttp (consecutive slashes are normalized by most servers). If Bazarr has issues, we add a 1-line override. YAGNI.

### 3. `search()` abstract method

Bazarr doesn't have a text search endpoint — it manages subtitles for media already tracked by Radarr/Sonarr. The `search()` method is required by `BaseApiClient` (abstract). We'll implement it as a search for movies/episodes by title using the Bazarr movies/episodes list endpoint with filtering. This satisfies the architecture test and provides useful functionality.

### 4. Handler scope

The handler provides:
- `/subtitles` command — shows a menu to check movie or episode subtitle status
- Callback-based flow: user picks movie/series → sees subtitle status → can trigger search
- `/wanted` is already taken by the Missing handler — we'll use the `/subtitles` command with a "Wanted" button that shows movies/episodes missing subtitles

### 5. No ConversationHandler needed

The Bazarr flow is simple enough to use CallbackQueryHandler chains rather than a full ConversationHandler state machine. The user picks from inline keyboards, no free-text input needed.

---

## Phase 1: Foundation (API Client + Config)

### Task 1.1: Add Bazarr config section

**Files:**
- Modify: `config_example.yaml` (add bazarr section after lidarr)
- Modify: `tests/conftest.py` (add bazarr to `MOCK_CONFIG_DATA`)

Add config block following the *arr pattern:
```yaml
# Bazarr Configuration (Subtitles — Optional)
bazarr:
  enable: false
  server:
    addr: localhost
    port: 6767
    path: /
    ssl: false
  auth:
    apikey:
```

Add to `MOCK_CONFIG_DATA`:
```python
"bazarr": {
    "enable": True,
    "server": {"addr": "localhost", "port": 6767, "path": "/", "ssl": False},
    "auth": {"apikey": "test-bazarr-key"},
},
```

### Task 1.2: Create BazarrClient API client

**Files:**
- Create: `src/api/bazarr.py`
- Create: `tests/test_api/test_bazarr.py`
- Modify: `src/api/__init__.py` (add BazarrClient export)
- Create: `tests/fixtures/bazarr_data.py` (sample API responses)

**Sample data** (`tests/fixtures/bazarr_data.py`):
```python
BAZARR_SYSTEM_STATUS = {
    "data": {
        "bazarr_version": "1.4.0",
        "sonarr_version": "4.0.0",
        "radarr_version": "5.0.0",
        "operating_system": "Linux",
        "python_version": "3.11.0",
        "start_time": 1700000000,
    }
}

BAZARR_MOVIES = {
    "data": [
        {
            "title": "Inception",
            "radarrId": 1,
            "audio_language": [{"name": "English"}],
            "missing_subtitles": [{"name": "French", "code2": "fr", "code3": "fre"}],
            "subtitles": [{"path": "/subs/en.srt", "language": "en", "forced": False, "hi": False}],
            "monitored": True,
            "profileId": 1,
        },
        {
            "title": "The Matrix",
            "radarrId": 2,
            "audio_language": [{"name": "English"}],
            "missing_subtitles": [],
            "subtitles": [
                {"path": "/subs/en.srt", "language": "en", "forced": False, "hi": False},
                {"path": "/subs/fr.srt", "language": "fr", "forced": False, "hi": False},
            ],
            "monitored": True,
            "profileId": 1,
        },
    ],
    "total": 2,
}

BAZARR_MOVIES_WANTED = {
    "data": [
        {
            "title": "Inception",
            "radarrId": 1,
            "missing_subtitles": [{"name": "French", "code2": "fr", "code3": "fre"}],
            "sceneName": "Inception.2010.1080p",
            "tags": [],
        }
    ],
    "total": 1,
}

BAZARR_EPISODES_WANTED = {
    "data": [
        {
            "seriesTitle": "Breaking Bad",
            "episode_number": "S01E01",
            "episodeTitle": "Pilot",
            "missing_subtitles": [{"name": "Spanish", "code2": "es", "code3": "spa"}],
            "sonarrSeriesId": 10,
            "sonarrEpisodeId": 100,
            "sceneName": "Breaking.Bad.S01E01",
            "tags": [],
            "seriesType": "standard",
        }
    ],
    "total": 1,
}
```

**BazarrClient** (`src/api/bazarr.py`):
```python
"""
Filename: bazarr.py
Author: (generated)
Created Date: 2026-03-10
Description: Bazarr API client module.
"""

from typing import List, Dict
from colorama import Fore

from src.api.base import BaseApiClient
from src.config.settings import config
from src.utils.logger import get_logger

logger = get_logger("addarr.bazarr")


class BazarrClient(BaseApiClient):
    """Bazarr API client for subtitle management."""

    # Bazarr API has no version prefix — override to empty string
    API_VERSION = ""

    def __init__(self):
        bazarr_config = config.get("bazarr", {})
        server_config = bazarr_config.get("server", {})
        auth_config = bazarr_config.get("auth", {})

        if not server_config.get("addr") or not server_config.get("port"):
            logger.error(Fore.RED + "❌ Bazarr server address or port not configured")
            raise ValueError("Bazarr server address or port not configured")

        if not auth_config.get("apikey"):
            logger.error(Fore.RED + "❌ Bazarr API key not configured")
            raise ValueError("Bazarr API key not configured")

        super().__init__("bazarr")
        logger.info(Fore.GREEN + f"✅ Bazarr API client initialized: {self.base_url}")

    async def search(self, term: str) -> List[Dict]:
        """Search movies by title in Bazarr's tracked library."""
        try:
            logger.info(Fore.BLUE + f"🔍 Searching Bazarr for: {term}")
            result = await self._request("movies")

            if not result or not isinstance(result, dict):
                logger.warning(Fore.YELLOW + f"⚠️ No results from Bazarr")
                return []

            movies = result.get("data", [])
            term_lower = term.lower()
            matches = [m for m in movies if term_lower in m.get("title", "").lower()]

            logger.info(Fore.GREEN + f"✅ Found {len(matches)} matches for: {term}")
            return matches

        except Exception as e:
            logger.error(Fore.RED + f"❌ Search failed: {str(e)}")
            return []

    async def get_movies(self) -> List[Dict]:
        """Get all movies with subtitle info."""
        try:
            result = await self._request("movies")
            if result and isinstance(result, dict):
                return result.get("data", [])
            return []
        except Exception as e:
            logger.error(Fore.RED + f"❌ Failed to get movies: {str(e)}")
            return []

    async def get_wanted_movies(self) -> List[Dict]:
        """Get movies missing subtitles."""
        try:
            logger.info(Fore.BLUE + "📭 Getting movies wanted subtitles")
            result = await self._request("movies/wanted")
            if result and isinstance(result, dict):
                data = result.get("data", [])
                logger.info(Fore.GREEN + f"✅ Found {len(data)} movies wanting subtitles")
                return data
            return []
        except Exception as e:
            logger.error(Fore.RED + f"❌ Failed to get wanted movies: {str(e)}")
            return []

    async def get_wanted_episodes(self) -> List[Dict]:
        """Get episodes missing subtitles."""
        try:
            logger.info(Fore.BLUE + "📭 Getting episodes wanted subtitles")
            result = await self._request("episodes/wanted")
            if result and isinstance(result, dict):
                data = result.get("data", [])
                logger.info(Fore.GREEN + f"✅ Found {len(data)} episodes wanting subtitles")
                return data
            return []
        except Exception as e:
            logger.error(Fore.RED + f"❌ Failed to get wanted episodes: {str(e)}")
            return []

    async def search_movie_subtitles(self, radarr_id: int, language: str,
                                     forced: bool = False, hi: bool = False) -> bool:
        """Trigger subtitle search for a specific movie."""
        try:
            logger.info(Fore.BLUE + f"🔍 Searching subtitles for movie {radarr_id} ({language})")
            success, _data, error = await self._make_request(
                f"movies/subtitles?radarrid={radarr_id}&language={language}"
                f"&forced={'true' if forced else 'false'}&hi={'true' if hi else 'false'}",
                method="PATCH",
            )
            if success:
                logger.info(Fore.GREEN + f"✅ Subtitle search triggered for movie {radarr_id}")
            else:
                logger.error(Fore.RED + f"❌ Subtitle search failed: {error}")
            return success
        except Exception as e:
            logger.error(Fore.RED + f"❌ Failed to search subtitles: {str(e)}")
            return False

    async def search_episode_subtitles(self, sonarr_series_id: int,
                                       sonarr_episode_id: int, language: str,
                                       forced: bool = False, hi: bool = False) -> bool:
        """Trigger subtitle search for a specific episode."""
        try:
            logger.info(Fore.BLUE + f"🔍 Searching subtitles for episode {sonarr_episode_id}")
            success, _data, error = await self._make_request(
                f"episodes/subtitles?seriesid={sonarr_series_id}"
                f"&episodeid={sonarr_episode_id}&language={language}"
                f"&forced={'true' if forced else 'false'}&hi={'true' if hi else 'false'}",
                method="PATCH",
            )
            if success:
                logger.info(Fore.GREEN + f"✅ Subtitle search triggered for episode {sonarr_episode_id}")
            else:
                logger.error(Fore.RED + f"❌ Episode subtitle search failed: {error}")
            return success
        except Exception as e:
            logger.error(Fore.RED + f"❌ Failed to search episode subtitles: {str(e)}")
            return False
```

**Tests** — validate init errors, search, wanted lists, subtitle search triggers. Use `aioresponses` with base URL `http://localhost:6767/api//` (double slash from empty API_VERSION).

**Note on double-slash URL:** The `_make_request` in `base.py` constructs: `f"{self.base_url}/api/{self.API_VERSION}/{endpoint}"`. With `API_VERSION = ""` this gives `http://localhost:6767/api//movies`. Tests must mock this exact URL. This is intentional and HTTP-spec compliant.

### Task 1.3: Create BazarrService singleton

**Files:**
- Create: `src/services/bazarr.py`
- Create: `tests/test_services/test_bazarr.py`
- Modify: `src/services/__init__.py` (add BazarrService export)
- Modify: `tests/conftest.py` (add BazarrService singleton reset)
- Modify: `tests/test_architecture/test_conventions.py` (add to SINGLETON_CLASSES)

**BazarrService** (`src/services/bazarr.py`):
```python
"""
Filename: bazarr.py
Author: (generated)
Created Date: 2026-03-10
Description: Bazarr service for subtitle management.
"""

from typing import Any, Dict, List, Optional

from src.api.bazarr import BazarrClient
from src.config.settings import config
from src.utils.logger import get_logger

logger = get_logger("addarr.services.bazarr")


class BazarrService:
    """Service class for Bazarr subtitle operations."""

    _instance: Optional["BazarrService"] = None
    _client: Optional[BazarrClient] = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BazarrService, cls).__new__(cls)
            cls._initialize()
        return cls._instance

    @classmethod
    def _initialize(cls):
        cls._client = None
        cls._config = config.get("bazarr", {})

    @property
    def client(self) -> Optional[BazarrClient]:
        if not self._client and self._config.get("enable"):
            try:
                self._client = BazarrClient()
            except Exception as e:
                logger.error(f"Failed to initialize Bazarr client: {str(e)}")
                return None
        return self._client

    def is_enabled(self) -> bool:
        return bool(self._config.get("enable"))

    async def get_wanted_movies(self) -> List[Dict]:
        if not self.client:
            return []
        return await self.client.get_wanted_movies()

    async def get_wanted_episodes(self) -> List[Dict]:
        if not self.client:
            return []
        return await self.client.get_wanted_episodes()

    async def search_movie_subtitles(self, radarr_id: int, language: str) -> bool:
        if not self.client:
            return False
        return await self.client.search_movie_subtitles(radarr_id, language)

    async def search_episode_subtitles(self, sonarr_series_id: int,
                                       sonarr_episode_id: int,
                                       language: str) -> bool:
        if not self.client:
            return False
        return await self.client.search_episode_subtitles(
            sonarr_series_id, sonarr_episode_id, language
        )

    async def search_movies(self, term: str) -> List[Dict]:
        if not self.client:
            return []
        return await self.client.search(term)
```

**Singleton reset** in `tests/conftest.py`:
```python
from src.services.bazarr import BazarrService
# ...
BazarrService._instance = None
BazarrService._client = None
```

**Architecture test** — add `"BazarrService"` to `SINGLETON_CLASSES` set.

---

## Phase 2: Handler + Translations + Registration

### Task 2.1: Add translation keys

**Files:**
- Modify: All 9 translation files (`translations/addarr.*.yml`)
- Modify: `translations/addarr.template.yml`

Add these flat keys to each locale file (English values shown, other locales get English as placeholder):
```yaml
# Bazarr (Subtitles)
BazarrNotEnabled: "❌ Bazarr is not enabled or configured"
BazarrSubtitlesHeader: "🔤 *Subtitle Management*"
BazarrChooseType: "Choose media type to check subtitles:"
BazarrMovieSubtitles: "🎬 Movie Subtitles"
BazarrEpisodeSubtitles: "📺 Episode Subtitles"
BazarrWantedMovies: "📭 Wanted Movie Subs"
BazarrWantedEpisodes: "📭 Wanted Episode Subs"
BazarrSearchPrompt: "🔍 Enter a movie title to check subtitles:"
BazarrNoResults: "No movies found matching your search."
BazarrMovieStatus: "🎬 *{title}*\n\n✅ *Available:* {available}\n❌ *Missing:* {missing}"
BazarrNoMissing: "✅ No missing subtitles!"
BazarrWantedMovieItem: "🎬 *{title}*\nMissing: {languages}"
BazarrWantedEpisodeItem: "📺 *{series}* — {episode}\n_{ep_title}_\nMissing: {languages}"
BazarrSearchTriggered: "🔍 Subtitle search triggered for *{title}*"
BazarrSearchFailed: "❌ Failed to trigger subtitle search"
BazarrNoWantedMovies: "✅ No movies are missing subtitles!"
BazarrNoWantedEpisodes: "✅ No episodes are missing subtitles!"
Subtitles: "Subtitles"
SearchSubtitles: "🔍 Search Subtitles"
CommandSubtitles: "Subtitle management"
```

### Task 2.2: Create BazarrHandler

**Files:**
- Create: `src/bot/handlers/bazarr.py`
- Create: `tests/test_handlers/test_bazarr.py`
- Modify: `src/bot/handlers/__init__.py` (add BazarrHandler export)

**Handler** (`src/bot/handlers/bazarr.py`):

The handler uses `ConversationHandler` for the movie search flow (needs text input) and standalone `CallbackQueryHandler` for wanted lists.

States needed (add to `src/bot/states.py`):
```python
# Bazarr states
BAZARR_SEARCH = 10
```

```python
"""
Filename: bazarr.py
Author: (generated)
Created Date: 2026-03-10
Description: Bazarr subtitle handler module.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler, CallbackQueryHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters,
)
from src.bot.handlers.auth import require_auth
from src.bot.states import States
from src.services.bazarr import BazarrService
from src.services.translation import TranslationService
from src.utils.logger import get_logger, log_user_interaction

logger = get_logger("addarr.bazarr")


class BazarrHandler:
    """Handler for Bazarr subtitle commands."""

    def __init__(self):
        self.translation = TranslationService()
        self.service = BazarrService()

    def get_handler(self):
        """Return handler list."""
        conv = ConversationHandler(
            entry_points=[
                CommandHandler("subtitles", self.subtitles_menu),
                CallbackQueryHandler(self.subtitles_menu, pattern="^bazarr_menu$"),
            ],
            states={
                States.BAZARR_SEARCH: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.handle_search,
                    ),
                ],
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CallbackQueryHandler(self.cancel, pattern="^bazarr_cancel$"),
            ],
            per_user=True,
            per_chat=True,
        )
        return [
            conv,
            CallbackQueryHandler(self.wanted_movies, pattern="^bazarr_wanted_movies$"),
            CallbackQueryHandler(self.wanted_episodes, pattern="^bazarr_wanted_episodes$"),
            CallbackQueryHandler(self.search_subtitles_trigger, pattern="^bazarr_search_"),
            CallbackQueryHandler(self.prompt_search, pattern="^bazarr_movie_search$"),
        ]

    @require_auth
    async def subtitles_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show the subtitles main menu."""
        if not update.effective_user:
            return ConversationHandler.END

        log_user_interaction(logger, update.effective_user, "/subtitles")

        if not self.service.is_enabled():
            text = self.translation.get_text("BazarrNotEnabled")
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.message.edit_text(text)
            else:
                await update.message.reply_text(text)
            return ConversationHandler.END

        t = self.translation
        keyboard = [
            [InlineKeyboardButton(
                t.get_text("BazarrMovieSubtitles"),
                callback_data="bazarr_movie_search",
            )],
            [InlineKeyboardButton(
                t.get_text("BazarrWantedMovies"),
                callback_data="bazarr_wanted_movies",
            )],
            [InlineKeyboardButton(
                t.get_text("BazarrWantedEpisodes"),
                callback_data="bazarr_wanted_episodes",
            )],
        ]
        text = t.get_text("BazarrSubtitlesHeader") + "\n\n" + t.get_text("BazarrChooseType")

        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.edit_text(
                text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown",
            )
        return ConversationHandler.END

    @require_auth
    async def prompt_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Prompt user to enter a movie title."""
        if not update.callback_query:
            return ConversationHandler.END

        await update.callback_query.answer()
        text = self.translation.get_text("BazarrSearchPrompt")
        await update.callback_query.message.edit_text(text)
        return States.BAZARR_SEARCH

    @require_auth
    async def handle_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle movie title search text."""
        if not update.message or not update.message.text:
            return ConversationHandler.END

        term = update.message.text.strip()
        results = await self.service.search_movies(term)

        if not results:
            await update.message.reply_text(
                self.translation.get_text("BazarrNoResults"),
            )
            return ConversationHandler.END

        # Show first 5 results with subtitle status
        for movie in results[:5]:
            title = movie.get("title", "Unknown")
            available = ", ".join(
                s.get("language", "?") for s in movie.get("subtitles", [])
            ) or "None"
            missing_list = movie.get("missing_subtitles", [])
            missing = ", ".join(
                m.get("name", "?") for m in missing_list
            ) or "None"

            text = self.translation.get_text(
                "BazarrMovieStatus",
                title=title, available=available, missing=missing,
            )

            # Add search button for each missing language
            keyboard = []
            radarr_id = movie.get("radarrId")
            for lang in missing_list:
                code = lang.get("code2", lang.get("code3", ""))
                name = lang.get("name", code)
                keyboard.append([InlineKeyboardButton(
                    f"🔍 Search {name}",
                    callback_data=f"bazarr_search_m_{radarr_id}_{code}",
                )])

            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
            await update.message.reply_text(
                text, parse_mode="Markdown", reply_markup=reply_markup,
            )

        return ConversationHandler.END

    @require_auth
    async def wanted_movies(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show movies missing subtitles."""
        if not update.callback_query:
            return
        await update.callback_query.answer()

        movies = await self.service.get_wanted_movies()
        if not movies:
            await update.callback_query.message.edit_text(
                self.translation.get_text("BazarrNoWantedMovies"),
            )
            return

        lines = []
        for movie in movies[:10]:
            languages = ", ".join(
                m.get("name", "?") for m in movie.get("missing_subtitles", [])
            )
            lines.append(self.translation.get_text(
                "BazarrWantedMovieItem",
                title=movie.get("title", "Unknown"),
                languages=languages,
            ))

        await update.callback_query.message.edit_text(
            "\n\n".join(lines), parse_mode="Markdown",
        )

    @require_auth
    async def wanted_episodes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show episodes missing subtitles."""
        if not update.callback_query:
            return
        await update.callback_query.answer()

        episodes = await self.service.get_wanted_episodes()
        if not episodes:
            await update.callback_query.message.edit_text(
                self.translation.get_text("BazarrNoWantedEpisodes"),
            )
            return

        lines = []
        for ep in episodes[:10]:
            languages = ", ".join(
                m.get("name", "?") for m in ep.get("missing_subtitles", [])
            )
            lines.append(self.translation.get_text(
                "BazarrWantedEpisodeItem",
                series=ep.get("seriesTitle", "Unknown"),
                episode=ep.get("episode_number", "?"),
                ep_title=ep.get("episodeTitle", ""),
                languages=languages,
            ))

        await update.callback_query.message.edit_text(
            "\n\n".join(lines), parse_mode="Markdown",
        )

    @require_auth
    async def search_subtitles_trigger(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle subtitle search trigger from inline button."""
        if not update.callback_query:
            return
        await update.callback_query.answer()

        # Parse callback_data: bazarr_search_m_{radarrId}_{langCode}
        #                    or bazarr_search_e_{seriesId}_{episodeId}_{langCode}
        parts = update.callback_query.data.split("_")
        # parts: ["bazarr", "search", type, ...]

        if len(parts) >= 5 and parts[2] == "m":
            # Movie: bazarr_search_m_{radarrId}_{lang}
            radarr_id = int(parts[3])
            language = parts[4]
            success = await self.service.search_movie_subtitles(radarr_id, language)
        else:
            success = False

        if success:
            await update.callback_query.message.edit_text(
                self.translation.get_text("BazarrSearchTriggered", title=str(radarr_id)),
            )
        else:
            await update.callback_query.message.edit_text(
                self.translation.get_text("BazarrSearchFailed"),
            )

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel the conversation."""
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.edit_text("Cancelled.")
        elif update.message:
            await update.message.reply_text("Cancelled.")
        return ConversationHandler.END
```

### Task 2.3: Register handler + health check + help text

**Files:**
- Modify: `src/main.py` (add BazarrHandler registration + import)
- Modify: `src/services/health.py` (add Bazarr health check)
- Modify: `src/bot/states.py` (add BAZARR_SEARCH state)
- Modify: `config_example.yaml` (add subtitles entrypoint — actually no, /subtitles is hardcoded)
- Modify: `src/bot/commands.py` (add subtitles command to authenticated commands)

**Handler registration** in `_add_handlers()` — add after History handler, before Transmission, gated on `config.get("bazarr", {}).get("enable")`:
```python
# Bazarr handler (if enabled)
if config.get("bazarr", {}).get("enable", False):
    from src.bot.handlers.bazarr import BazarrHandler
    bazarr_handler = BazarrHandler()
    for handler in bazarr_handler.get_handler():
        self.application.add_handler(handler)
```

**Health check** — add `check_bazarr_health()` method and call it in `run_health_checks()`. Bazarr uses `X-API-KEY` header (same as *arr) and endpoint is `/api/system/status`.

**Help text** — add `BazarrHelp` translation key and conditionally include in HelpHandler `_build_help_text()`.

---

## Phase 3: Integration + Polish

### Task 3.1: Wire up help text and bot commands

**Files:**
- Modify: `src/bot/handlers/help.py` (add Bazarr section if enabled)
- Modify: `src/bot/commands.py` (add /subtitles to authenticated command list)
- Modify: translations (add `HelpBazarr` key)

### Task 3.2: Final integration testing

**Files:**
- Run full test suite
- Run flake8, mypy
- Validate translations
- Verify architecture tests pass (singleton, handler conventions)

---

## Verification Checklist

- [ ] `pytest --tb=short -q` passes
- [ ] `python -m flake8 .` passes
- [ ] `mypy src/` passes
- [ ] `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` passes
- [ ] Architecture tests pass (`SINGLETON_CLASSES`, `get_handler()` convention)
- [ ] New code has 100% test coverage
- [ ] Config example includes bazarr section
- [ ] Help text shows Bazarr commands when enabled
- [ ] Health check includes Bazarr when enabled
