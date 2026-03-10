# Issue #122: Webhook-Based Download Notifications

**Plan:** [plan.md](plan.md)
**Branch:** `feature/122-webhook-download-notifications`
**Issue:** https://github.com/Krypt0nBull3t/Addarr/issues/122

---

### Phase 1: Foundation — Models, Config, Formatter, Translations (3 tasks)

**Goal:** Build all pure-logic components that the webhook service depends on: event models, message formatter, config schema, and translation keys.

- [x] **1.1** Webhook event models and config schema
    - **Context:** See plan.md Phases 1 + 4. Key refs: `src/models/notification.py` (dataclass pattern), `config_example.yaml:90` (service config pattern), `tests/conftest.py:23` (MOCK_CONFIG_DATA)
    - **Watch out:** `WebhookEvent.details` is a catch-all dict for service-specific fields (quality, episodes, etc.) — don't over-model the *arr payloads. Sonarr title should include S01E01 format. Lidarr has `DownloadFailure`/`ImportFailure` as separate event types (not just `ManualInteractionRequired`). Event type in payload is `"Health"` not `"HealthIssue"`.
    - **Scope:** Enums, dataclass, three parser functions, config_example.yaml webhooks section, MOCK_CONFIG_DATA update
    - **Touches:** `src/models/webhook.py` (create), `config_example.yaml`, `tests/conftest.py`, `tests/test_models/test_webhook_models.py` (create)
    - **Action items:**
        - [RED] Write tests for `parse_radarr_event()` — Grab, Download, Upgrade (isUpgrade=True), Health, HealthRestored, ManualInteractionRequired, Test, unknown event type, missing/malformed fields
        - [RED] Write tests for `parse_sonarr_event()` — same event types, verify S01E01 title formatting with multi-episode payloads
        - [RED] Write tests for `parse_lidarr_event()` — same events plus DownloadFailure/ImportFailure, verify artist+album title extraction
        - [GREEN] Implement `WebhookEventType` enum, `WebhookSource` enum, `WebhookEvent` dataclass
        - [GREEN] Implement `parse_radarr_event()`, `parse_sonarr_event()`, `parse_lidarr_event()`
        - [GREEN] Add `webhooks` section to `config_example.yaml` (enable, port, host, per-service secrets, event toggles)
        - [GREEN] Add `webhooks` key to `MOCK_CONFIG_DATA` in `tests/conftest.py`
    - **Success:** `pytest tests/test_models/test_webhook_models.py -v` passes, existing tests unaffected
    - **Completed:** 2026-03-10
    - **Learnings:**
        - Radarr Grab uses `release.quality`, Download uses `movieFile.quality` — need to check both
        - Lidarr Grab uses `albums` (list), Download uses `album` (singular) — different payload shapes
        - Sonarr `_format_sonarr_title` needs separate paths for single vs multi-episode and with/without episode title
    - **Key Changes:**
        - Created `src/models/webhook.py` with `WebhookEventType`, `WebhookSource` enums, `WebhookEvent` dataclass, and 3 parser functions
        - Added `webhooks` section to `config_example.yaml`
        - Added `webhooks` key to `MOCK_CONFIG_DATA` in `tests/conftest.py`
        - Created `tests/test_models/test_webhook_models.py` with 37 tests
    - **Notes:** `Dict` type hint used for `details` field — could be `Dict[str, Any]` but kept simple

- [x] **1.2** Webhook message formatter *(in progress)*
    - **Context:** See plan.md Phase 2. Key refs: `src/services/webhook_formatter.py` (new), `src/services/translation.py` (`TranslationService.get_text()` does single-level flat key lookup)
    - **Watch out:** `get_text()` is a flat `.get(key)` — don't use nested keys. The formatter should use `default=` parameter for fallback English text so it works even without translation files loaded. Quality comes from `event.details.get("quality", "Unknown")`.
    - **Scope:** `format_webhook_event()` function, no class needed (stateless)
    - **Touches:** `src/services/webhook_formatter.py` (create), `tests/test_services/test_webhook_formatter.py` (create)
    - **Action items:**
        - [RED] Write tests for each event type (GRAB, DOWNLOAD, UPGRADE, HEALTH_ISSUE, HEALTH_RESTORED, FAILURE, TEST, OTHER) — verify output contains title, quality, source
        - [RED] Write tests for Sonarr episode formatting in title (S01E01 - Episode Title)
        - [RED] Write tests for missing details (no quality, no title) — graceful defaults
        - [GREEN] Implement `format_webhook_event()` using TranslationService
    - **Success:** `pytest tests/test_services/test_webhook_formatter.py -v` passes
    - **Completed:** 2026-03-10
    - **Learnings:**
        - TranslationService.get_text() returns the key name when translation is missing — used this as detection for fallback to English defaults
        - Need to mock TranslationService at the import site to test the translation-available path
    - **Key Changes:**
        - Created `src/services/webhook_formatter.py` with `format_webhook_event()` using translation fallback pattern
        - Created `tests/test_services/test_webhook_formatter.py` with 12 tests
    - **Notes:** The formatter uses `{title}` Python format strings for defaults, while translations use `%(title)s` python-i18n syntax

- [x] **1.3** Translation keys for all 9 languages
    - **Context:** See plan.md Phase 7. Key refs: `translations/addarr.en-us.yml` (existing keys pattern), `translations/addarr.template.yml` (template reference)
    - **Watch out:** Keys must be flat top-level (not nested). Non-English files get English text initially. Use `%{variable}` syntax for interpolation (python-i18n convention).
    - **Scope:** Add webhook notification keys + wizard UI keys to all 9 translation files
    - **Touches:** `translations/addarr.en-us.yml`, `translations/addarr.de-de.yml`, `translations/addarr.es-es.yml`, `translations/addarr.fr-fr.yml`, `translations/addarr.it-it.yml`, `translations/addarr.nl-be.yml`, `translations/addarr.pl-pl.yml`, `translations/addarr.pt-pt.yml`, `translations/addarr.ru-ru.yml`
    - **Action items:**
        - [GREEN] Add all webhook translation keys to `addarr.en-us.yml`
        - [GREEN] Add same keys (English text) to all 8 other language files
        - [GREEN] Run `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` to verify
    - **Success:** `--validate-i18n` passes, no missing key warnings
    - **Completed:** 2026-03-10
    - **Learnings:**
        - Translation keys use `%{variable}` syntax (python-i18n convention), not Python `{variable}` format strings
        - Wizard UI keys added proactively for task 3.1 (WebhookMenuTitle, WebhookNotAdmin, WebhookSecretGenerated, etc.)
    - **Key Changes:**
        - Added 28 webhook translation keys to all 9 language files and template
        - Keys cover: 8 notification types (WebhookGrab, WebhookDownload, etc.) + 20 wizard UI keys (CommandWebhooks, WebhookMenuTitle, etc.)
    - **Notes:** Non-English files have English placeholder text — can be translated later

---

### Phase 2: Webhook HTTP Service (2 tasks)

**Goal:** Build the aiohttp web server that receives webhook POSTs and dispatches notifications, then wire it into the bot lifecycle.

- [x] **2.1** WebhookService singleton HTTP server
    - **Context:** See plan.md Phase 3. Key refs: `src/services/health.py:67` (singleton pattern template), `src/services/notification.py:45` (`notify_admin()` method). aiohttp is already a dependency — use `aiohttp.web.Application`, `AppRunner`, `TCPSite` for the server lifecycle.
    - **Watch out:** Always return 200 OK to *arr services (except 401 for invalid secret) to prevent retry storms. Port-in-use (`OSError`) must be caught in `start()` — log error + suggestion, don't crash bot. Secret validation is optional: skip if no secret configured for the service. Event type filtering: check `config.get("webhooks", {}).get("events", {}).get(event_type_key, True)` — enabled by default.
    - **Scope:** WebhookService class with start/stop, route handlers, secret validation, event processing pipeline
    - **Touches:** `src/services/webhook.py` (create), `tests/test_services/test_webhook_service.py` (create)
    - **Action items:**
        - [RED] Write tests for singleton pattern (`__new__` returns same instance)
        - [RED] Write tests for `_validate_secret()` — valid secret, invalid secret, no secret configured (should pass), no header sent (should fail if secret configured)
        - [RED] Write tests for each endpoint (`/webhooks/radarr`, `/webhooks/sonarr`, `/webhooks/lidarr`) with sample payloads — verify NotificationService.notify_admin called with formatted message
        - [RED] Write tests for disabled event types being filtered (no notification sent)
        - [RED] Write tests for malformed JSON (return 200, no crash)
        - [RED] Write tests for start/stop lifecycle (server starts listening, stops cleanly)
        - [RED] Write test for port-in-use error handling (OSError caught, logged, not raised)
        - [GREEN] Implement `WebhookService` singleton with `_initialize()`, `start()`, `stop()`
        - [GREEN] Implement `_setup_routes()`, endpoint handlers, `_validate_secret()`, `_process_event()`
        - [GREEN] Create module-level `webhook_service = WebhookService()` instance
    - **Success:** `pytest tests/test_services/test_webhook_service.py -v` passes, 100% coverage on new code
    - **Completed:** 2026-03-10
    - **Learnings:**
        - Config patching must be at import site (`src.services.webhook.config`) not just via MockConfig — the module-level `from src.config.settings import config` binds at import time
        - Module-level `_PARSERS` dict holds direct references to parser functions — must use `patch.dict` to override, not `patch` on the function name
        - aiohttp `TestClient`/`TestServer` pattern works well for testing webhook endpoints without starting a real server
    - **Key Changes:**
        - Created `src/services/webhook.py` with `WebhookService` singleton (start/stop, route handlers, secret validation, event filtering)
        - Created `tests/test_services/test_webhook_service.py` with 24 tests at 100% coverage
        - Added `WebhookService` to singleton reset in `tests/conftest.py`
    - **Notes:** The `webhook_service = WebhookService()` module-level instance at bottom of webhook.py gets created at import time — ensure conftest resets it

- [x] **2.2** Bot lifecycle integration
    - **Context:** See plan.md Phase 5. Key refs: `src/main.py:212` (`start()` method), `src/main.py:235` (`stop()` method), `src/main.py:220` (health checker task pattern), `tests/test_architecture/test_conventions.py:20` (SINGLETON_CLASSES set)
    - **Watch out:** `NotificationService.set_bot()` must be called in `start()` after `self.application.start()` so the bot instance is available for webhook notifications. Import `WebhookService` inside the conditional to avoid import when webhooks are disabled. Add `WebhookService` to `SINGLETON_CLASSES` in architecture tests. Add singleton reset to `tests/conftest.py`.
    - **Scope:** Wire WebhookService start/stop into AddarrBot, inject bot into NotificationService, update architecture tests and conftest
    - **Touches:** `src/main.py`, `tests/test_main.py`, `tests/test_architecture/test_conventions.py`, `tests/conftest.py`
    - **Action items:**
        - [RED] Write test: webhook server starts when `webhooks.enable` is True in config
        - [RED] Write test: webhook server does NOT start when `webhooks.enable` is False
        - [RED] Write test: `stop()` calls `webhook_service.stop()` when webhook was started
        - [RED] Write test: NotificationService.set_bot() is called with application.bot
        - [GREEN] Add `NotificationService().set_bot(self.application.bot)` to `AddarrBot.start()`
        - [GREEN] Add conditional webhook server start in `AddarrBot.start()`
        - [GREEN] Add webhook server stop in `AddarrBot.stop()`
        - [GREEN] Add `WebhookService` to `SINGLETON_CLASSES` in `test_conventions.py`
        - [GREEN] Add `WebhookService` singleton reset to `conftest.py`
    - **Success:** `pytest tests/test_main.py tests/test_architecture/ -v` passes, webhook lifecycle correctly managed
    - **Completed:** 2026-03-10
    - **Learnings:**
        - NotificationService.set_bot() must be called after application.start() so the bot instance is available for webhook notifications
        - _webhook_service attribute on AddarrBot tracks the instance for stop() cleanup
    - **Key Changes:**
        - Added `WebhookService` and `NotificationService` imports to `src/main.py`
        - Added webhook start/stop to `AddarrBot.start()` and `AddarrBot.stop()`
        - Added `NotificationService().set_bot()` call in `start()`
        - Added `WebhookService` to `SINGLETON_CLASSES` in architecture tests
        - Added `WebhookService` singleton reset in `tests/conftest.py`
        - Added 4 lifecycle integration tests in `tests/test_main.py`
    - **Notes:** Webhook server starts after application.start() and before polling begins

---

### Phase 3: Interactive Setup Wizard (2 tasks)

**Goal:** Build the `/webhooks` Telegram command with a full conversation flow for configuring webhook secrets, ports, and event toggles through inline keyboards.

- [x] **3.1** Webhook setup handler with states and keyboards
    - **Context:** See plan.md Phase 6. Key refs: `src/bot/handlers/settings.py` (ConversationHandler pattern), `src/bot/states.py` (state definitions), `src/bot/keyboards.py` (keyboard factory functions), `src/bot/handlers/auth.py` (`@require_auth` + `is_admin()` pattern), `src/definitions.py` (`is_admin()`)
    - **Watch out:** Handler must be registered even when webhooks are disabled (so admin can see status + "not enabled" message). ConversationHandler states use string keys (not ints) for wizard flows. `config.update_nested()` + `config.save()` for persisting secrets/port. Port change requires bot restart — inform user. The `WEBHOOK_CHANGE_PORT` state needs a `MessageHandler` (not `CallbackQueryHandler`) since user types a number.
    - **Scope:** WebhooksHandler class, conversation states, keyboard functions, admin gate
    - **Touches:** `src/bot/handlers/webhooks.py` (create), `src/bot/states.py`, `src/bot/keyboards.py`, `tests/test_handlers/test_webhooks_handler.py` (create)
    - **Action items:**
        - [RED] Write test: non-admin user gets rejected with WebhookNotAdmin message
        - [RED] Write test: `show_menu()` displays server status (running/stopped) and per-service config status
        - [RED] Write test: `show_menu()` shows "not enabled" message when webhooks disabled in config
        - [RED] Write test: `setup_service()` generates a secret, saves to config, returns instructions with correct URL and port
        - [RED] Write test: `regenerate_secret()` creates new secret, saves to config
        - [RED] Write test: `show_events()` displays toggles matching current config state
        - [RED] Write test: `toggle_event()` flips event type and saves to config
        - [RED] Write test: `prompt_port()` asks for port number, `save_port()` validates range and saves
        - [RED] Write test: `save_port()` rejects invalid port (out of range, non-numeric)
        - [RED] Write test: `handle_close()` returns ConversationHandler.END
        - [GREEN] Add webhook states to `src/bot/states.py`
        - [GREEN] Add `get_webhook_menu_keyboard()`, `get_webhook_setup_keyboard()`, `get_webhook_events_keyboard()` to `src/bot/keyboards.py`
        - [GREEN] Implement `WebhooksHandler` class with all conversation methods
        - [GREEN] Implement `get_handler()` returning ConversationHandler with all states
    - **Success:** `pytest tests/test_handlers/test_webhooks_handler.py -v` passes, full wizard flow works
    - **Completed:** 2026-03-10
    - **Learnings:**
        - `@require_auth` decorator handles the `effective_message`/`effective_user` None guard before the handler runs, making explicit guard clauses unreachable dead code
        - Config must be patched at import site (`src.bot.handlers.webhooks.config`) AND kept active through the test (use yield-based fixture)
        - Test users need to be in `AuthHandler._authenticated_users` to pass `@require_auth`
    - **Key Changes:**
        - Created `src/bot/handlers/webhooks.py` with full ConversationHandler (menu, setup, regen, events, port, close)
        - Added 3 webhook states to `src/bot/states.py` (WEBHOOK_MENU, WEBHOOK_EVENTS, WEBHOOK_CHANGE_PORT)
        - Added 3 keyboard functions to `src/bot/keyboards.py` (menu, service, events)
        - Created `tests/test_handlers/test_webhooks_handler.py` with 22 tests at 100% coverage
    - **Notes:** Handler registered even when webhooks disabled — admin sees "not enabled" message

- [x] **3.2** Handler registration and command menu
    - **Context:** See plan.md Phase 6 (handler/command registration sections). Key refs: `src/main.py:107` (`_add_handlers()`), `src/bot/commands.py` (`build_authenticated_commands()`)
    - **Watch out:** Register WebhooksHandler after SettingsHandler, before HelpHandler. Command name must be lowercase (`webhooks`). Add the `CommandWebhooks` translation key usage in commands.py.
    - **Scope:** Register handler in main.py, add /webhooks to command menu
    - **Touches:** `src/main.py`, `src/bot/commands.py`, `tests/test_main.py`
    - **Action items:**
        - [RED] Write test: WebhooksHandler is registered in `_add_handlers()`
        - [RED] Write test: `/webhooks` appears in authenticated commands list
        - [GREEN] Add WebhooksHandler import and registration in `_add_handlers()`
        - [GREEN] Add `webhooks` command to `build_authenticated_commands()` in `commands.py`
    - **Success:** `pytest tests/test_main.py -v` passes, `/webhooks` command is registered
    - **Completed:** 2026-03-10
    - **Learnings:**
        - WebhooksHandler is always-on (not conditional on config) since admin needs to see status even when disabled
        - Adding a handler requires updating `_make_handler_patches()` in test_main.py and all handler count assertions
    - **Key Changes:**
        - Added `WebhooksHandler` import and registration in `src/main.py:_add_handlers()` (after Settings, before Delete)
        - Added `webhooks` command to `build_authenticated_commands()` in `src/bot/commands.py`
        - Updated handler count assertions in `tests/test_main.py` (14→15 base, +1 for optional)
        - Updated command count assertions in `tests/test_bot/test_commands.py` (7→8 base, +1 for all totals)
    - **Notes:** Command uses `CommandWebhooks` translation key — already added in task 1.3

---

## Progress

| Task | Status | Date |
|------|--------|------|
| 1.1  | [x]    | 2026-03-10 |
| 1.2  | [x]    | 2026-03-10 |
| 1.3  | [x]    | 2026-03-10 |
| 2.1  | [x]    | 2026-03-10 |
| 2.2  | [x]    | 2026-03-10 |
| 3.1  | [x]    | 2026-03-10 |
| 3.2  | [x]    | 2026-03-10 |
