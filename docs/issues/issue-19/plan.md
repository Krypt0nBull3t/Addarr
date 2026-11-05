# Plan: Convert Transmission API Client from Sync to Async

## Context

Issue #19. `src/api/transmission.py` uses synchronous `requests.post()` while all other API clients use async `aiohttp`. This blocks the event loop during Transmission API calls. The fix converts it to async, matching the pattern used by Radarr/Sonarr/Lidarr clients.

## Design Decisions

1. **Drop `BaseApiClient` inheritance** — The RPC protocol (single endpoint, method+arguments body, session ID negotiation) is fundamentally different from the REST pattern `BaseApiClient` assumes. All 3 other clients (Radarr, Sonarr, Lidarr) are standalone. The current inheritance is also broken (missing `service_name` arg, no `search()` impl).

2. **Rename `TransmissionAPI` → `TransmissionClient`** — Matches naming convention of `RadarrClient`, `SonarrClient`, `LidarrClient`, `SabnzbdClient`.

3. **Read config directly in `__init__`** — Like other clients, read from `config["transmission"]` instead of accepting explicit constructor args. Simplifies the service layer.

4. **Retry loop for session ID negotiation** — Replace recursive `_make_request` call with a `for attempt in range(2)` loop. Avoids async recursion.

5. **Remove `requests` and `transmission-rpc` from requirements.txt** — `requests` is only used in `src/api/transmission.py`. `transmission-rpc` is never imported anywhere.

## Files Modified

| File | Change |
|------|--------|
| `src/api/transmission.py` | Full rewrite: sync→async, drop BaseApiClient, rename class |
| `src/services/transmission.py` | Methods→async, update import |
| `src/bot/handlers/transmission.py` | Add 3 `await` keywords |
| `tests/test_api/conftest.py` | Add transmission fixtures |
| `tests/test_api/test_transmission_api.py` | Full rewrite: aioresponses |
| `tests/test_services/test_transmission_service.py` | Async tests + AsyncMock |
| `tests/test_handlers/test_transmission_handler.py` | AsyncMock for service |
| `tests/conftest.py` | Add `ssl` to mock config |
| `requirements.txt` | Remove `requests`, `transmission-rpc` |

## Verification

1. `pytest tests/test_api/test_transmission_api.py -v` — API tests pass
2. `pytest tests/test_services/test_transmission_service.py -v` — Service tests pass
3. `pytest tests/test_handlers/test_transmission_handler.py -v` — Handler tests pass
4. `pytest --tb=short -q` — Full suite, no regressions
5. `flake8 .` — No lint errors
