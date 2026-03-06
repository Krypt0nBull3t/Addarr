# TASKS — Issue #136: Integration Test Harness

> **Issue:** [#136](https://github.com/Krypt0nBull3t/Addarr/issues/136)
> **Branch:** `feature/136-integration-test-harness`
> **Plan:** [plan.md](plan.md)

---

### Phase 1: Core Harness Infrastructure (2 tasks)

**Goal:** Build the `BotHarness` class that can construct a real PTB `Application`, process `Update` objects through the handler chain, and capture bot responses — validated with a `/start` smoke test.

- [x] **1.1** Build BotHarness with response capture and Update factories
    - **Context:** See plan.md "Design Decisions" sections 1–3. The harness builds a real `Application` via `Application.builder().token("test").build()`, registers handlers using the same logic as `AddarrBot._add_handlers()` (`src/main.py:106-188`), and intercepts outgoing API calls by patching `Bot._do_post`. Update objects are constructed via `Update.de_json(data, bot)` with dicts matching Telegram's wire format.
    - **Watch out:**
        - `Application.builder().token("test")` — PTB validates token format, may need `"0:test"` or similar dummy that passes the regex
        - `Bot._do_post` is the low-level hook — confirm this is the right interception point in PTB v20+ (may be `Bot._post` or `Bot.do_api_request`)
        - Callback updates need a `message` field (the message the inline keyboard was on) — handlers call `query.message.edit_text()`
        - The existing `conftest.py` mock config injection must work with the real `Application` (it should — handlers import config at module level, already intercepted)
        - `AuthHandler._authenticated_users` must be pre-seeded for non-auth tests
    - **Scope:** `tests/integration/__init__.py`, `tests/integration/conftest.py` (BotHarness, BotResponse dataclass, update factories, application builder fixture)
    - **Touches:** `tests/integration/conftest.py` (new), `tests/integration/__init__.py` (new)
    - **Action items:**
        - [RED] Write smoke test: `test_start_command_returns_response` — sends `/start` to a fully wired Application, asserts bot sent a `sendMessage` response containing menu text
        - [RED] Write test: `test_unknown_command_no_crash` — sends `/nonexistent`, asserts no error raised
        - [RED] Write test: `test_harness_captures_multiple_responses` — verifies `harness.responses` collects all API calls from a single update
        - [GREEN] Implement `BotResponse` dataclass with `method`, `text`, `chat_id`, `reply_markup`, `photo` fields
        - [GREEN] Implement update factory functions: `make_text_update()`, `make_command_update()`, `make_callback_update()` using `Update.de_json()`
        - [GREEN] Implement `BotHarness` class: builds Application, registers handlers, patches Bot transport, exposes `send_command()`, `send_text()`, `tap_button()`, `responses`, `last_response`
        - [GREEN] Implement `harness` pytest fixture that builds and initializes the Application
    - **Success:** Smoke tests pass — `/start` returns a recognizable response, harness captures it, no real network calls made
    - **Completed:** 2026-03-06
    - **Learnings:**
        - PTB v22 `TelegramObject` is frozen — can't patch `Bot._do_post` directly. Must intercept at `HTTPXRequest.do_request` level instead
        - `do_request` returns `(status_code, bytes)` — response must be wrapped as `{"ok": true, "result": ...}` JSON
        - `Application.initialize()` calls `getMe` — transport patch must be in place before init
        - Token format `"0:TEST"` passes PTB's builder validation
        - `_FAKE_RESULTS` dict needs a `getMe` entry returning bot info for initialize to work
    - **Key Changes:**
        - Created `tests/integration/__init__.py`
        - Created `tests/integration/conftest.py` — BotHarness class, BotResponse dataclass, update factories, harness fixture
        - Created `tests/integration/test_smoke.py` — 3 smoke tests (start command, unknown command, multiple response capture)
    - **Notes:** PTB warnings about `per_message=False` on ConversationHandlers are pre-existing and benign

- [x] **1.2** Add conversation state inspection and auth pre-seeding
    - **Context:** See plan.md sections 5–6. Most integration tests need an authenticated user. `AuthHandler._authenticated_users` (class-level `set` in `src/bot/handlers/auth.py:58`) must be pre-seeded. Conversation state is tracked in `ConversationHandler._conversations` dict, keyed by `(chat_id, user_id)` tuple.
    - **Watch out:**
        - `@require_auth` decorator (`auth.py:37-51`) checks `AuthHandler.is_authenticated()` — if user not in set, it replies with "Not Authorized" and returns `None` (skips handler), which may not be `ConversationHandler.END`
        - Singleton reset in `conftest.py` already clears `AuthHandler._authenticated_users` between tests
        - Conversation state key format may vary — check PTB v20 docs for `ConversationHandler._conversations` key structure
    - **Scope:** Auth fixture, state inspection helper on BotHarness
    - **Touches:** `tests/integration/conftest.py`
    - **Action items:**
        - [RED] Write test: `test_unauthenticated_user_blocked` — sends `/movie` without auth, asserts "authenticate" in response
        - [RED] Write test: `test_authenticated_user_proceeds` — sends `/movie` with pre-seeded auth, asserts "Title" prompt in response (entering SEARCHING state)
        - [RED] Write test: `test_conversation_state_after_command` — sends `/movie`, checks harness reports conversation is in SEARCHING state
        - [GREEN] Add `authenticated_user_id` parameter to harness fixture that pre-seeds `AuthHandler._authenticated_users`
        - [GREEN] Add `get_conversation_state(handler_name, chat_id, user_id)` method to BotHarness
    - **Success:** Auth gating works in integration tests, conversation state is inspectable
    - **Completed:** 2026-03-06
    - **Learnings:**
        - Auth pre-seeding was already implemented in task 1.1 (harness fixture adds user 12345 to `AuthHandler._authenticated_users`) — test for unauthenticated just discards that user
        - PTB `ConversationHandler._conversations` uses `(chat_id, user_id)` tuple as key, stores state as plain int (not tuple) in PTB v22
        - `require_auth` returns `None` when user not authenticated, which prevents ConversationHandler from entering any state
    - **Key Changes:**
        - Added `get_conversation_state(handler_name, chat_id, user_id)` method to `BotHarness` in `tests/integration/conftest.py`
        - Created `tests/integration/test_auth_gating.py` with 3 tests (unauth blocked, auth proceeds, state inspection)
    - **Notes:** ConversationHandler state is stored as plain int, but code handles tuple case defensively for PTB version compatibility

---

### Phase 2: API Mock Helpers (1 task)

**Goal:** Friendly `aioresponses` wrappers for Radarr, Sonarr, and Lidarr APIs that make test setup concise and readable.

- [ ] **2.1** Build API mock helpers for Radarr, Sonarr, Lidarr
    - **Context:** See plan.md section 4. API clients use `BaseApiClient._make_request()` (`src/api/base.py:131`) which calls `session.request(method, url)` via `aiohttp`. URL pattern: `http://localhost:{port}/api/v3/{endpoint}` with `X-Api-Key` header. Each mock helper wraps `aioresponses` to register URL patterns for search, quality profiles, root folders, and add endpoints. Radarr port 7878, Sonarr 8989, Lidarr 8686 (from `conftest.py` mock config).
    - **Watch out:**
        - `aioresponses` must be installed as test dependency — check if it's already in requirements or test deps
        - URL construction: `base.py:145` builds `{base_url}/api/v3/{endpoint}` — mock URLs must match exactly
        - Radarr search endpoint: `movie/lookup?term=...` (`radarr.py:47`), Sonarr: `series/lookup?term=...`, Lidarr: `artist/lookup?term=...`
        - Quality profile endpoints: `qualityprofile` for all three
        - Root folder endpoints: `rootfolder` for all three
        - Add endpoints: `movie` (POST) for Radarr, `series` (POST) for Sonarr, `artist` (POST) for Lidarr
        - Each service's `_make_request` does retries — mock should return 200 on first call
    - **Scope:** `tests/integration/api_mocks.py` — `RadarrMockHelper`, `SonarrMockHelper`, `LidarrMockHelper` classes + fixtures
    - **Touches:** `tests/integration/api_mocks.py` (new), `tests/integration/conftest.py` (add fixtures)
    - **Action items:**
        - [RED] Write test: `test_radarr_mock_search_returns_results` — uses mock helper, calls `RadarrClient().search("inception")`, asserts results returned
        - [RED] Write test: `test_sonarr_mock_quality_profiles` — uses mock helper, calls quality profile endpoint, asserts profiles returned
        - [RED] Write test: `test_mock_helper_defaults_return_empty_search` — verifies `set_defaults()` returns empty search results
        - [GREEN] Implement `BaseMockHelper` with `set_defaults()`, URL builder from mock config
        - [GREEN] Implement `RadarrMockHelper` with `search_returns()`, `quality_profiles()`, `root_folders()`, `add_returns()`
        - [GREEN] Implement `SonarrMockHelper` and `LidarrMockHelper` following same pattern
        - [GREEN] Add `mock_radarr`, `mock_sonarr`, `mock_lidarr` fixtures to integration conftest
    - **Success:** API mock helpers correctly intercept aiohttp calls, tests pass without network access

---

### Phase 3: Media Flow Tests (2 tasks)

**Goal:** Full conversation flow tests for all three media types, including the happy path and edge cases.

- [ ] **3.1** Movie flow: search → select → quality → added
    - **Context:** Movie flow uses `MediaHandler` (`src/bot/handlers/media/handler.py`). States: `/movie` → SEARCHING → user types query → `handle_search` calls `MediaService.search_movies()` → SELECTING → user taps `select_{id}` → `handle_selection` calls `MediaService.add_movie()` → if quality selection needed, returns dict with `type: "quality_selection"` → QUALITY_SELECT → user taps `quality_{id}` → `handle_quality_selection` calls `add_movie_with_profile()` → END. The `@require_auth` and `@rate_limit` decorators wrap entry points.
    - **Watch out:**
        - `handle_selection` (`handler.py:386`) matches result by `r["id"] == selection` where selection is the string after `select_` — mock search results must have an `id` field matching
        - `add_movie()` returns either `(success, message)` tuple or `dict(type="quality_selection", profiles=[...], root_folder=...)` — the flow branches on this
        - `show_result()` in `formatters.py` sends a `reply_photo` if the result has a poster URL, otherwise `reply_text` — mock results should include/exclude `remotePoster` to test both paths
        - `rate_limit` decorator may interfere — may need to disable or mock `RateLimitService`
    - **Scope:** `tests/integration/test_media_flow.py` — movie happy path, no results, cancel at each stage
    - **Touches:** `tests/integration/test_media_flow.py` (new)
    - **Action items:**
        - [RED] Write test: `test_movie_happy_path` — `/movie` → type "inception" → tap `select_{id}` → tap `quality_{id}` → assert "added" in response
        - [RED] Write test: `test_movie_no_results` — `/movie` → type "xyznonexistent" → assert "No movie found" in response, conversation ends
        - [RED] Write test: `test_movie_cancel_at_search` — `/movie` → tap `menu_cancel` → assert cancelled message
        - [RED] Write test: `test_movie_cancel_at_selection` — search → results shown → tap `select_cancel` → assert cancelled
        - [RED] Write test: `test_movie_cancel_at_quality` — select result → quality shown → tap `quality_cancel` → assert cancelled
        - [GREEN] Wire up API mocks for Radarr search, quality profiles, root folders, and add endpoints in each test
        - [GREEN] Fix any harness issues discovered during first real conversation flow test
    - **Success:** All movie flow tests pass, conversation states transition correctly, responses contain expected text

- [ ] **3.2** Series and music flows with type-specific steps
    - **Context:** Series flow adds a SEASON_SELECT state after QUALITY_SELECT (`handler.py:529-566`). Season keyboard has "Monitor All", "All Seasons", "Future Seasons", "Future Episodes", plus individual season buttons. User selects seasons then taps `season_confirm`. Music flow adds ALBUM_SELECT state for artist searches — shows album monitor mode keyboard (`get_album_monitor_mode_keyboard()` in `keyboards.py`). Album/song searches skip album selection and add directly.
    - **Watch out:**
        - Series `quality_data` must include `"seasons"` key for season picker to appear
        - Season selection uses `SeasonPickerMixin` (`season_picker.py`) — `handle_season_selection` toggles seasons in `context.user_data["selected_seasons"]` set
        - Music `selected` result must have `music_type` field ("artist", "album", or "song") to route correctly
        - Lidarr add uses `artist_id`, not the result `id` directly — mock data must include both
    - **Scope:** `tests/integration/test_media_flow.py` — series and music happy paths
    - **Touches:** `tests/integration/test_media_flow.py`
    - **Action items:**
        - [RED] Write test: `test_series_happy_path` — `/series` → search → select → quality → season select → confirm → added
        - [RED] Write test: `test_series_monitor_all` — select "Monitor All" then confirm, assert correct add call
        - [RED] Write test: `test_music_artist_happy_path` — `/music` → search → select artist → quality → album monitor mode → added
        - [RED] Write test: `test_music_album_direct_add` — `/music` → search → select album result → quality → added (no album picker)
        - [GREEN] Add Sonarr and Lidarr mock data with correct field shapes (seasons, music_type, artist_id)
        - [GREEN] Fix any state transition issues discovered
    - **Success:** Series season picker and music album picker work end-to-end in integration tests

---

### Phase 4: Auth and Cancel Flow Tests (1 task)

**Goal:** Test the authentication conversation flow and systematic cancel-at-every-stage coverage.

- [ ] **4.1** Auth flow and comprehensive cancel tests
    - **Context:** Auth flow: `AuthHandler` (`src/bot/handlers/auth.py:54`) uses ConversationHandler with PASSWORD state. Entry via `/auth` command. User types password, checked against `config["telegram"]["password"]` (mock: "test-pass"). On success, user ID added to `_authenticated_users` and persisted to config.yaml (mocked via MockConfig.save()). Cancel tests: every ConversationHandler state should handle `menu_cancel` callback or `/cancel` command gracefully.
    - **Watch out:**
        - Auth handler writes to `config.yaml` via `yaml.dump` — must mock file I/O or the `CONFIG_PATH` constant
        - `register_commands_for_chat` is called after successful auth — needs `application.bot.set_my_commands` to not fail
        - The `/start` handler checks auth and shows different menus for authenticated vs unauthenticated users
    - **Scope:** `tests/integration/test_auth_flow.py`, `tests/integration/test_cancel_flow.py`
    - **Touches:** `tests/integration/test_auth_flow.py` (new), `tests/integration/test_cancel_flow.py` (new)
    - **Action items:**
        - [RED] Write test: `test_auth_correct_password` — unauthenticated user sends `/auth` → types "test-pass" → assert authenticated
        - [RED] Write test: `test_auth_wrong_password` — sends wrong password → assert not authenticated, appropriate message
        - [RED] Write test: `test_auth_then_movie` — authenticate → then `/movie` → assert enters SEARCHING (not blocked)
        - [RED] Write test: `test_cancel_movie_at_every_state` — parametrized test cancelling at SEARCHING, SELECTING, QUALITY_SELECT stages
        - [RED] Write test: `test_cancel_command_fallback` — send `/cancel` during conversation, assert conversation ends
        - [GREEN] Mock config.yaml file writes in auth handler
        - [GREEN] Mock `register_commands_for_chat` to prevent bot API calls during auth
        - [GREEN] Implement any missing harness helpers discovered during these tests
    - **Success:** Full auth round-trip works, cancel is tested at every conversation stage

---

### Phase 5: Downloads Flow Tests (1 task)

**Goal:** Test the `/downloads` unified dashboard with Transmission and SABnzbd.

- [ ] **5.1** Downloads dashboard integration tests
    - **Context:** `DownloadsHandler` (`src/bot/handlers/downloads.py`) uses `CommandHandler` + multiple `CallbackQueryHandler`s (not a ConversationHandler). It checks `is_enabled()` on both Transmission and SABnzbd services. Callbacks: `dl_client_*` (tab switch), `dl_tab_*` (queue/history), `dl_page_*` (pagination), `dl_pause_*`/`dl_resume_*` (item control), `dl_pauseall`/`dl_resumeall`, `dl_refresh`. Transmission uses sync `requests.post` (not aiohttp). SABnzbd uses aiohttp via `BaseApiClient`.
    - **Watch out:**
        - Transmission uses `requests.post` (sync) — mock with `unittest.mock.patch("requests.post")`, not aioresponses
        - Config must enable transmission/sabnzbd (`enable: True`) for handlers to register — need to override mock config
        - `DownloadsHandler.__init__` checks `is_enabled()` at construction time — config override must happen before handler init
        - Downloads handler is NOT a ConversationHandler — no state machine, just standalone handlers matched by callback pattern
    - **Scope:** `tests/integration/test_downloads_flow.py`
    - **Touches:** `tests/integration/test_downloads_flow.py` (new)
    - **Action items:**
        - [RED] Write test: `test_downloads_command_shows_queue` — `/downloads` with Transmission enabled, assert queue displayed
        - [RED] Write test: `test_downloads_sabnzbd_queue` — `/downloads` with SABnzbd enabled, assert SABnzbd queue displayed
        - [RED] Write test: `test_downloads_client_switch` — both clients enabled, tap `dl_client_transmission` then `dl_client_sabnzbd`, verify tab switch
        - [RED] Write test: `test_downloads_refresh` — tap `dl_refresh`, assert queue re-fetched
        - [GREEN] Create config override fixture that enables Transmission and/or SABnzbd
        - [GREEN] Mock Transmission `requests.post` responses (queue, torrent list)
        - [GREEN] Mock SABnzbd aiohttp responses (queue, history)
        - [GREEN] Build harness variant that re-registers handlers with download-enabled config
    - **Success:** Downloads dashboard works with both clients, tab switching and refresh verified
