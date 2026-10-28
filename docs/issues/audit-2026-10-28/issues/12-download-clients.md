---
title: "Download client failures look like success"
labels: [bug, agent-ready, priority:high]
slice: 12
findings: [F082, F080, F081, F083, F084, F085, F086]
---
## Bug

- **F082** The wizard writes `transmission.server.addr/port`. The client reads `transmission.host/port`. A remote Transmission becomes localhost:9091.
- **F080** `set_speed_limit`, `pause_queue` and `resume_queue` return False on failure. The callers ignore it and show success.
- **F081** When the client is down or the key is wrong, the service returns an empty queue dict. /downloads says "DownloadsEmpty".
- **F083** The wizard tests SABnzbd with `mode=version`, which needs no key. A wrong key passes.
- **F084** /downloads keeps the client in `user_data`. An old Transmission Pause button goes to SABnzbd with a torrent id.
- **F085** Refresh keeps `dl_page` without clamping. The result is an empty page with no nav row.
- **F086** The SABnzbd remaining size is read from `size` (total) instead of `sizeleft`.

## Steps to reproduce

1. **F082** Run `python run.py --setup` and configure Transmission on another host. Start the bot and open /downloads. The bot connects to localhost:9091.
2. **F080** Stop SABnzbd or set a wrong key. Set a speed limit, or tap pause or resume, in the SABnzbd menu or in Settings. The bot reports success.
3. **F081** Stop SABnzbd or Transmission, or set a wrong key. Open /downloads. The bot shows the empty message (`DownloadsEmpty`).
4. **F083** Run the wizard with a wrong SABnzbd API key. The connection test passes.
5. **F084** Open /downloads on the Transmission tab. Open /downloads again and switch to SABnzbd. Tap Pause on the old Transmission message. The torrent id goes to SABnzbd.
6. **F085** Open /downloads and go to the last page. Let downloads finish until there are fewer pages. Tap Refresh. The page is empty and has no nav row.
7. **F086** Start a large download in SABnzbd. The remaining size equals the total size.

## Expected behavior

The client uses the Transmission address from the wizard. A failed action shows an error. A down client or a wrong key shows an error, not "empty". The wizard rejects a wrong SABnzbd key. Each button acts on the client it was made for. Refresh clamps to the last page. The remaining size is the real remaining size.

## Fix

- [ ] **F082** Write `host`/`port` for Transmission (`src/setup/service_config.py:151-163`, `src/api/transmission.py:21-22`)
- [ ] **F080** Check the returned bool; show the error text (`src/bot/handlers/sabnzbd.py:89`; `src/bot/handlers/settings.py:610`, `:628`, `:634`)
- [ ] **F081** Return `None` on error; show the error (`src/services/sabnzbd.py:206`, `:234`, `:238`; `src/services/transmission.py:160`)
- [ ] **F083** Use `mode=queue` (`src/setup/validators.py:44`)
- [ ] **F084** Put the client in callback_data (`src/bot/handlers/downloads.py:85`)
- [ ] **F085** Clamp `dl_page` with the shared helper from slice 28 (`src/bot/handlers/downloads.py:302`)
- [ ] **F086** Read `sizeleft` for `size_remaining` (`src/services/sabnzbd.py:228`)

## Acceptance criteria

Each test fails before its fix and passes after:

- **F082** `tests/test_setup/test_service_config.py`: the Transmission config has top-level `host` and `port`, the keys `TransmissionClient` reads.
- **F080** `tests/test_handlers/test_sabnzbd_handler.py` and `tests/test_handlers/test_settings_handler.py`: when the service returns False, the reply is the error text, not the success text.
- **F081** `tests/test_services/test_sabnzbd_service.py` and `tests/test_services/test_transmission_service.py`: an HTTP error or a wrong-key response returns `None`. `tests/test_handlers/test_downloads_handler.py`: `None` shows an error, not `DownloadsEmpty`.
- **F083** `tests/test_setup/test_validators.py`: the SABnzbd check sends `mode=queue`.
- **F084** `tests/test_handlers/test_downloads_handler.py`: a Transmission button's callback_data names the client, and tapping it calls Transmission while `user_data` says SABnzbd.
- **F085** `tests/test_handlers/test_downloads_handler.py`: Refresh with `dl_page` past the last page shows the last page with its nav row.
- **F086** `tests/test_services/test_sabnzbd_service.py`: `size_remaining` comes from `sizeleft`.
- `pytest`, `flake8` and `mypy src/` pass. If a translation key is added for the error texts, `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` passes.

## Notes

- Source: audit 2026-10-28, docs/issues/audit-2026-10-28/FINDINGS.md (F-ids F082, F080, F081, F083, F084, F085, F086).
- Priority: max P 30, sum P 144 (high).
- Order: do slices 1-8 first. F085 needs the shared pagination helper from slice 28 (F265). Slice 7 (F071) changes the same Settings speed code (`src/bot/handlers/settings.py:609`). Slice 21 (F246) fixes the SABnzbd fixtures that use `size` as the remaining size.
