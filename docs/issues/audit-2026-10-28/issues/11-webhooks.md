---
title: "Webhook setup resets and leaks secrets; server binds 0.0.0.0"
labels: [bug, security, agent-ready, priority:high]
slice: 11
findings: [F100, F012, F104, F102, F103, F106, F101, F105]
---
## Bug

- **F100** Tapping an already set-up service in /webhooks makes a new secret at once. Existing *arr webhooks then get 401.
- **F012** In a group with `chatMode: allow_all`, /webhooks posts the new secret into the group.
- **F104** The webhook server binds `0.0.0.0` over plain HTTP by default (bandit B104 x3). The docker-compose comment says "no listening ports".
- **F102** Close runs `user_data.clear()`. This wipes the state of other open flows.
- **F103** The port prompt has no Cancel button, and `menu_cancel` is not in the fallbacks. After Cancel elsewhere, typed text is read as a port.
- **F106** When `logging.adminNotifyId` is empty or 0 (the wizard writes 0), every event returns 200 and is dropped with no log.
- **F101** Back (`wh_back`) has no handler in `WEBHOOK_MENU`.
- **F105** A non-ASCII `X-Api-Secret` makes `hmac.compare_digest(str, str)` raise TypeError: HTTP 500 and a traceback (reproduced).

## Steps to reproduce

1. **F100** Set up Radarr in /webhooks and enter the URL and secret in Radarr. Run /webhooks again and tap Radarr. A new secret is saved. Radarr's next webhook gets 401.
2. **F012** Set `security.chatMode: allow_all`. Run /webhooks in a group and tap a service. The secret is posted in the group.
3. **F104** Turn webhooks on and leave `webhooks.host` unset. The server listens on `0.0.0.0` over HTTP.
4. **F102** Start a flow that keeps data in `user_data`. Open /webhooks and tap Close. The other flow has lost its data.
5. **F103** Run /webhooks and tap the port button. Tap Cancel in another menu. Type `8080`: it is saved as the webhook port, not searched.
6. **F106** Leave the admin notify id empty in the wizard (it writes 0). Send a test webhook from Radarr. The server returns 200. Nothing is sent and nothing is logged.
7. **F101** Run /webhooks, tap a service, then tap Back. Nothing happens.
8. **F105** Send a POST to `/webhooks/radarr` with the header `X-Api-Secret: é`. The server returns 500 and logs a traceback.

## Expected behavior

Tapping a set-up service shows the existing secret. Only Regenerate makes a new one. /webhooks works only in private chats. The server binds `127.0.0.1` by default, and the docs describe the port. Close leaves other flows alone. The port prompt can be cancelled. A missing admin notify id gives one warning at start. Back returns to the menu. A bad secret header gives 401, not 500.

## Fix

- [ ] **F100** Show the existing secret; only Regenerate makes a new one (`src/bot/handlers/webhooks.py:150-163`)
- [ ] **F012** Refuse /webhooks outside private chats (`src/bot/handlers/webhooks.py:166-176`)
- [ ] **F104** Default host `127.0.0.1`; fix the compose comment; document the port (`src/services/webhook.py:54`, `:70`, `:78`; `docker-compose.yml:12-21`)
- [ ] **F102** Remove the `user_data.clear()` (`src/bot/handlers/webhooks.py:347`)
- [ ] **F103** Add a `^menu_cancel$` fallback and a Cancel button to the port prompt (`src/bot/handlers/webhooks.py:271`)
- [ ] **F106** Warn once at webhook start when `adminNotifyId` is empty or 0 (`src/services/notification.py:44`, `src/setup/prompts.py:236`)
- [ ] **F101** Add `^wh_back$` to `WEBHOOK_MENU` (`src/bot/handlers/webhooks.py:53-69`, `src/bot/keyboards.py:1252`)
- [ ] **F105** Compare `.encode()` bytes in `hmac.compare_digest` (`src/services/webhook.py:108`, `:143`)

## Acceptance criteria

Each test fails before its fix and passes after:

- **F100** `tests/test_handlers/test_webhooks_handler.py`: tapping `wh_setup_radarr` when a `radarr_secret` exists shows that secret and does not save a new one.
- **F012** `tests/test_handlers/test_webhooks_handler.py`: /webhooks in a group chat sends no secret and ends the conversation.
- **F104** `tests/test_services/test_webhook_service.py`: with no `webhooks.host`, the server binds `127.0.0.1`.
- **F102** `tests/test_handlers/test_webhooks_handler.py`: after Close, an unrelated `user_data` key is still there.
- **F103** `tests/test_handlers/test_webhooks_handler.py`: the port prompt has a Cancel button, `menu_cancel` ends the conversation, and text sent after it is not saved as a port.
- **F106** `tests/test_services/test_webhook_service.py`: starting the server with `adminNotifyId` 0 or empty logs one warning.
- **F101** `tests/test_handlers/test_webhooks_handler.py`: `wh_back` in `WEBHOOK_MENU` shows the menu again.
- **F105** `tests/test_services/test_webhook_service.py`: a non-ASCII `X-Api-Secret` gives 401.
- `pytest`, `flake8` and `mypy src/` pass. If a translation key is added (for example the F012 refusal), `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` passes.

## Notes

- Source: audit 2026-10-28, docs/issues/audit-2026-10-28/FINDINGS.md (F-ids F100, F012, F104, F102, F103, F106, F101, F105).
- Priority: max P 30, sum P 175 (high).
- Order: do slices 1-8 first. Slice 7 (F070) changes the `is_admin` import in `src/bot/handlers/webhooks.py:29`.
- F104: with the new default, *arr apps on another host need `webhooks.host` set. The port docs must say so.
