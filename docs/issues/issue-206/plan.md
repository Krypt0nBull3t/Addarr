# Webhook setup resets and leaks secrets; server binds 0.0.0.0 (#206) Implementation Plan

**Goal:** Fix the eight webhook findings F100, F012, F104, F102, F103, F106, F101 and F105 from the 2026-10-28 audit.

**Architecture:** Two layers change. `src/services/webhook.py` gets a safe default host, a byte-safe secret compare and one start-up warning. `src/bot/handlers/webhooks.py` gets a private-chat gate, a "show, do not reset" setup step and three small flow fixes (Close, Cancel, Back). Docs and one translation key follow.

**Tech Stack:** python-telegram-bot 22.8 (`ConversationHandler`), aiohttp, pytest with `aioresponses` and the `MockConfig` fixtures.

**Spec:** GitHub issue #206 (`docs/issues/audit-2026-10-28/issues/11-webhooks.md`). Decisions confirmed by the orchestrator:

- F012 reuses the existing key `PrivateChatOnly`; no new key for the refusal.
- Existing configs that already hold `webhooks.host` keep it. The fix changes only the default. No config migration.
- The PR body says that remote *arr apps need `webhooks.host: 0.0.0.0`.

## Global Constraints

- Branch `fix/206-webhook-setup-secrets`, PR targets `development`.
- Config access uses `config.get(...)`, never `config["key"]`.
- Handler tests patch `src.bot.handlers.webhooks.config`; service tests patch `src.services.webhook.config`.
- Every test, gate and push runs through the suite lock (`<lock>`), with the worktree `.venv`.
- A new translation key goes into `translations/addarr.template.yml` and all 9 locale files; `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` must pass.
- No `.venv` of the main checkout. No force push.

## Review Focus

- Secret stored as an all-digit YAML int: setup must show it as text, and the compare must still work (`str()` first, then `.encode()`).
- Header holding a lone surrogate (aiohttp decodes headers with `surrogateescape`): compare must return False, not raise `UnicodeEncodeError`.
- `/webhooks` from a group when `chatMode: private_only`: the generic gate in `@require_auth` already blocks it; the new gate must not double-reply.
- `menu_cancel` tapped while the port prompt is open must end the conversation and not leave `WEBHOOK_CHANGE_PORT` active.
- `adminNotifyId` as the string `"0"` or `None`: one warning, not one per event and not zero.

---

### Task 1: Service hardening (F104, F105, F106)

**Files:**
- Modify: `src/services/webhook.py:54`, `:70`, `:78` (host default), `:104-108` (compare), `start()` (warning)
- Modify: `config_example.yaml:93-96`, `docker-compose.yml:12-21`, `.claude/skills/security-audit/SKILL.md:58`
- Test: `tests/test_services/test_webhook_service.py`

**Interfaces:**
- Consumes: `config.get("webhooks", {})`, `config.get("logging", {})`.
- Produces: `WebhookService._host` defaults to `"127.0.0.1"`; `_validate_secret` never raises on text input; `start()` logs one `logger.warning` when `logging.adminNotifyId` is falsy or `"0"`.

- [ ] **Step 1: Write the failing tests**
  - `TestHostDefault.test_host_defaults_to_loopback`: webhooks enabled, no `host` key; after `WebhookService()` assert `service._host == "127.0.0.1"`. Add `test_configured_host_is_kept` with `host: "0.0.0.0"` (existing configs keep their value).
  - `TestSecretValidation.test_non_ascii_secret_is_rejected`: `_validate_secret("radarr", "é") is False`; `test_lone_surrogate_secret_is_rejected`: `"\udce9"` gives False.
  - `TestWebhookEndpoints.test_non_ascii_secret_header_returns_401`: POST `/webhooks/radarr` with header `X-Api-Secret: é` returns 401.
  - `TestAdminNotifyWarning`: with `logging.adminNotifyId` set to `0`, `""`, `None` and `"0"` (parametrize), `await service.start()` (with `web.TCPSite` and `web.AppRunner` patched as in `test_start_creates_runner`) logs exactly one warning containing `adminNotifyId` (use `caplog` or patch `logger`); with `12345` it logs none.
- [ ] **Step 2: Run tests, confirm each fails**
  Run: `<lock> .venv/bin/python -m pytest tests/test_services/test_webhook_service.py -v`
  Expected: the new tests FAIL (host is `0.0.0.0`, `TypeError`/500 on `é`, no warning).
- [ ] **Step 3: Implement in `src/services/webhook.py`**
  - Replace the three `"0.0.0.0"` defaults with `"127.0.0.1"`.
  - In `_validate_secret`, compare `str(provided).encode("utf-8", "surrogateescape")` with `str(configured).encode("utf-8", "surrogateescape")` in `hmac.compare_digest`.
  - Add `_warn_if_admin_notify_missing()` (private method) called in `start()` after the `_enabled` check: warn once when `config.get("logging", {}).get("adminNotifyId")` is falsy or `str(...).strip() == "0"`. Message: webhook events are dropped because `logging.adminNotifyId` is not set; set it to a Telegram chat id.
- [ ] **Step 4: Docs and config**
  - `config_example.yaml`: `host: 127.0.0.1` with a comment that the default listens on this machine only and that *arr apps on another host need `host: 0.0.0.0`; comment on `port` that it is TCP, plain HTTP, must be reachable by the *arr apps and that firewall or Docker must allow it.
  - `docker-compose.yml`: replace "(no listening ports)" with a note that the optional webhook receiver listens on `webhooks.host:webhooks.port` (default `127.0.0.1:8080`, host networking exposes it on the host), and that remote *arr apps need `host: 0.0.0.0`.
  - `.claude/skills/security-audit/SKILL.md:58`: default is now `127.0.0.1:8080`.
- [ ] **Step 5: Run tests, confirm pass**
  Run: `<lock> .venv/bin/python scripts/test_runner.py services --coverage` and `<lock> .venv/bin/python -m pytest tests/test_architecture --tb=short -v`
  Expected: PASS.
- [ ] **Step 6: Commit** `fix: harden webhook server host, secret compare and admin notify warning (#206, task 1)`

### Task 2: Handler flow fixes (F101, F102, F103) with the Cancel keyboard

**Files:**
- Modify: `src/bot/handlers/webhooks.py` (`get_handler`, `prompt_port`, `handle_close`), `src/bot/keyboards.py` (new `get_webhook_port_keyboard`)
- Test: `tests/test_handlers/test_webhooks_handler.py`, `tests/test_bot/test_keyboards.py` (or the file that tests the webhook keyboards)

**Interfaces:**
- Produces: `get_webhook_port_keyboard() -> InlineKeyboardMarkup` with one Cancel button (text from `TranslationService().get_text("Cancel")`) and `callback_data="menu_cancel"`.

- [ ] **Step 1: Write the failing tests**
  - `TestBackToMenu.test_wh_back_registered_in_webhook_menu`: from `handler.get_handler()[0].states[States.WEBHOOK_MENU]`, one `CallbackQueryHandler` matches `wh_back` (use its `pattern`).
  - `TestClose.test_close_keeps_unrelated_user_data`: `context.user_data["other"] = 1`; after `handle_close` it is still there.
  - `TestPortChange.test_prompt_port_has_cancel_button`: the `reply_markup` passed to `edit_text` holds a button with `callback_data == "menu_cancel"`.
  - `TestPortChange.test_menu_cancel_is_a_fallback`: a fallback `CallbackQueryHandler` matches `menu_cancel`; calling it returns `ConversationHandler.END`.
  - `TestPortChange.test_text_after_cancel_is_not_saved_as_port`: with the fallback registered, `states[WEBHOOK_CHANGE_PORT]` is not reached after `menu_cancel`; assert `save_port` is not called and the saved port stays `8080` (drive `ConversationHandler.handle_update` or assert on `check_update` for a text update after the END; pick whichever the existing tests of other conversations use).
  - Keyboard test: `get_webhook_port_keyboard()` has one row, one button, `callback_data == "menu_cancel"`.
- [ ] **Step 2: Run tests, confirm each fails**
  Run: `<lock> .venv/bin/python -m pytest tests/test_handlers/test_webhooks_handler.py -v`
- [ ] **Step 3: Implement**
  - `get_handler`: add `CallbackQueryHandler(self._back_to_menu, pattern="^wh_back$")` to `WEBHOOK_MENU`; add `CallbackQueryHandler(self.handle_close, pattern="^menu_cancel$")` to `fallbacks`.
  - `handle_close`: delete `context.user_data.clear()`.
  - `prompt_port`: pass `reply_markup=get_webhook_port_keyboard()` to `edit_text`. Import it from `src.bot.keyboards`.
- [ ] **Step 4: Run tests, confirm pass; then handler scope**
  Run: `<lock> .venv/bin/python scripts/test_runner.py handlers --coverage`
- [ ] **Step 5: Commit** `fix: webhook Back, Close and port Cancel (#206, task 2)`

### Task 3: Private-chat gate and stable secrets (F012, F100)

**Files:**
- Modify: `src/bot/handlers/webhooks.py` (`show_menu`, `setup_service`), `translations/addarr.template.yml` plus 9 locale files (new key `WebhookSecretExisting`)
- Test: `tests/test_handlers/test_webhooks_handler.py`

**Interfaces:**
- Produces: translation key `WebhookSecretExisting` with placeholders `%{service}`, `%{url}`, `%{secret}`; text says the secret is already set, repeats URL and secret, and says Regenerate makes a new one (old *arr webhooks then stop working).

- [ ] **Step 1: Write the failing tests**
  - `TestShowMenu.test_group_chat_is_refused`: update with `effective_chat.type = "group"` (set on the `make_update` result) and `security.chatMode: allow_all`: `show_menu` returns `ConversationHandler.END`, replies `PrivateChatOnly`, and no reply contains a secret.
  - `TestShowMenu.test_private_chat_still_works` (guards the happy path).
  - `TestSetupService.test_setup_service_shows_existing_secret`: `wh_setup_radarr` (fixture has `radarr_secret = "existing-radarr-secret"`), `secrets.token_hex` patched to return `"new"`: stored secret is still `"existing-radarr-secret"`, `config.save` not called, the edited text contains `existing-radarr-secret`, the keyboard has a `wh_regen_radarr` button.
  - `test_setup_service_shows_numeric_secret_as_text`: stored `12345678` (int) shows `12345678` and saves nothing.
  - Keep `test_setup_service_generates_secret` (sonarr has no secret) green.
- [ ] **Step 2: Run tests, confirm each fails**
- [ ] **Step 3: Implement**
  - `show_menu`: before the admin gate, `if update.effective_chat and update.effective_chat.type != "private":` reply `get_text("PrivateChatOnly")` and return `ConversationHandler.END`. Keep `@require_auth` first.
  - `setup_service`: read `existing = webhook_config.get(f"{service}_secret")`. If set, use `str(existing)`, text key `WebhookSecretExisting`, no `token_hex`, no save. Else the current generate-and-save path. Both paths share the `url`, keyboard and return.
  - Add `WebhookSecretExisting` to the template and all 9 locales (nl-be in Netherlands Dutch wording, not Flemish).
- [ ] **Step 4: Run scoped checks**
  Run: `<lock> .venv/bin/python scripts/test_runner.py handlers --coverage` and `PYTHONIOENCODING=utf-8 <lock> .venv/bin/python run.py --validate-i18n`
- [ ] **Step 5: Commit** `fix: show existing webhook secret and refuse /webhooks outside private chats (#206, task 3)`

### Task 4: Integration test and full gate

**Files:**
- Create: `tests/integration/test_webhooks_flow.py` (pattern: `tests/integration/test_system_flow.py`, `BotHarness` from `tests/integration/conftest.py`)

- [ ] **Step 1:** Happy path through the harness: `/webhooks` as an admin in a private chat shows the menu; tapping a configured service shows the existing secret; Back returns to the menu; the port button shows Cancel; `menu_cancel` ends the flow. A group `/webhooks` is refused.
- [ ] **Step 2:** Run `<lock> .venv/bin/python -m pytest tests/integration --tb=short -v`.
- [ ] **Step 3:** Flow preflight from `references/preflight.md` (flake8, mypy, i18n, unit with the 100% gate, integration, architecture), through `<lock>`.
- [ ] **Step 4: Commit** `test: webhook wizard integration flow (#206, task 4)`
