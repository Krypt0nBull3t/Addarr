# Issue #20: Flesh Out SABnzbd API Client

## Context

The SABnzbd API client (`src/api/sabnzbd.py`) only has `check_status()` and `set_speed_limit()`. The service layer (`src/services/sabnzbd.py`) is slightly ahead with `get_status()`, `set_speed_limit()`, and `add_nzb()`. Both layers need parity and missing operations: pause/resume queue and download history.

The two layers are **independent** — each makes its own HTTP calls. API client uses inline f-string URLs; service uses params dicts.

## Scope

**API Client — 5 new methods:**
| Method | SABnzbd Mode | Returns |
|--------|-------------|---------|
| `get_queue()` | `mode=queue` | `dict` (parsed JSON) or `{}` |
| `add_nzb(url, nzbname, category)` | `mode=addurl` | `bool` |
| `pause_queue()` | `mode=pause` | `bool` |
| `resume_queue()` | `mode=resume` | `bool` |
| `get_history(limit=10)` | `mode=history` | `dict` (parsed JSON) or `{}` |

**Service — 3 new methods** (get_status and add_nzb already exist):
| Method | Returns |
|--------|---------|
| `pause_queue()` | `bool` |
| `resume_queue()` | `bool` |
| `get_history(limit=10)` | `Dict[str, Any]` with `total`, `items` |

**Tests:** 25 new tests (16 API + 9 service), 3 per method (success, HTTP error, connection error) + 1 extra for add_nzb with optional params.

## Files

| File | Change |
|------|--------|
| `src/api/sabnzbd.py` | Add 5 methods |
| `src/services/sabnzbd.py` | Add 3 methods |
| `tests/test_api/test_sabnzbd_api.py` | Add 5 test classes (16 tests) |
| `tests/test_services/test_sabnzbd_service.py` | Add 3 test classes (9 tests) |
| `tests/fixtures/sample_data.py` | Add `SABNZBD_HISTORY` constant |

## Tasks (TDD order — grouped by feature)

### Task 1: `get_queue()` in API client
- **RED:** Write `TestSabnzbdGetQueue` (3 tests) — success returns parsed dict, HTTP error returns `{}`, connection error returns `{}`
- **GREEN:** Implement `SabnzbdClient.get_queue()` — inline URL `mode=queue`, parse JSON on 200, return `{}` on error
- **Verify:** `pytest tests/test_api/test_sabnzbd_api.py -v`

### Task 2: `add_nzb()` in API client
- **RED:** Write `TestSabnzbdAddNzb` (4 tests) — success, with optional params, HTTP error, connection error
- **GREEN:** Implement `SabnzbdClient.add_nzb(url, nzbname, category)` — inline URL `mode=addurl&name={url}`, append `&nzbname=` and `&cat=` if provided, parse JSON for `status`
- **Verify:** `pytest tests/test_api/test_sabnzbd_api.py -v`

### Task 3: `pause_queue()` in both layers
- **RED:** Write `TestSabnzbdPauseQueue` in API tests (3 tests) + `TestPauseQueue` in service tests (3 tests)
- **GREEN:** Implement in both — API client: inline URL `mode=pause`, return `response.status == 200`; Service: params dict, parse JSON `status`
- **Verify:** `pytest tests/test_api/test_sabnzbd_api.py tests/test_services/test_sabnzbd_service.py -v`

### Task 4: `resume_queue()` in both layers
- **RED:** Write `TestSabnzbdResumeQueue` in API tests (3 tests) + `TestResumeQueue` in service tests (3 tests)
- **GREEN:** Implement in both — mirrors pause_queue with `mode=resume`
- **Verify:** `pytest tests/test_api/test_sabnzbd_api.py tests/test_services/test_sabnzbd_service.py -v`

### Task 5: `get_history()` in both layers
- **RED:** Write `TestSabnzbdGetHistory` in API tests (3 tests) + `TestGetHistory` in service tests (3 tests). Add `SABNZBD_HISTORY` to `tests/fixtures/sample_data.py`
- **GREEN:** API client: inline URL `mode=history&limit={limit}`, return parsed dict or `{}`. Service: params dict, return `{'total': N, 'items': [...]}` or `{'total': 0, 'items': []}` on error
- **Verify:** `pytest tests/test_api/test_sabnzbd_api.py tests/test_services/test_sabnzbd_service.py -v`

## Patterns to Follow

**API client** (inline f-string URL, follow `check_status`/`set_speed_limit`):
```python
async def pause_queue(self) -> bool:
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{self.api_url}/api?mode=pause&output=json&apikey={self.api_key}"
            async with session.get(url) as response:
                return response.status == 200
    except Exception as e:
        logger.error(f"Error pausing SABnzbd queue: {e}")
        return False
```

**Service** (params dict, follow `set_speed_limit`/`add_nzb`):
```python
async def pause_queue(self) -> bool:
    try:
        params = {'mode': 'pause', 'output': 'json', 'apikey': self.api_key}
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/api", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('status', False)
                else:
                    logger.error(f"SABnzbd API returned status {response.status}")
                    return False
    except Exception as e:
        logger.error(f"Error pausing SABnzbd queue: {e}")
        return False
```

## Watch-outs

- API client URL: no double-slash (`http://localhost:8090/api`). Service URL: has double-slash (`http://localhost:8090//api`) due to `path: "/"` in config
- API client tests: exact URL string matching. Service tests: `SABNZBD_API_PATTERN` regex
- `get_queue()` is complementary to `check_status()` — both use `mode=queue` but `get_queue` returns data
- No handler changes — that's a separate concern

## Verification

After all tasks:
```bash
pytest tests/test_api/test_sabnzbd_api.py tests/test_services/test_sabnzbd_service.py -v
pytest --tb=short -q
flake8 src/api/sabnzbd.py src/services/sabnzbd.py
```
