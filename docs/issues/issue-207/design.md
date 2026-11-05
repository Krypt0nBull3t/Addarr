# Issue 207: Download client failures look like success

## Intent

A down download client, a wrong key or a stale button must show an error or act on the right client. Today the bot shows success, an empty queue or the wrong client's data. Seven defects (F080 to F086) share this cause.

## Goals

- F082: the setup wizard writes the keys that `TransmissionClient` reads (`host`, `port`).
- F080: a service action that returns `False` shows an error text, not the success text.
- F081: a failed queue fetch shows an error, not `DownloadsEmpty`.
- F083: the wizard rejects a wrong SABnzbd API key.
- F084: a download button acts on the client it was drawn for.
- F085: Refresh with a stale `dl_page` shows the last page with its nav row.
- F086: the SABnzbd remaining size comes from `sizeleft`.

## Non-goals

- No change to the `/downloads` layout, tabs or button labels.
- No change to the SABnzbd or Transmission request logic, except the checks above.
- No change to `get_history` error handling (see call 3).

## Findings from the code (line numbers checked on `origin/development` cf51f57)

- `src/services/sabnzbd.py:225-238` and `src/services/transmission.py:107-160` return an `empty` dict on every error. The handler cannot tell it from a real empty queue.
- A wrong SABnzbd key returns HTTP 200 with `{"status": false, "error": "API Key Incorrect"}`. It has no `queue` key.
- `src/setup/service_config.py:150-162` returns `server` and `auth` for Transmission. `src/api/transmission.py:21-23` reads `host`, `port` and `ssl`.
- `src/setup/validators.py:44` sends `mode=version`. SABnzbd answers that call without a key. The check at `:71` looks for the key `version`.
- `src/bot/handlers/downloads.py:85` picks the service from `user_data["dl_client"]`. `_parse_item_id` and the admin check use the same value.
- `src/bot/keyboards.py:861` `_build_dl_pagination_row` does not clamp the page. `_build_pagination_row` (from #223) clamps inside the row only. No shared clamp function exists.

## Design

- **F082.** For Transmission, `get_valid_service_config` returns `{"host", "port"}` in the success and the skip case. It does not write `ssl`: `config_example.yaml` has no Transmission `ssl` key, and #225 (F253) aligns the config mock with the example. A small helper builds the dict, so the four blocks do not repeat.
- **F080.** `sabnzbd.py` handler and the three Settings handlers check the returned bool. On `False` they show the existing error text (`Sabnzbd.Error` in the handler, the existing "could not complete action" text in Settings). No new key.
- **F081.** `get_queue_details` returns `Optional[Dict]`. It returns `None` on an HTTP error, an exception, a missing client, and a SABnzbd reply without a `queue` key. The handler shows a new translation key (`DownloadsFetchError`) in all 9 locale files. The error view keeps a keyboard with the client switcher (multi-client mode) and Refresh, so the user can switch to the other client.
- **F083.** The SABnzbd check sends `mode=queue` and accepts a reply with the key `queue`. Other services still need `version`.
- **F084.** In multi-client mode the keyboard builds `dl_pause_<c>_<id>` and `dl_resume_<c>_<id>`, where `<c>` is `sab` or `tx`. The handler reads the client from the callback and falls back to `user_data` for old buttons without it. A SABnzbd id starts with `SABnzbd_nzo_`, so no id can look like a client prefix. `_do_action` takes the client as an argument, so the admin check and the service match the button. Single-client mode keeps the old format, because no mismatch is possible.
- **F085.** Add `clamp_page(page, total_pages)` in `src/bot/keyboards.py`. `_build_pagination_row` uses it, so the logic exists once. The two downloads keyboards and `_refresh_current_view` use it too. The handler stores the clamped page in `user_data` and passes it to the history text. `_build_dl_pagination_row` stays (replacing it is #223).
- **F086.** `size_remaining` reads `queue.get('sizeleft', '0 MB')`.

## Decisions (confirmed by the orchestrator, 2026-11-05)

1. F084 covers the four action buttons: item pause, item resume, Pause All, Resume All.
2. The F081 error view has a keyboard (client switcher in multi-client mode, and Refresh).
3. `get_history` is unchanged. The PR body names it as a follow-up.
4. One shared `clamp_page(page, total_pages)`, as in the F085 design above.
5. F082 writes `host` and `port` only.
6. New translation key `DownloadsFetchError` in the template and the 9 locale files.

## Left to the builder

Test names, the helper name for the wizard dict, and the exact wording of the new text (it follows the style of `DownloadsPauseError`).
