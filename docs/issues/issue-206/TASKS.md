# Tasks: Webhook setup resets and leaks secrets; server binds 0.0.0.0 (#206)

Source plan: `docs/issues/issue-206/plan.md`. Branch `fix/206-webhook-setup-secrets`. PR targets `development`.
The PR body must say that remote *arr apps need `webhooks.host: 0.0.0.0`.

### Phase 1: Webhook service and docs (1 task)

**Goal:** The receiver binds loopback by default, rejects bad secret headers with 401, and warns once when no admin chat gets its events.

- [x] **1.1** Harden `WebhookService` (F104, F105, F106) and document host and port
    - **Context:**
        - **Why:** The server listens on `0.0.0.0` over plain HTTP by default (F104). A non-ASCII `X-Api-Secret` makes `hmac.compare_digest(str, str)` raise `TypeError`, so the client gets 500 (F105). With `logging.adminNotifyId` 0 or empty, `NotificationService.notify_admin` returns silently and every event is lost (F106).
        - **Architecture:** Singleton service (`__new__` + `_initialize`, docs/adr/0001). Config via `config.get(...)`. No new singleton, so `SINGLETON_CLASSES` and `reset_singletons` stay as they are.
        - **Key refs:** `src/services/webhook.py:54`, `:70`, `:78` (host default), `:104-108` (compare), `start()`; `src/services/notification.py:44`; `src/setup/prompts.py:236` (wizard writes `adminNotifyId = 0`); `tests/test_services/test_webhook_service.py` fixtures `webhook_config`, `webhook_service`, `webhook_client`, class `TestWebhookLifecycle.test_start_creates_runner` (how `start()` is patched).
        - **Watch out:** `aiohttp` decodes header bytes as UTF-8 with `surrogateescape`, so a header can hold a lone surrogate; `.encode()` with the default error mode raises. Use `.encode("utf-8", "surrogateescape")` after `str()` (YAML loads an all-digit secret as int, keep the `str()`). Existing configs that hold `host` keep it: change only the default. The warning goes in `start()`, once, not per event. Treat `0`, `"0"`, `""` and `None` as missing. Fixtures in this test file use `host: "0.0.0.0"`; the new default test must omit the key.
    - **Scope:** Service code, three doc/config comments, one skill line.
    - **Touches:** `src/services/webhook.py`, `config_example.yaml:93-96`, `docker-compose.yml:12-21`, `.claude/skills/security-audit/SKILL.md:58`, `tests/test_services/test_webhook_service.py`
    - **Action items:**
        - [RED] Write pytest tests: no `webhooks.host` gives `service._host == "127.0.0.1"`; a configured `host: "0.0.0.0"` is kept
        - [RED] Write pytest tests: `_validate_secret("radarr", "é")` and `"\udce9"` return False; POST `/webhooks/radarr` with `X-Api-Secret: é` returns 401
        - [RED] Write pytest tests (parametrized `0`, `""`, `None`, `"0"`, and `12345` as the control): `await service.start()` logs exactly one warning naming `adminNotifyId`, none for `12345`
        - [GREEN] Change the three `"0.0.0.0"` defaults to `"127.0.0.1"`; compare byte strings in `_validate_secret`; add the one-time warning in `start()`
        - [GREEN] `config_example.yaml`: `host: 127.0.0.1` plus comments on host and port (plain HTTP, TCP port, must be reachable by the *arr apps, remote *arr apps need `host: 0.0.0.0`)
        - [GREEN] `docker-compose.yml`: replace the "no listening ports" claim with the webhook receiver note (host networking exposes `webhooks.host:webhooks.port`, default `127.0.0.1:8080`)
        - [GREEN] `.claude/skills/security-audit/SKILL.md:58`: default is `127.0.0.1:8080`
    - **Success:** `scripts/test_runner.py services --coverage` and `tests/test_architecture` pass (the architecture tests parse skills and docs); flake8 and mypy clean; each new test failed before the fix.
    - **Completed:** 2026-11-05
    - **Learnings:**
        - The 10 new tests all failed first (host `0.0.0.0`, `TypeError` on `é`, no warning), then passed.
        - `scripts/test_runner.py services --coverage` reports the 100% gate as failed because `rate_limit.py` has gaps in that scoped run; `webhook.py` itself is at 100%. The full gate runs in the preflight.
        - `config.get("logging", {})` can return a dict without `adminNotifyId`; `None` and a missing key take the same warning path.
    - **Key Changes:**
        - `src/services/webhook.py`: host default `127.0.0.1` (3 places); `_validate_secret` compares `utf-8`/`surrogateescape` bytes; new `_warn_if_admin_notify_missing()` called from `start()`.
        - `config_example.yaml`, `docker-compose.yml`, `.claude/skills/security-audit/SKILL.md`: default host and port documented, remote *arr apps need `host: 0.0.0.0`.
        - `tests/test_services/test_webhook_service.py`: `TestHostDefault`, `TestAdminNotifyWarning`, secret and endpoint tests for non-ASCII headers.
    - **Notes:** Existing configs that set `webhooks.host` keep it (no migration). Put "remote *arr apps need `webhooks.host: 0.0.0.0`" in the PR body.

### Phase 2: Handler flow fixes (2 tasks)

**Goal:** Back, Close and the port prompt behave, and `/webhooks` never shows a secret outside a private chat or resets one by a tap.

- [x] **2.1** Back, Close and port Cancel (F101, F102, F103)
    - **Context:**
        - **Why:** `wh_back` has no handler in `WEBHOOK_MENU` (F101). Close calls `context.user_data.clear()` and wipes other flows (F102). The port prompt has no Cancel button and `menu_cancel` is not a fallback, so after a Cancel tap the conversation stays in `WEBHOOK_CHANGE_PORT` and typed text is saved as a port (F103).
        - **Architecture:** `ConversationHandler` in `WebhooksHandler.get_handler()`. Keyboards live in `src/bot/keyboards.py` (webhook section, ~line 1245). The `^menu_cancel$` callback is the shared Cancel callback data (`src/bot/keyboards.py:74`); `StartHandler` registers last, so the webhook conversation sees it first while it is active.
        - **Key refs:** `src/bot/handlers/webhooks.py:53-69` (WEBHOOK_MENU), `:85-90` (fallbacks), `:260-272` (`prompt_port`), `:343-358` (`handle_close`), `_back_to_menu` at `:315`; `tests/test_handlers/test_webhooks_handler.py` classes `TestPortChange`, `TestClose`, `TestBackToMenu`, `TestGetHandler`; `tests/test_bot/test_keyboards.py`.
        - **Watch out:** Callback patterns stay anchored (`^wh_back$`, `^menu_cancel$`). `handle_close` edits the message to `WebhookClose` for a callback; the `menu_cancel` fallback reuses it. Look up handlers via `handler.get_handler()[0].states` and `.fallbacks`, not by importing private lists. New keyboard text uses `TranslationService().get_text("Cancel")`, existing key.
    - **Scope:** Handler registration, one keyboard builder, one line removed.
    - **Touches:** `src/bot/handlers/webhooks.py`, `src/bot/keyboards.py` (new `get_webhook_port_keyboard() -> InlineKeyboardMarkup`), `tests/test_handlers/test_webhooks_handler.py`, `tests/test_bot/test_keyboards.py`
    - **Action items:**
        - [RED] Write pytest tests: a `CallbackQueryHandler` for `wh_back` exists in `States.WEBHOOK_MENU` and shows the menu again
        - [RED] Write pytest tests: after `handle_close`, `context.user_data["other"]` is still set
        - [RED] Write pytest tests: the `prompt_port` message carries a button with `callback_data == "menu_cancel"`; `get_webhook_port_keyboard()` has exactly that one button
        - [RED] Write pytest tests: a fallback matches `menu_cancel`, returns `ConversationHandler.END`, and text sent afterwards is not saved as the port
        - [GREEN] Add the `wh_back` handler and the `menu_cancel` fallback; remove `context.user_data.clear()`; pass `get_webhook_port_keyboard()` to `prompt_port`
    - **Success:** `scripts/test_runner.py handlers --coverage` and `scripts/test_runner.py bot --coverage` pass; flake8 and mypy clean.
    - **Completed:** 2026-11-05
    - **Learnings:**
        - `check_update` on a `CallbackQueryHandler` needs a real `Update`; the `make_update` factory gives a `MagicMock`, so the tests match on `handler.pattern` (fallbacks also hold a `CommandHandler` with no `pattern`).
        - All 5 new tests failed with `src/` stashed, then passed with it restored.
        - The unit test proves `menu_cancel` ends the conversation. "Text after cancel is not saved as a port" is proven end to end in task 3.1 (it needs the real conversation state).
    - **Key Changes:**
        - `src/bot/handlers/webhooks.py`: `wh_back` handler in `WEBHOOK_MENU`; `menu_cancel` fallback to `handle_close`; `prompt_port` sends `get_webhook_port_keyboard()`; `context.user_data.clear()` removed.
        - `src/bot/keyboards.py`: new `get_webhook_port_keyboard()`.
        - Tests in `tests/test_handlers/test_webhooks_handler.py` and `tests/test_bot/test_keyboards.py`.
    - **Notes:** `scripts/test_runner.py bot --coverage` prints a failing 100% gate (it also lists `src/bot/handlers/`, which `tests/test_bot/` does not cover). Ignore it; the preflight runs the real gate.

- [x] **2.2** Private-chat gate and stable secrets (F012, F100)
    - **Context:**
        - **Why:** In a group with `chatMode: allow_all`, `/webhooks` posts a secret into the group (F012). Tapping an already set-up service saves a new secret at once, so the *arr app gets 401 (F100). The audit decision: show the stored secret, only Regenerate makes a new one.
        - **Architecture:** `show_menu` is the `/webhooks` entry point with `@require_auth`. `auth.py` `_enforce_private_chat` skips the check under `allow_all`, so the handler needs its own check. The service keyboard (`get_webhook_service_keyboard`) already has Regenerate and Back.
        - **Key refs:** `src/bot/handlers/webhooks.py:98-141` (`show_menu`), `:143-177` (`setup_service`), `src/bot/handlers/auth.py:38-52` (`PrivateChatOnly` use), `translations/addarr.en-us.yml:354-355` (`WebhookSecretGenerated`, `WebhookSecretRegenerated`), the `i18n-key` skill.
        - **Watch out:** Decided: reuse the existing key `PrivateChatOnly` for the refusal (no new key); run the check before the admin gate and return `ConversationHandler.END`. The only new key is `WebhookSecretExisting` (placeholders `%{service}`, `%{url}`, `%{secret}`) in `translations/addarr.template.yml` and all 9 locales; `nl-be` uses Netherlands Dutch wording. A stored secret can be an int (all digits in YAML): show `str(...)`. Do not call `token_hex` or `config.save()` on the show path. `test_setup_service_generates_secret` uses sonarr (no secret) and must stay green.
    - **Scope:** Two handler changes, one translation key in 10 files.
    - **Touches:** `src/bot/handlers/webhooks.py`, `translations/addarr.template.yml` and `translations/addarr.<locale>.yml` (9 files), `tests/test_handlers/test_webhooks_handler.py`
    - **Action items:**
        - [RED] Write pytest tests: `/webhooks` from a group chat (`allow_all`) returns `ConversationHandler.END`, replies `PrivateChatOnly`, and no reply holds a secret; a private chat still shows the menu
        - [RED] Write pytest tests: `wh_setup_radarr` with `radarr_secret` set shows that secret, saves nothing (`config.save` not called, `token_hex` not called), and offers a `wh_regen_radarr` button; an int secret is shown as text
        - [GREEN] Add the private-chat check to `show_menu` before the admin gate
        - [GREEN] Make `setup_service` show the stored secret with `WebhookSecretExisting`, and generate only when none is stored
        - [GREEN] Add `WebhookSecretExisting` to the template and the 9 locale files (`@i18n-key`)
    - **Success:** `scripts/test_runner.py handlers --coverage` passes; `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` passes; flake8 and mypy clean; each new test failed before the fix.
    - **Completed:** 2026-11-05
    - **Learnings:**
        - `@require_auth` runs `_enforce_private_chat` first and, under `private_only`, already refuses a group. The new gate only matters under `allow_all`, so its test sets `security.chatMode: allow_all` and patches `src.bot.handlers.auth.config` too.
        - The 3 new tests failed first (`token_hex` called on a stored secret; no refusal in a group), then passed.
        - The existing webhook strings are English in every locale; the new key is translated in each one anyway (`nl-be` in Netherlands Dutch).
    - **Key Changes:**
        - `src/bot/handlers/webhooks.py`: `show_menu` refuses a non-private chat before the admin gate (key `PrivateChatOnly`); `setup_service` shows the stored secret (`WebhookSecretExisting`, `str()` for an int secret) and generates only when none is stored.
        - `translations/addarr.template.yml` and 9 locale files: new key `WebhookSecretExisting`.
        - `tests/test_handlers/test_webhooks_handler.py`: `TestPrivateChatOnly`, existing-secret test (str and int secret).
    - **Notes:** `regenerate_secret` is unchanged and is the only path that replaces a stored secret.

### Phase 3: Integration and gate (1 task)

**Goal:** The wizard works end to end through the real handler chain, and the full CI gate passes.

- [ ] **3.1** Webhook wizard integration test
    - **Context:**
        - **Why:** The handler flow changed (Back, Cancel, group refusal, show-secret). The skill requires an end-to-end check for a changed user-facing flow, and `tests/integration/` has none for webhooks.
        - **Architecture:** `BotHarness` (`tests/integration/conftest.py`) already registers `WebhooksHandler` in `_register_handlers`. It exposes `send_command`, `tap_button`, `send_text` and `get_conversation_state("webhooks_conversation")`. `find_response` is in `tests/integration/fixtures.py`.
        - **Key refs:** `tests/integration/test_system_flow.py` and `tests/integration/test_cancel_flow.py` as patterns; `tests/conftest.py:99` (`MockConfig` webhooks defaults); `tests/test_handlers/test_webhooks_handler.py` fixture `webhook_handler_config` (patch `src.bot.handlers.webhooks.config`).
        - **Watch out:** The harness user 12345 must be an admin and webhooks must be enabled in the patched config. The group case needs an update whose chat type is `group`; check what `make_command_update` in `tests/integration/fixtures.py` supports and extend it only if needed.
    - **Scope:** One new integration test file, plus the full preflight.
    - **Touches:** `tests/integration/test_webhooks_flow.py` (new), possibly `tests/integration/fixtures.py`
    - **Action items:**
        - [RED] Write integration tests: `/webhooks` shows the menu; tapping a configured service shows the stored secret and `wh_back` returns to the menu
        - [RED] Write integration tests: the port button shows Cancel; `menu_cancel` ends the conversation (`get_conversation_state` is None) and `send_text("8080")` does not save the port
        - [RED] Write an integration test: `/webhooks` in a group is refused
        - [GREEN] Fix any wiring gap the tests expose
        - [GREEN] Run the flow preflight (`references/preflight.md`): flake8, mypy, i18n, unit tests with the 100% gate, integration, architecture, all through `<lock>`
    - **Success:** `pytest tests/integration` passes; the preflight is green; requirement pins unchanged.
