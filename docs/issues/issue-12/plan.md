# Fix: SABnzbd Speed Limit Selection (Issue #12)

## Context

The SABnzbd handler (`src/bot/handlers/sabnzbd.py:90`) calls `self.sabnzbd_service.set_speed_limit(speed)` but this method doesn't exist in either `SABnzbdService` or `SabnzbdClient`. The handler and handler tests are already correct — only the service and API layers need the method added.

**SABnzbd API**: `mode=config&name=speedlimit&value=<percentage>&output=json&apikey=<key>` — returns `{"status": true}` on success.

## Files to Modify

| File | Change |
|---|---|
| `tests/test_api/test_sabnzbd_api.py` | Add `TestSabnzbdSetSpeedLimit` (3 tests) |
| `tests/test_services/test_sabnzbd_service.py` | Add `TestSetSpeedLimit` (3 tests) |
| `src/api/sabnzbd.py` | Add `set_speed_limit(percentage)` method |
| `src/services/sabnzbd.py` | Add `set_speed_limit(percentage)` method |

No changes to handler or handler tests (already correct).

## TDD Steps

### Step 1: Write API client tests
Add `TestSabnzbdSetSpeedLimit` to `tests/test_api/test_sabnzbd_api.py` with 3 tests:
- `test_set_speed_limit_success` — 200 + `{"status": true}` → returns `True`
- `test_set_speed_limit_http_error` — 500 → returns `False`
- `test_set_speed_limit_exception` — connection error → returns `False`

Pattern: use `aio_mock`, `sabnzbd_client`, `sabnzbd_url` fixtures; exact URL matching (matches `TestSabnzbdCheckStatus` pattern).

### Step 2: Write service tests
Add `TestSetSpeedLimit` to `tests/test_services/test_sabnzbd_service.py` with 3 tests:
- `test_set_speed_limit_success` — 200 + `{"status": true}` → returns `True`
- `test_set_speed_limit_http_error` — 500 → returns `False`
- `test_set_speed_limit_exception` — connection error → returns `False`

Pattern: use `aioresponses()` context manager, `SABNZBD_API_PATTERN` regex, `sabnzbd_service` fixture (matches `TestAddNzb` pattern).

### Step 3: Run tests — expect failures
```bash
pytest tests/test_api/test_sabnzbd_api.py tests/test_services/test_sabnzbd_service.py -v -x
```

### Step 4: Implement `SabnzbdClient.set_speed_limit`
Add after `check_status` in `src/api/sabnzbd.py`. Follow `check_status` pattern: inline f-string URL, `aiohttp.ClientSession`, return `bool`.

### Step 5: Implement `SABnzbdService.set_speed_limit`
Add after `add_nzb` in `src/services/sabnzbd.py`. Follow `add_nzb` pattern: params dict, `session.get(url, params=params)`, return `bool`.

### Step 6: Run all tests — expect pass
```bash
pytest tests/test_api/test_sabnzbd_api.py tests/test_services/test_sabnzbd_service.py tests/test_handlers/test_sabnzbd_handler.py -v
```

## Verification
```bash
pytest --tb=short -q                        # Full suite passes
flake8 src/api/sabnzbd.py src/services/sabnzbd.py tests/test_api/test_sabnzbd_api.py tests/test_services/test_sabnzbd_service.py
```

## Notes
- Service does NOT delegate to API client (existing pattern) — both layers get independent implementations
- No input validation needed — handler constrains speed to 25/50/100 via button callbacks
- Double-slash in service URL (`http://localhost:8090//api`) is expected; regex pattern already handles it
