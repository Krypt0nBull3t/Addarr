# Issue #136: Integration Test Harness for End-to-End Conversation Flow Testing

## Context

Addarr has comprehensive unit tests that call individual handler methods directly with mock objects. However, there's no way to verify that the full conversation wiring works — state transitions, callback pattern matching, handler registration order, and data flow between steps — without deploying the bot to a live environment.

This plan adds an integration test layer that processes real `Update` objects through the actual `python-telegram-bot` handler chain, catching wiring bugs that unit tests can't.

## Target Structure

```
tests/
├── conftest.py                        # existing (unchanged)
├── integration/
│   ├── __init__.py
│   ├── conftest.py                    # BotHarness, response capture, API mock fixtures
│   ├── test_media_flow.py             # movie/series/music: search → select → quality → add
│   ├── test_auth_flow.py              # unauthenticated → password → authenticated → command
│   ├── test_downloads_flow.py         # /downloads with Transmission/SABnzbd tabs
│   └── test_cancel_flow.py            # cancel at every conversation stage
```

## Design Decisions

### 1. Real Application, Fake Transport

Build a real `Application` via `Application.builder().token("test").build()` with all handlers registered via `AddarrBot._add_handlers()` logic. The key is `Application.process_update(update)` — this feeds an Update through PTB's actual dispatcher (pattern matching, conversation state tracking, handler groups) without polling Telegram.

We intercept outgoing bot responses by patching `Bot._do_post` (the low-level HTTP method PTB uses for all API calls). This captures every `reply_text`, `edit_message_text`, `send_photo`, etc. as raw request data.

**Why not mock individual response methods?** Because we want real `Update` objects, which means real `Message` objects on callback queries. Mocking at the transport layer lets PTB's internal plumbing work naturally while preventing any network calls.

### 2. Real Update Objects via de_json

Construct `Update` objects using `Update.de_json(data, bot)` with dictionaries matching Telegram's API format. This ensures callback_data patterns, message types, and user IDs are all realistic.

A factory module provides helpers:
- `make_text_update(text, user_id, chat_id)` → Update with a text message
- `make_command_update(command, user_id, chat_id)` → Update with a /command
- `make_callback_update(callback_data, user_id, chat_id, message)` → Update with a callback query

The `message` parameter on callback updates is important — PTB's `CallbackQuery.message` carries the original message that the inline keyboard was attached to, and handlers use `query.message.edit_text()` etc.

### 3. Response Capture

The `BotHarness` captures all outgoing API calls made by the bot. Each captured response includes:
- Method name (`sendMessage`, `editMessageText`, `sendPhoto`, etc.)
- Parameters (text, chat_id, reply_markup, parse_mode, etc.)

A `BotResponse` dataclass provides convenient access:
```python
@dataclass
class BotResponse:
    method: str       # "sendMessage", "editMessageText", etc.
    text: str         # message text or caption
    chat_id: int
    reply_markup: dict | None  # inline keyboard if present
    photo: str | None
```

The harness exposes `last_response` and `responses` (full list) after each `process_update` call.

### 4. API Mock Fixtures

Wrap `aioresponses` in friendly fixtures that set up canned responses for each service:

```python
@pytest.fixture
def mock_radarr(aioresponses):
    """Pre-configure Radarr API responses."""
    helper = RadarrMockHelper(aioresponses)
    # Default: search returns empty, profiles return one profile, root folders return one
    helper.set_defaults()
    return helper
```

Each helper provides methods like:
- `helper.search_returns(results)` — mock the search endpoint
- `helper.quality_profiles(profiles)` — mock quality profile lookup
- `helper.root_folders(folders)` — mock root folder lookup
- `helper.add_returns(success=True)` — mock the add endpoint

This keeps test bodies clean and focused on the conversation flow.

### 5. Auth Handling

The `@require_auth` decorator checks `AuthHandler._authenticated_users`. For most integration tests, we pre-seed the authenticated user set in the fixture. The auth flow test specifically does NOT pre-seed, testing the full password → authenticate → access flow.

### 6. Conversation State Verification

After each step, the harness can optionally check which conversation state PTB's `ConversationHandler` is in for a given user. This helps debug "conversation got stuck" issues. Access via PTB's internal `ConversationHandler._conversations` dict.

## Phased Approach

### Phase 1: Core Harness Infrastructure
- `BotHarness` class with `process_update()` wrapper and response capture
- Update factory functions (text, command, callback)
- Basic smoke test: send `/start`, verify bot responds

### Phase 2: API Mock Helpers
- `RadarrMockHelper`, `SonarrMockHelper`, `LidarrMockHelper` wrapping aioresponses
- Transmission and SABnzbd mock helpers
- Verify mocks work with a simple search call

### Phase 3: Media Flow Tests
- Movie flow: `/movie` → search → select → quality → added
- Series flow: `/series` → search → select → quality → season select → added
- Music flow: `/music` → search → select → quality → album monitor mode → added
- No results flow: search returns empty → appropriate message
- Navigation: paging through multiple results

### Phase 4: Auth & Cancel Flow Tests
- Auth flow: unauthenticated → `/start` → password prompt → correct password → authenticated
- Cancel at each conversation state (SEARCHING, SELECTING, QUALITY_SELECT, SEASON_SELECT)
- `/cancel` command as fallback

### Phase 5: Downloads Flow Tests
- `/downloads` with Transmission enabled
- `/downloads` with SABnzbd enabled
- Tab switching between clients

## Bot Response Methods to Intercept

From the codebase analysis, these are all the Telegram Bot API methods the handlers call:

| PTB Method | Telegram API Method | Used By |
|---|---|---|
| `message.reply_text()` | `sendMessage` | All handlers — initial responses |
| `message.reply_photo()` | `sendPhoto` | Media formatters — result cards with posters |
| `query.message.edit_text()` | `editMessageText` | Handlers + formatters — update message content |
| `query.message.edit_caption()` | `editMessageCaption` | Formatters — update photo caption |
| `query.message.edit_reply_markup()` | `editMessageReplyMarkup` | Season/album pickers — keyboard-only updates |
| `query.message.delete()` | `deleteMessage` | Formatters — cleanup before sending new message |
| `query.answer()` | `answerCallbackQuery` | All callback handlers — acknowledge tap |

## Verification

- `pytest tests/integration/ -v` passes with no external services
- Integration tests run in CI alongside existing unit tests
- No modifications to existing unit tests or production code
- Coverage: at minimum one happy-path test per media type + auth flow + cancel flow
