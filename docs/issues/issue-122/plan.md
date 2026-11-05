# Webhook-Based Download Notifications — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an HTTP webhook receiver that accepts event notifications from Radarr/Sonarr/Lidarr and sends formatted Telegram messages to admins about download lifecycle events (grab, download, upgrade, health issue, failure).

**Architecture:** A new `WebhookService` singleton runs an `aiohttp` web server on a configurable port alongside the existing Telegram polling loop. Each *arr service sends webhook POST requests to dedicated endpoints. The service validates requests via per-service secrets, parses event payloads into dataclass models, formats human-readable messages, and routes them through the existing `NotificationService`. A `/webhooks` Telegram command provides an interactive setup wizard that guides admins through enabling webhooks, generating secrets, configuring each *arr service, and testing connectivity — all without leaving Telegram.

**Tech Stack:** aiohttp (web server + existing dependency), python-telegram-bot (existing), dataclasses (event models)

---

## Context

### Issue #122 Requirements
- Webhook receiver for Radarr/Sonarr/Lidarr events: grab, download, upgrade, health, failure
- Admin notification via Telegram (user tracking deferred to #124)
- Config section for enable/port/secrets/event toggles
- Graceful lifecycle management (start/stop with bot)

### Key Integration Points

1. **Bot Lifecycle** (`src/main.py:AddarrBot`): Start webhook server in `start()` as `asyncio.create_task()`, stop in `stop()`. Mirrors the `HealthService` pattern.

2. **NotificationService** (`src/services/notification.py`): Already has `notify_admin(message)` and `notify_user(chat_id, message)`. Webhook service calls these — no changes needed to NotificationService itself. But `set_bot()` must be called before webhook events arrive. Currently `set_bot()` is NOT called in main.py — the webhook service must set it.

3. **Config** (`config_example.yaml`): New `webhooks:` top-level section.

4. **Translation** (`translations/addarr.*.yml`): New flat keys for webhook event messages.

5. **Architecture Tests** (`tests/test_architecture/test_conventions.py`): Add `WebhookService` to `SINGLETON_CLASSES`.

### *arr Webhook Support (Verified)

All three services natively support outbound webhooks, configured in their UI under
**Settings > Connect > Add > Webhook**. They share the same Servarr codebase architecture.

**Configuration in *arr UI:**
- `URL`: endpoint to POST to (e.g., `http://bot-host:8080/webhooks/radarr`)
- `Method`: POST (default) or PUT
- `Username/Password`: optional HTTP Basic Auth
- `Headers`: custom key-value headers (advanced setting) — this is how we validate requests

**Authentication:** There is **no built-in HMAC or signature**. The *arr services support
adding custom headers in their webhook config. We instruct users to add a
`X-Webhook-Secret: <token>` header in each service's webhook settings, and validate
that header on our end against a per-service secret in `config.yaml`.

**Common base fields** (all payloads, all services):
```json
{
  "eventType": "Grab",
  "instanceName": "Radarr",
  "applicationUrl": "http://localhost:7878"
}
```

**Radarr event types** (11):
`Test`, `Grab`, `Download`, `Rename`, `MovieAdded`, `MovieDelete`, `MovieFileDelete`,
`Health`, `HealthRestored`, `ApplicationUpdate`, `ManualInteractionRequired`

**Radarr Grab payload:**
```json
{
  "eventType": "Grab",
  "instanceName": "Radarr",
  "applicationUrl": "http://localhost:7878",
  "movie": {"id": 1, "title": "Movie Title", "year": 2024, "tmdbId": 12345},
  "release": {"quality": "Bluray-1080p", "size": 1234567890},
  "downloadClient": "qBittorrent",
  "downloadId": "abc123"
}
```

**Radarr Download/Import payload:**
```json
{
  "eventType": "Download",
  "movie": {"id": 1, "title": "Movie Title", "year": 2024},
  "movieFile": {"relativePath": "Movie (2024)/Movie.mkv", "quality": "Bluray-1080p"},
  "isUpgrade": false,
  "downloadClient": "qBittorrent"
}
```

**Sonarr event types** (11):
`Test`, `Grab`, `Download`, `Rename`, `SeriesAdd`, `SeriesDelete`, `EpisodeFileDelete`,
`Health`, `HealthRestored`, `ApplicationUpdate`, `ManualInteractionRequired`

**Sonarr Grab payload:**
```json
{
  "eventType": "Grab",
  "series": {"id": 1, "title": "Series Title", "year": 2024, "tvdbId": 12345},
  "episodes": [{"seasonNumber": 1, "episodeNumber": 1, "title": "Episode Title"}],
  "release": {"quality": "HDTV-720p", "size": 500000000},
  "downloadClient": "SABnzbd"
}
```

**Sonarr Download/Import payload:**
```json
{
  "eventType": "Download",
  "series": {"id": 1, "title": "Series Title"},
  "episodes": [{"seasonNumber": 1, "episodeNumber": 1, "title": "Episode Title"}],
  "episodeFile": {"relativePath": "Season 1/S01E01.mkv", "quality": "HDTV-720p"},
  "isUpgrade": false
}
```

**Lidarr event types** (13):
`Test`, `Grab`, `Download`, `DownloadFailure`, `ImportFailure`, `Rename`, `Retag`,
`ArtistAdd`, `ArtistDelete`, `AlbumDelete`, `Health`, `HealthRestored`, `ApplicationUpdate`

**Lidarr Grab payload:**
```json
{
  "eventType": "Grab",
  "artist": {"id": 1, "name": "Artist Name"},
  "albums": [{"id": 1, "title": "Album Title"}],
  "release": {"quality": "FLAC", "size": 800000000},
  "downloadClient": "Transmission"
}
```

**Lidarr Import payload:**
```json
{
  "eventType": "Download",
  "artist": {"id": 1, "name": "Artist Name"},
  "album": {"id": 1, "title": "Album Title"},
  "tracks": [{"title": "Track Title"}],
  "isUpgrade": false
}
```

Sources: Servarr Wiki, `WebhookEventType.cs` and `WebhookProxy.cs` in each repo.

### Design Decisions

1. **aiohttp web server, not flask/fastapi** — aiohttp is already a dependency, runs natively on the same asyncio event loop, zero new dependencies.

2. **One endpoint per service** (`/webhooks/radarr`, `/webhooks/sonarr`, `/webhooks/lidarr`) — cleaner than a single endpoint with routing logic. Each handler knows its payload format.

3. **Secret validation via custom header** — *arr services have NO built-in HMAC/signature. They support adding custom headers in webhook settings. We instruct users to add `X-Webhook-Secret: <token>` and validate it against per-service secrets in config.

4. **Admin-only notifications initially** — route all webhook notifications through `NotificationService.notify_admin()`. User-targeted notifications depend on #124 (user preferences / request tracking).

5. **Singleton service** — follows `HealthService` pattern: singleton class, `start()/stop()` lifecycle, global instance.

6. **Event models as dataclasses** — lightweight, testable, no external dependency.

7. **NotificationService.set_bot() integration** — The webhook service needs the bot instance to send messages. We inject it in `AddarrBot.start()` after `self.application.start()` gives us access to `self.application.bot`.

8. **Interactive Telegram setup wizard** — A `/webhooks` admin-only command with a full `ConversationHandler` flow. Minimal config.yaml setup (just `enable: true` + `port`), then the bot guides the user through generating secrets, shows exact URLs and step-by-step instructions for configuring each *arr service, and handles the `Test` event type to verify connectivity. Secrets are auto-generated and saved to `config.yaml` via `config.update_nested()` + `config.save()`. This removes the need for users to manually edit config.yaml for secrets or know URL patterns.

---

## Phase 1: Webhook Event Models

Create dataclass models for webhook events from each service.

**Files:**
- Create: `src/models/webhook.py`
- Test: `tests/test_models/test_webhook_models.py`

**What to build:**
- `WebhookEventType` enum: `GRAB`, `DOWNLOAD`, `UPGRADE`, `HEALTH_ISSUE`, `HEALTH_RESTORED`, `FAILURE`, `TEST`, `OTHER`
- `WebhookSource` enum: `RADARR`, `SONARR`, `LIDARR`
- `WebhookEvent` dataclass: `source`, `event_type`, `title`, `message`, `details` (dict), `is_upgrade` (bool)
- `parse_radarr_event(payload: dict) -> WebhookEvent` — maps Radarr JSON to WebhookEvent
- `parse_sonarr_event(payload: dict) -> WebhookEvent` — maps Sonarr JSON to WebhookEvent
- `parse_lidarr_event(payload: dict) -> WebhookEvent` — maps Lidarr JSON to WebhookEvent

**Mapping logic:**
- `eventType == "Test"` → `TEST`
- `eventType == "Grab"` → `GRAB`, title = movie/series/artist title
- `eventType == "Download"` with `isUpgrade == False` → `DOWNLOAD`
- `eventType == "Download"` with `isUpgrade == True` → `UPGRADE`
- `eventType == "Health"` → `HEALTH_ISSUE`
- `eventType == "HealthRestored"` → `HEALTH_RESTORED`
- `eventType == "ManualInteractionRequired"` → `FAILURE` (Radarr/Sonarr)
- `eventType == "DownloadFailure"` or `"ImportFailure"` → `FAILURE` (Lidarr)
- Everything else → `OTHER`

**Testing notes:**
- Pure data transformation — no mocks needed, just assert input→output
- Test each event type for each service
- Test missing/malformed fields (should not crash, use sensible defaults)

---

## Phase 2: Webhook Message Formatter

Format `WebhookEvent` objects into human-readable Telegram messages.

**Files:**
- Create: `src/services/webhook_formatter.py`
- Test: `tests/test_services/test_webhook_formatter.py`
- Modify: `translations/addarr.en-us.yml` (add translation keys)

**What to build:**
- `format_webhook_event(event: WebhookEvent) -> str` — produces a Telegram-ready message string

**Message templates (translation keys):**
```
WebhookGrab: "🎬 Grabbing: %{title}\nQuality: %{quality}\nService: %{source}"
WebhookDownload: "✅ Downloaded: %{title}\nQuality: %{quality}\nService: %{source}"
WebhookUpgrade: "⬆️ Upgraded: %{title}\nQuality: %{quality}\nService: %{source}"
WebhookHealthIssue: "⚠️ Health Issue (%{source}): %{message}"
WebhookHealthRestored: "✅ Health Restored (%{source}): %{message}"
WebhookFailure: "❌ Failed: %{title}\nService: %{source}\nReason: %{message}"
WebhookTest: "🔔 Test notification from %{source}"
WebhookUnknown: "ℹ️ %{source} event: %{title}"
```

**Design:**
- Uses `TranslationService.get_text()` for i18n support
- Falls back to English defaults if key missing
- Extracts quality from `event.details.get("quality", "Unknown")`
- For Sonarr: includes season/episode info in title (e.g., "Breaking Bad S01E01 - Pilot")

**Testing notes:**
- Mock `TranslationService` (already mocked globally in conftest)
- Test each event type produces expected format
- Test with missing details (graceful degradation)

---

## Phase 3: Webhook Service (HTTP Server)

The core service: aiohttp web server that receives webhooks and dispatches notifications.

**Files:**
- Create: `src/services/webhook.py`
- Test: `tests/test_services/test_webhook_service.py`

**What to build:**

```python
class WebhookService:
    """Singleton HTTP webhook receiver for *arr services."""
    _instance = None
    _app: Optional[aiohttp.web.Application]
    _runner: Optional[aiohttp.web.AppRunner]
    _site: Optional[aiohttp.web.TCPSite]
    _running: bool

    def __new__(cls): ...  # singleton pattern

    @classmethod
    def _initialize(cls): ...

    async def start(self, port: int, host: str = "0.0.0.0") -> None:
        """Create aiohttp app, register routes, start listening.
        Handles OSError (port in use) gracefully — logs error with
        suggestion to change port via /webhooks or config.yaml,
        does NOT crash the bot."""

    async def stop(self) -> None:
        """Gracefully shut down the HTTP server."""

    def _setup_routes(self, app: aiohttp.web.Application) -> None:
        """Register POST /webhooks/{radarr,sonarr,lidarr}"""

    async def _handle_radarr(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        """Validate secret, parse payload, format message, notify admin."""

    async def _handle_sonarr(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        """Same pattern for Sonarr."""

    async def _handle_lidarr(self, request: aiohttp.web.Request) -> aiohttp.web.Response:
        """Same pattern for Lidarr."""

    def _validate_secret(self, request: aiohttp.web.Request, service: str) -> bool:
        """Check X-Webhook-Secret header against config secret for the service."""

    async def _process_event(self, source: str, payload: dict) -> None:
        """Parse event, format message, send via NotificationService."""
```

**Request flow:**
1. Receive POST request
2. Validate `X-Webhook-Secret` header against `config.get("webhooks", {}).get("{service}_secret")` (skip if no secret configured)
3. Parse JSON body
4. Check if event type is enabled in config (`config.get("webhooks", {}).get("events", {}).get(event_type, True)`)
5. Parse payload into `WebhookEvent` model
6. Format message via `format_webhook_event()`
7. Send via `NotificationService().notify_admin(message)`
8. Return 200 OK (always, to prevent *arr retry storms)

**Error handling:**
- Invalid JSON → log warning, return 200 (don't trigger retries)
- Invalid secret → return 401 Unauthorized
- Parse/format error → log error, return 200
- Notification send error → log error, return 200

**Testing notes:**
- Use `aiohttp.test_utils.AioHTTPTestCase` or `aiohttp.test_utils.TestServer` for integration-style tests
- Mock `NotificationService` to verify messages are sent
- Test secret validation (valid, invalid, missing)
- Test each endpoint with sample payloads
- Test disabled event types are filtered
- Test malformed JSON handling

---

## Phase 4: Configuration

Add webhook config section and update validation.

**Files:**
- Modify: `config_example.yaml`
- Modify: `tests/conftest.py` (add webhooks to MOCK_CONFIG_DATA)

**Config section:**
```yaml
# Webhook Notifications (Optional)
# Receives events from *arr services for download lifecycle notifications
webhooks:
  enable: false
  port: 8080
  host: 0.0.0.0
  # Per-service webhook secrets (must match what you configure in each *arr app)
  radarr_secret:
  sonarr_secret:
  lidarr_secret:
  # Event types to notify on (all enabled by default)
  events:
    grab: true
    download: true
    upgrade: true
    health: true
    failure: true
```

**Testing notes:**
- Add `webhooks` key to `MOCK_CONFIG_DATA` in `tests/conftest.py` with `enable: False`
- Verify existing tests still pass with the new config key

---

## Phase 5: Bot Lifecycle Integration

Wire the webhook server into `AddarrBot` start/stop and inject the bot into `NotificationService`.

**Files:**
- Modify: `src/main.py` (AddarrBot.start, AddarrBot.stop)
- Modify: `tests/test_main.py` (add webhook lifecycle tests)
- Modify: `tests/test_architecture/test_conventions.py` (add WebhookService to SINGLETON_CLASSES)
- Modify: `tests/conftest.py` (add WebhookService singleton reset)

**Changes to AddarrBot:**

In `start()`, after `await self.application.start()`:
```python
# Inject bot into NotificationService for webhook notifications
from src.services.notification import NotificationService
NotificationService().set_bot(self.application.bot)

# Start webhook server if enabled
webhooks_config = config.get("webhooks", {})
if webhooks_config.get("enable", False):
    from src.services.webhook import webhook_service
    port = webhooks_config.get("port", 8080)
    host = webhooks_config.get("host", "0.0.0.0")
    await webhook_service.start(port=port, host=host)
    self._webhook_service = webhook_service
```

In `stop()`, before stopping health checker:
```python
# Stop webhook server
if hasattr(self, '_webhook_service') and self._webhook_service:
    await self._webhook_service.stop()
```

**Testing notes:**
- Mock `WebhookService` in main.py tests
- Test that webhook server starts when config enables it
- Test that webhook server doesn't start when disabled
- Test graceful stop includes webhook server
- Update `_make_mock_application()` if needed

---

## Phase 6: Interactive Webhook Setup Wizard

Admin-only `/webhooks` Telegram command with a multi-step `ConversationHandler` that guides
users through webhook configuration without leaving Telegram.

**Files:**
- Create: `src/bot/handlers/webhooks.py`
- Modify: `src/bot/states.py` (add webhook wizard states)
- Modify: `src/bot/keyboards.py` (add webhook keyboard layouts)
- Modify: `src/main.py` (register WebhooksHandler)
- Modify: `src/bot/commands.py` (add /webhooks to authenticated commands)
- Create: `tests/test_handlers/test_webhooks_handler.py`

**Conversation states** (add to `States` class):
```python
# Webhook setup wizard states
WEBHOOK_MENU = "webhook_menu"
WEBHOOK_SETUP_SERVICE = "webhook_setup_service"
WEBHOOK_CONFIRM_SECRET = "webhook_confirm_secret"
WEBHOOK_EVENTS = "webhook_events"
WEBHOOK_CHANGE_PORT = "webhook_change_port"
```

**Flow:**

```
/webhooks (entry_point, @require_auth + admin check)
    ↓
webhook_menu() → WEBHOOK_MENU
    Shows current status:
    - Webhook server: Running on port 8080 / Not running
    - Port: 8080 (Change)
    - Radarr: ✅ Configured (secret set) / ❌ Not configured
    - Sonarr: ✅ Configured / ❌ Not configured
    - Lidarr: ✅ Configured / ❌ Not configured
    - Last event received: <timestamp> or "None"

    Buttons:
    [🔧 Setup Radarr] [🔧 Setup Sonarr]
    [🔧 Setup Lidarr]
    [🔌 Change Port]
    [📋 Event Types]
    [❌ Close]
    ↓
User clicks "Setup Radarr"
    ↓
webhook_setup_service("radarr") → WEBHOOK_SETUP_SERVICE
    1. Generate a random 32-char hex secret (secrets.token_hex(16))
    2. Save to config: config.update_nested("webhooks.radarr_secret", secret)
    3. Determine webhook URL: http://<bot_host>:<port>/webhooks/radarr
       (bot_host from config.get("webhooks", {}).get("host", "0.0.0.0") —
        but display a note that 0.0.0.0 must be replaced with actual IP/hostname)
    4. Display step-by-step instructions:

    "🔧 Radarr Webhook Setup

    1. Open Radarr → Settings → Connect → Add → Webhook
    2. Set Name: Addarr
    3. Set URL: http://<your-bot-ip>:8080/webhooks/radarr
    4. Set Method: POST
    5. Click 'Show Advanced' and add a custom header:
       Key: X-Webhook-Secret
       Value: <generated_secret>
    6. Select notification triggers (recommended: all)
    7. Click Test to verify, then Save

    Secret saved to config. Click Test in Radarr to verify."

    Buttons:
    [🔄 Regenerate Secret] [◀️ Back]
    ↓
User clicks "Back" → WEBHOOK_MENU
    ↓
User clicks "Event Types"
    ↓
webhook_events() → WEBHOOK_EVENTS
    Shows toggle buttons for each event type:
    [✅ Grab] [✅ Download]
    [✅ Upgrade] [✅ Health]
    [✅ Failure]
    [◀️ Back]

    Clicking a toggle flips it (✅ → ❌ and vice versa),
    saves to config, and refreshes the keyboard.
    ↓
User clicks "Back" → WEBHOOK_MENU
    ↓
User clicks "Close" → ConversationHandler.END
```

**WebhooksHandler class:**
```python
class WebhooksHandler:
    """Admin-only interactive webhook setup wizard."""

    def __init__(self):
        self.translation = TranslationService()

    def get_handler(self) -> list:
        """Return ConversationHandler for /webhooks command."""

    async def show_menu(self, update, context) -> str:
        """Entry point: show webhook status and setup options."""

    async def setup_service(self, update, context) -> str:
        """Generate secret, show setup instructions for a specific *arr service."""

    async def regenerate_secret(self, update, context) -> str:
        """Generate a new secret for the current service."""

    async def toggle_event(self, update, context) -> str:
        """Toggle an event type on/off."""

    async def show_events(self, update, context) -> str:
        """Show event type toggle menu."""

    async def handle_back(self, update, context) -> str:
        """Return to webhook menu."""

    async def handle_close(self, update, context) -> int:
        """End the conversation."""

    async def prompt_port(self, update, context) -> str:
        """Ask admin to type a new port number."""

    async def save_port(self, update, context) -> str:
        """Validate and save the new port. Inform that restart is required."""
```

**Port change flow:**
```
User clicks "Change Port" → WEBHOOK_CHANGE_PORT
    ↓
prompt_port() shows: "Enter a new port number (1024-65535):"
    ↓
User types: 9090
    ↓
save_port() validates range, saves config.update_nested("webhooks.port", 9090),
    config.save(), shows "Port changed to 9090. Restart the bot for this to take effect."
    → WEBHOOK_MENU
```

Add `WEBHOOK_CHANGE_PORT = "webhook_change_port"` to `States`.

**Keyboard functions** (add to `src/bot/keyboards.py`):
```python
def get_webhook_menu_keyboard(radarr_configured, sonarr_configured, lidarr_configured):
    """Webhook main menu with per-service setup buttons."""

def get_webhook_setup_keyboard():
    """Regenerate secret / Back buttons for service setup screen."""

def get_webhook_events_keyboard(events_config):
    """Toggle buttons for each event type with current state."""
```

**Test event handling:**
When the webhook server receives a `Test` event type from any *arr service, it confirms
connectivity is working. The `format_webhook_event()` formatter (Phase 2) already handles
`TEST` → sends "Test notification from Radarr" message to admin. This serves as the
verification step in the setup wizard — user clicks "Test" in Radarr UI, bot sends a
Telegram message confirming receipt.

**Handler registration** (in `AddarrBot._add_handlers()`):
```python
# Webhook setup handler (admin only, always registered even if webhooks disabled
# so admins can see status and instructions)
webhooks_handler = WebhooksHandler()
for handler in webhooks_handler.get_handler():
    self.application.add_handler(handler)
```

Register after Settings handler, before Help handler (so `/webhooks` doesn't conflict
with existing commands).

**Command registration** (in `src/bot/commands.py`):
Add `("webhooks", translation.get_text("CommandWebhooks", default="Webhook setup"))` to
the authenticated commands list.

**Testing notes:**
- Follow `SettingsHandler` test patterns: mock config, mock query, assert state transitions
- Test admin-only gate (non-admin gets rejected)
- Test secret generation and config persistence
- Test event toggle saves to config
- Test menu shows correct status based on config state
- Test the instruction text includes correct URL/port from config

---

## Phase 7: Translation Keys

Add webhook notification translation keys to all 9 language files.

**Files:**
- Modify: `translations/addarr.en-us.yml`
- Modify: `translations/addarr.de-de.yml`
- Modify: `translations/addarr.es-es.yml`
- Modify: `translations/addarr.fr-fr.yml`
- Modify: `translations/addarr.it-it.yml`
- Modify: `translations/addarr.nl-be.yml`
- Modify: `translations/addarr.pl-pl.yml`
- Modify: `translations/addarr.pt-pt.yml`
- Modify: `translations/addarr.ru-ru.yml`

**Keys to add (English):**
```yaml
# Webhook notifications
WebhookGrab: "🎬 Grabbing: %{title}\nQuality: %{quality}\nService: %{source}"
WebhookDownload: "✅ Downloaded: %{title}\nQuality: %{quality}\nService: %{source}"
WebhookUpgrade: "⬆️ Upgraded: %{title}\nQuality: %{quality}\nService: %{source}"
WebhookHealthIssue: "⚠️ Health Issue (%{source}): %{message}"
WebhookHealthRestored: "✅ Health Restored (%{source}): %{message}"
WebhookFailure: "❌ Failed: %{title}\nService: %{source}\nReason: %{message}"
WebhookTest: "🔔 Test notification from %{source}"
WebhookUnknown: "ℹ️ %{source} event: %{title}"

# Webhook setup wizard
CommandWebhooks: "Webhook setup"
WebhookMenuTitle: "🔔 Webhook Notifications"
WebhookServerRunning: "Server: ✅ Running on port %{port}"
WebhookServerStopped: "Server: ❌ Not running"
WebhookServiceConfigured: "✅ Configured (secret set)"
WebhookServiceNotConfigured: "❌ Not configured"
WebhookSetupTitle: "🔧 %{service} Webhook Setup"
WebhookSetupInstructions: "1. Open %{service} → Settings → Connect → + → Webhook\n2. Set Name: Addarr\n3. Set URL: %{url}\n4. Set Method: POST\n5. Click 'Show Advanced' and add a header:\n   Key: X-Webhook-Secret\n   Value: %{secret}\n6. Select notification triggers\n7. Click Test to verify, then Save"
WebhookSecretRegenerated: "🔄 New secret generated. Update the header in %{service}."
WebhookEventsTitle: "📋 Event Notifications"
WebhookNotAdmin: "⛔ Webhook setup requires admin access."
WebhookNotEnabled: "⚠️ Webhooks not enabled. Set webhooks.enable: true and webhooks.port in config.yaml, then restart."
WebhookSetupService: "🔧 Setup %{service}"
WebhookRegenerateSecret: "🔄 Regenerate Secret"
WebhookEventTypes: "📋 Event Types"
WebhookClose: "❌ Close"
```

**Note:** For non-English files, keep the emoji + English structure initially. Native translations can be contributed later. The key names remain the same across all files.

---

## Verification Checklist

1. `pytest --tb=short -q` — all tests pass
2. `python -m flake8 .` — no lint errors
3. `mypy src/` — no new type errors
4. `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` — all translations valid
5. Architecture tests pass (singleton, layer boundaries)
6. New service has 100% test coverage

## Files Changed Summary

| Action | Path |
|--------|------|
| Create | `src/models/webhook.py` |
| Create | `src/services/webhook.py` |
| Create | `src/services/webhook_formatter.py` |
| Create | `src/bot/handlers/webhooks.py` |
| Create | `tests/test_models/test_webhook_models.py` |
| Create | `tests/test_services/test_webhook_service.py` |
| Create | `tests/test_services/test_webhook_formatter.py` |
| Create | `tests/test_handlers/test_webhooks_handler.py` |
| Modify | `src/main.py` |
| Modify | `src/bot/states.py` |
| Modify | `src/bot/keyboards.py` |
| Modify | `src/bot/commands.py` |
| Modify | `config_example.yaml` |
| Modify | `tests/conftest.py` |
| Modify | `tests/test_main.py` |
| Modify | `tests/test_architecture/test_conventions.py` |
| Modify | `translations/addarr.*.yml` (9 files) |
