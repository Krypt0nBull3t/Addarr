# Tasks: Issue #19 — Convert Transmission API Client from Sync to Async

## Phase 1: API Client

- [x] **1.1 Update test fixtures** — `tests/test_api/conftest.py`
  - Add `transmission_client` fixture (imports `TransmissionClient`, returns instance)
  - Add `transmission_url` fixture (returns `"http://localhost:9091"`)

- [x] **1.2 Rewrite API tests** — `tests/test_api/test_transmission_api.py`
  - Remove all `@patch("requests.post")`, `MagicMock`, `BaseApiClient` workarounds
  - Use `aioresponses` (`aio_mock` fixture) + `@pytest.mark.asyncio`
  - `TestTransmissionInit`: URL construction (http/https), auth (with/without credentials)
  - `TestTransmissionMakeRequest`: success (200), session ID negotiation (409→200), connection error
  - `TestTransmissionDelegates`: `get_session()`, `set_alt_speed_enabled(True/False)`
  - `TestTransmissionTestConnection`: success, failure

- [x] **1.3 Implement async client** — `src/api/transmission.py`
  - Standalone class `TransmissionClient` (no `BaseApiClient`)
  - `__init__`: read config, build `rpc_url`, create `aiohttp.BasicAuth` if credentials
  - `async _make_request(method, arguments)`: `aiohttp.ClientSession` + retry on 409
  - `async get_session()`, `async set_alt_speed_enabled()`, `async test_connection()`
  - Verify: `pytest tests/test_api/test_transmission_api.py -v`

## Phase 2: Service Layer

- [x] **2.1 Rewrite service tests** — `tests/test_services/test_transmission_service.py`
  - `NoClient` + `WithMockClient` classes: convert to `async def` + `@pytest.mark.asyncio`
  - Replace `MagicMock()` with `AsyncMock()` for async API methods
  - Update `patch` target from `TransmissionAPI` to `TransmissionClient`
  - `Enabled` and `Client` test classes stay sync

- [x] **2.2 Convert service to async** — `src/services/transmission.py`
  - Import `TransmissionClient` instead of `TransmissionAPI`
  - `client` property stays sync, type hint → `TransmissionClient`
  - `async def test_connection()`, `async def set_alt_speed()`, `async def get_status()`
  - `is_enabled()` stays sync
  - Verify: `pytest tests/test_services/test_transmission_service.py -v`

## Phase 3: Handler

- [x] **3.1 Update handler tests** — `tests/test_handlers/test_transmission_handler.py`
  - `mock_service.get_status` → `AsyncMock(...)` (4 tests)
  - `mock_service.set_alt_speed` → `AsyncMock(...)` (2 tests)
  - `mock_service.is_enabled` stays `MagicMock` (still sync)

- [x] **3.2 Add `await` in handler** — `src/bot/handlers/transmission.py`
  - Line 51: `status = await self.service.get_status()`
  - Line 88: `status = await self.service.get_status()`
  - Line 91: `if await self.service.set_alt_speed(not current_state):`
  - Verify: `pytest tests/test_handlers/test_transmission_handler.py -v`

## Phase 4: Cleanup

- [x] **4.1 Update mock config** — `tests/conftest.py`
  - Add `"ssl": False` to the `transmission` mock config dict

- [x] **4.2 Remove unused deps** — `requirements.txt`
  - Remove `requests>=2.31.0`
  - Remove `transmission-rpc>=3.0.0`

- [x] **4.3 Full verification**
  - `pytest --tb=short -q` — full suite, no regressions
  - `flake8 .` — no lint errors
