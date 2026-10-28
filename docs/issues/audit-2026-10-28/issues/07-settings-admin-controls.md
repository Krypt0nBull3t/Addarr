---
title: "Settings and admin controls do the wrong thing"
labels: [bug, security, ux, agent-ready, priority:critical]
slice: 7
findings: [F072, F070, F071, F073]
---

## Bug

Several /settings controls show wrong data, use a broken admin check, or claim changes that do not happen.

- **F072** The Users menu shows "Allowlist (N users)" with the count of `authenticated_users`. Turning the allowlist on with an empty `allow_list` locks out all non-admins.
- **F070** /settings and /webhooks import `src.definitions.is_admin`. That copy compares ints only, raises `TypeError` on an empty `admins:`, and reads `./config.yaml` from the working directory.
- **F071** The service toggle writes `enable`, but the clients are cached at boot (MediaService; SABnzbd `_enabled` is frozen). After "disabled radarr" the bot keeps adding movies. After enabling SABnzbd, the bot says "Speed limit set" but skips the call.
- **F073** Calendar Add is unreachable: the *arr calendars list only library items, so `in_library` is always true. If reached, it skips `adminRestrictions`. The `defaultProfileId` setting is read only there.

## Steps to reproduce

F072:

1. Have 5 entries in `authenticated_users` and an empty `allow_list`.
2. Open /settings, then Users. The button says "Allowlist (5 users)".
3. Tap it to turn the allowlist on.
4. Every non-admin is locked out.

F070:

1. Set `admins:` with no value, or list an admin id as a quoted string.
2. Send /settings. The empty case raises `TypeError`. The quoted id is refused as non-admin.
3. Start the bot from another directory. /settings reads `./config.yaml` from that directory.

F071:

1. Open /settings, then Services, and turn Radarr off. The bot says "disabled radarr".
2. Send /movie and add a movie. It is added.
3. Turn SABnzbd on and set a speed limit. The bot says "Speed limit set", but nothing is sent.

F073:

1. Send /upcoming. Every item is already in the library, so no Add button shows.
2. Set a default quality profile in /settings. Nothing else uses it.

## Expected behavior

- The Allowlist button counts the `allow_list` entries.
- /settings and /webhooks use the same admin check as the rest of the bot.
- A service toggle says that a restart is needed.
- No calendar add path exists that no button reaches.
- When a default quality profile is set for a service, the add flow uses it and skips the quality picker.

## Fix

- [ ] **F072** Pass `len(config.get("allow_list") or [])` as the allowlist count (`src/bot/handlers/settings.py:659`, `:699`; `src/bot/keyboards.py:297`)
- [ ] **F070** Import `is_admin` from `src.utils.helpers` and delete the copy (`src/bot/handlers/settings.py:37`, `src/bot/handlers/webhooks.py:29`, `src/definitions.py:60-62`)
- [ ] **F071** Add "Restart the bot for this to take effect" to the toggle reply, as `WebhookPortSaved` does (`src/bot/handlers/settings.py:320-348`, `:609`; `src/services/media.py:40-60`; `src/services/sabnzbd.py:41`)
- [ ] **F073** Delete the calendar add path (`src/services/media.py:573`, `src/bot/handlers/calendar.py:30`, `:142-184`). Keep the /settings default quality profile (`src/bot/handlers/settings.py:375-430`). In the normal add flow, read `<service>.quality.defaultProfileId`. When it is set for that service, use it and skip the quality picker.

## Acceptance criteria

Each test below fails before the fix and passes after it.

- **F072** `tests/test_handlers/test_settings_handler.py`: with 5 `authenticated_users` and an empty `allow_list`, the Users menu and the toggle reply both build the keyboard with an allowlist count of 0.
- **F070** `tests/test_handlers/test_settings_handler.py` and `test_webhooks_handler.py`: with `admins: None` there is no `TypeError`. With `admins: ["12345"]`, user 12345 is an admin. The check uses the patched config, not `./config.yaml`.
- **F071** `tests/test_handlers/test_settings_handler.py`: the toggle reply contains the restart notice key. The new key exists in the template and all 9 locales.
- **F073** `tests/test_handlers/test_media_handler.py`: with `radarr.quality.defaultProfileId` set, adding a movie sends that profile id and never shows the quality picker. With no default set, the quality picker shows as before. The calendar add tests are removed with the code.
- `pytest`, `flake8`, `mypy src/` and `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` pass.

## Notes

- Source: audit 2026-10-28, docs/issues/audit-2026-10-28/FINDINGS.md (F-ids F072, F070, F071, F073).
- Priority: max P 40, sum P 116 (critical).
- Dependencies: slices 1-8 go first. Do F070 before slice 31: F260 deletes the rest of `src/definitions.py` (`load_config` to `is_allowed_chat`) once nothing imports it.
- Decided 2026-10-28: F073 delete the calendar add path. Keep the /settings default quality profile and skip the quality picker when a default is set for that service.
