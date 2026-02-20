# Fix: Add Transmission Health Checks to HealthService (Issue #22)

## Context

`HealthService.run_health_checks()` monitors media services (Radarr, Sonarr, Lidarr) and SABnzbd, but **Transmission is missing**. When Transmission is enabled in config, it should appear in `download_clients` results alongside SABnzbd — with version info on success, and descriptive errors on failure.

**Design decision**: Delegate to `TransmissionClient` rather than making direct HTTP calls (unlike SABnzbd/media checks). Transmission uses an RPC protocol with 409 session ID negotiation that `TransmissionClient` already handles. Reimplementing it would be duplication.

The method takes **no parameters** — `TransmissionClient.__init__` reads config internally (flat structure: `host`, `port`, `ssl`, `username`, `password`). Only the `enable` flag is needed from `run_health_checks()`.

## Files to Modify

| File | Change |
|---|---|
| `tests/test_services/test_health_service.py` | Add `TestCheckTransmissionHealth` (5 tests) + 3 integration tests to `TestRunHealthChecks` |
| `src/services/health.py` | Add import, `check_transmission_health()` method, Transmission block in `run_health_checks()` |

## TDD Steps

### Step 1 — RED: Write failing tests

Add `TestCheckTransmissionHealth` class after `TestCheckSabnzbdHealth` (~line 391). Mock via `patch("src.services.health.TransmissionClient")`:

| Test | Mock behavior | Expected return |
|---|---|---|
| `test_check_transmission_health_success` | `get_session()` returns `{"arguments": {"version": "4.0.0"}, "result": "success"}` | `(True, "Online (v4.0.0)")` |
| `test_check_transmission_health_missing_version` | `get_session()` returns `{"arguments": {}, "result": "success"}` | `(True, "Online (vUnknown)")` |
| `test_check_transmission_health_connection_error` | `get_session()` raises `aiohttp.ClientConnectorError` | `(False, "Error: Connection failed")` |
| `test_check_transmission_health_timeout` | `get_session()` raises `asyncio.TimeoutError()` | `(False, "Error: Connection timeout")` |
| `test_check_transmission_health_generic_exception` | `get_session()` raises `RuntimeError("Unexpected")` | `(False, "Error: Unexpected")` |

Add 3 integration tests to `TestRunHealthChecks`:

| Test | Config setup | Assertion |
|---|---|---|
| `test_run_health_checks_transmission_enabled` | Patch config with transmission `enable: True` | `download_clients` contains `{"name": "Transmission", ...}`, `check_transmission_health` called once |
| `test_run_health_checks_transmission_disabled` | Default config (transmission `enable: False`) | `check_transmission_health` NOT called, no Transmission in results |
| `test_run_health_checks_both_download_clients` | Both transmission + sabnzbd enabled | `download_clients` has 2 entries: Transmission and SABnzbd |

### Step 2 — GREEN: Implement

**`src/services/health.py`** — Add import:
```python
from src.api.transmission import TransmissionClient
```

**`src/services/health.py`** — Add method after `check_sabnzbd_health` (~line 221):
```python
async def check_transmission_health(self) -> Tuple[bool, str]:
    """Check Transmission connection via RPC client."""
    try:
        client = TransmissionClient()
        data = await client.get_session()
        version = data.get("arguments", {}).get("version", "Unknown")
        return True, f"Online (v{version})"
    except aiohttp.ClientConnectorError:
        return False, "Error: Connection failed"
    except asyncio.TimeoutError:
        return False, "Error: Connection timeout"
    except Exception as e:
        return False, f"Error: {str(e)}"
```

**`src/services/health.py`** — Add Transmission block in `run_health_checks()` before the SABnzbd block (~line 256):
```python
# Check Transmission
transmission = config.get("transmission", {})
if transmission.get("enable"):
    is_healthy, status = await self.check_transmission_health()
    results["download_clients"].append({
        "name": "Transmission",
        "healthy": is_healthy,
        "status": status
    })
```

### Step 3 — Verify

```bash
pytest tests/test_services/test_health_service.py -v
pytest --tb=short -q
flake8 src/services/health.py tests/test_services/test_health_service.py
```

## Existing test compatibility

The existing `test_run_health_checks_sabnzbd_enabled` patches `config.get` with a `side_effect` that only handles `sabnzbd`/`radarr`/`sonarr`/`lidarr`. For `transmission`, it falls through to `default={}`, so `{}.get("enable")` is falsy — the Transmission block is skipped. No breakage.

## Verification

1. `pytest tests/test_services/test_health_service.py -v` — all tests pass including 8 new ones
2. `pytest --tb=short -q` — full suite green
3. `flake8 src/services/health.py tests/test_services/test_health_service.py` — clean
4. `python scripts/test_runner.py services --coverage` — `check_transmission_health` fully covered
