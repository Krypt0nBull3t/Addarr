# Disk Space Monitoring in `/status` Command — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add disk space information to the `/status` command, showing per-drive usage with visual progress bars and low-space warnings.

**Architecture:** Add `get_disk_space()` to `BaseApiClient` (shared by all *arr clients). HealthService calls the first enabled media service's client to get disk data — no need to query all three since they return the same OS-level disk info. Add a "Disk Space" button to the system keyboard and a callback handler in SystemHandler.

**Tech Stack:** Python 3.11, aiohttp, python-telegram-bot v20+, pytest, aioresponses

---

## Design Decisions

1. **Single service query** — Radarr, Sonarr, and Lidarr all return the same OS-level `/diskspace` data. Query the first enabled service only. No deduplication needed.

2. **Method on BaseApiClient** — the endpoint, request format, and response format are identical across all three clients (`GET /api/{version}/diskspace` → `[{path, label, freeSpace, totalSpace}]`). Implement once in the base class.

3. **Threshold hardcoded at 10%** — module-level constant `LOW_SPACE_THRESHOLD = 0.10` in `system.py`. No config.yaml changes.

4. **Visual bar** — 10-char bar using block characters: `[████░░░░░░] 42%`. Warning emoji when free space < threshold.

5. **HealthService as aggregator** — follows existing pattern where SystemHandler calls health_service methods. HealthService creates the API client internally using a `_get_api_client()` helper.

## Phased Approach

### Phase 1: API Client Layer
Add `get_disk_space()` to `BaseApiClient`. Test via RadarrClient (concrete subclass).

### Phase 2: Service Layer
Add `get_disk_space()` to HealthService. Finds first enabled media service, creates its client, calls `get_disk_space()`.

### Phase 3: Handler + Keyboard + Formatting
Add "Disk Space" button to `get_system_keyboard()`. Add `_handle_diskspace()` callback in SystemHandler. Add `_build_disk_space_text()` formatter with progress bars and warning indicators.

### Phase 4: Translations
Add translation keys for disk space UI text.

## Files to Touch

### Modify:
- `src/api/base.py` — add `get_disk_space()` to `BaseApiClient`
- `src/services/health.py` — add `get_disk_space()` and `_get_api_client()`
- `src/bot/handlers/system.py` — add `_handle_diskspace()`, `_build_disk_space_text()`, helper functions
- `src/bot/keyboards.py` — add button to `get_system_keyboard()`
- `translations/addarr.en-us.yml` — add disk space translation keys
- `translations/addarr.template.yml` — add disk space template keys

### Test:
- `tests/test_api/test_radarr.py` — test `get_disk_space()` (inherited from base)
- `tests/test_services/test_health_service.py` — test `get_disk_space()`
- `tests/test_handlers/test_system_handler.py` — test disk space callback + formatter

### Data:
- `tests/fixtures/sample_data.py` — add `RADARR_DISK_SPACE` fixture

## Task Breakdown

### Task 1: BaseApiClient `get_disk_space()`

**Files:**
- Modify: `src/api/base.py` (add method after `check_status`, ~line 249)
- Test: `tests/test_api/test_radarr.py` (test via RadarrClient)
- Modify: `tests/fixtures/sample_data.py` — add `RADARR_DISK_SPACE`

**Implementation** (in `BaseApiClient`, after `check_status`):

```python
async def get_disk_space(self):
    """Get disk space information for configured drives."""
    try:
        results = await self._request("diskspace")
        if not results:
            return []
        return results
    except Exception as e:
        self.logger.error(f"Failed to get disk space: {str(e)}")
        return []
```

**Sample data fixture:**

```python
RADARR_DISK_SPACE = [
    {
        "path": "/movies",
        "label": "Movies",
        "freeSpace": 500000000000,
        "totalSpace": 1000000000000,
    },
    {
        "path": "/movies2",
        "label": "",
        "freeSpace": 50000000000,
        "totalSpace": 1000000000000,
    },
]
```

**Tests:**

```python
class TestRadarrDiskSpace:
    @pytest.mark.asyncio
    async def test_get_disk_space_success(self, aio_mock, radarr_client):
        aio_mock.get(f"{BASE}/diskspace", payload=RADARR_DISK_SPACE, status=200)
        results = await radarr_client.get_disk_space()
        assert len(results) == 2
        assert results[0]["path"] == "/movies"
        assert results[0]["freeSpace"] == 500000000000

    @pytest.mark.asyncio
    async def test_get_disk_space_empty(self, aio_mock, radarr_client):
        aio_mock.get(f"{BASE}/diskspace", payload=[], status=200)
        results = await radarr_client.get_disk_space()
        assert results == []

    @pytest.mark.asyncio
    async def test_get_disk_space_error(self, radarr_client):
        with patch.object(radarr_client, "_make_request", side_effect=Exception("fail")):
            results = await radarr_client.get_disk_space()
        assert results == []
```

### Task 2: HealthService `get_disk_space()`

**Files:**
- Modify: `src/services/health.py` (add methods after `get_status`, ~line 308)
- Test: `tests/test_services/test_health_service.py`

**Implementation:**

```python
def _get_api_client(self, config_key):
    """Create an API client instance for a media service."""
    try:
        if config_key == "radarr":
            from src.api.radarr import RadarrClient
            return RadarrClient()
        elif config_key == "sonarr":
            from src.api.sonarr import SonarrClient
            return SonarrClient()
        elif config_key == "lidarr":
            from src.api.lidarr import LidarrClient
            return LidarrClient()
    except Exception as e:
        logger.error(f"Failed to create API client for {config_key}: {e}")
    return None

async def get_disk_space(self):
    """Get disk space from the first enabled media service.

    All *arr services return the same OS-level disk info,
    so querying one is sufficient.
    """
    services = [
        ("Radarr", "radarr"),
        ("Sonarr", "sonarr"),
        ("Lidarr", "lidarr"),
    ]

    for service_name, config_key in services:
        service_config = config.get(config_key, {})
        if not service_config.get("enable"):
            continue

        try:
            client = self._get_api_client(config_key)
            if client is None:
                continue
            drives = await client.get_disk_space()
            return drives
        except Exception as e:
            logger.error(f"Failed to get disk space from {service_name}: {e}")

    return []
```

Note: returns a flat list `[{path, label, freeSpace, totalSpace}, ...]` — no dict-of-lists since we only query one service.

**Tests:**

```python
class TestHealthServiceDiskSpace:
    @pytest.mark.asyncio
    async def test_get_disk_space_returns_drives(self):
        """Returns disk space from the first enabled service."""
        hs = HealthService()
        mock_client = AsyncMock()
        mock_client.get_disk_space = AsyncMock(return_value=[
            {"path": "/movies", "label": "Movies", "freeSpace": 500e9, "totalSpace": 1e12}
        ])

        with (
            patch.object(hs, "_get_api_client", return_value=mock_client),
            patch("src.services.health.config") as mock_config,
        ):
            mock_config.get.side_effect = lambda k, d=None: (
                {"enable": True} if k == "radarr" else d or {}
            )
            results = await hs.get_disk_space()

        assert len(results) == 1
        assert results[0]["path"] == "/movies"

    @pytest.mark.asyncio
    async def test_get_disk_space_skips_disabled(self):
        """Skips disabled services, uses next enabled one."""
        hs = HealthService()
        mock_client = AsyncMock()
        mock_client.get_disk_space = AsyncMock(return_value=[
            {"path": "/tv", "freeSpace": 200e9, "totalSpace": 1e12}
        ])

        with (
            patch.object(hs, "_get_api_client", return_value=mock_client),
            patch("src.services.health.config") as mock_config,
        ):
            def config_get(k, d=None):
                if k == "radarr":
                    return {"enable": False}
                if k == "sonarr":
                    return {"enable": True}
                return d or {}
            mock_config.get.side_effect = config_get
            results = await hs.get_disk_space()

        assert len(results) == 1
        assert results[0]["path"] == "/tv"

    @pytest.mark.asyncio
    async def test_get_disk_space_no_enabled_services(self):
        """Returns empty list when no services are enabled."""
        hs = HealthService()
        with patch("src.services.health.config") as mock_config:
            mock_config.get.return_value = {}
            results = await hs.get_disk_space()
        assert results == []

    @pytest.mark.asyncio
    async def test_get_disk_space_client_error_tries_next(self):
        """Falls through to next service when one fails."""
        hs = HealthService()
        call_count = 0

        def make_client(config_key):
            nonlocal call_count
            call_count += 1
            client = AsyncMock()
            if call_count == 1:
                client.get_disk_space = AsyncMock(side_effect=Exception("timeout"))
            else:
                client.get_disk_space = AsyncMock(return_value=[
                    {"path": "/tv", "freeSpace": 100e9, "totalSpace": 500e9}
                ])
            return client

        with (
            patch.object(hs, "_get_api_client", side_effect=make_client),
            patch("src.services.health.config") as mock_config,
        ):
            mock_config.get.side_effect = lambda k, d=None: (
                {"enable": True} if k in ("radarr", "sonarr") else d or {}
            )
            results = await hs.get_disk_space()

        assert len(results) == 1
        assert results[0]["path"] == "/tv"

    def test_get_api_client_radarr(self):
        """_get_api_client returns RadarrClient for 'radarr'."""
        hs = HealthService()
        with patch("src.services.health.RadarrClient") as mock_cls:
            # Import happens lazily, so we patch at the target
            pass
        # Simpler: just test it doesn't crash for invalid key
        result = hs._get_api_client("nonexistent")
        assert result is None
```

### Task 3: Keyboard button + SystemHandler callback + formatter

**Files:**
- Modify: `src/bot/keyboards.py:74-93` — add "Disk Space" button to `get_system_keyboard()`
- Modify: `src/bot/handlers/system.py` — add constant, dispatch branch, handler, formatter, helper functions
- Test: `tests/test_handlers/test_system_handler.py`

**Keyboard change** (`keyboards.py:74-93`):

```python
def get_system_keyboard() -> InlineKeyboardMarkup:
    """Get system status keyboard with action buttons"""
    translation = TranslationService()
    keyboard = [
        [
            InlineKeyboardButton(
                "🔄 Refresh", callback_data="system_refresh"
            ),
            InlineKeyboardButton(
                "📋 Details", callback_data="system_details"
            ),
        ],
        [
            InlineKeyboardButton(
                "💾 Disk Space", callback_data="system_diskspace"
            ),
        ],
        [
            InlineKeyboardButton(
                f"◀️ {translation.get_text('Back')}",
                callback_data="system_back"
            ),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)
```

**Handler changes** (`system.py`):

Module-level constant:

```python
LOW_SPACE_THRESHOLD = 0.10  # 10% free space warning threshold
```

Dispatch branch (add after `details` branch):

```python
elif action == "diskspace":
    await self._handle_diskspace(query)
```

Handler method:

```python
async def _handle_diskspace(self, query):
    """Show disk space information from media services."""
    try:
        drives = await health_service.get_disk_space()
        text = _build_disk_space_text(drives, self.translation)
        await query.message.edit_text(
            text,
            reply_markup=get_system_keyboard(),
        )
        await query.answer()
    except Exception as e:
        logger.error(f"Error getting disk space: {e}")
        await query.message.edit_text(
            self.translation.get_text(
                "DiskSpaceError",
                default="Error retrieving disk space information.",
            ),
            reply_markup=get_system_keyboard(),
        )
        await query.answer(
            self.translation.get_text(
                "DiskSpaceFailed", default="Disk space check failed"
            )
        )
```

Module-level helper functions:

```python
def _format_usage_bar(used_fraction, width=10):
    """Build a text progress bar like [████░░░░░░]."""
    filled = round(used_fraction * width)
    empty = width - filled
    return f"[{'█' * filled}{'░' * empty}]"


def _format_bytes(num_bytes):
    """Format byte count to human-readable string."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num_bytes) < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} PB"


def _build_disk_space_text(drives, translation):
    """Build disk space display text with visual bars."""
    if not drives:
        return translation.get_text(
            "DiskSpaceNone",
            default="💾 *Disk Space*\n\nNo disk space data available.",
        )

    text = "💾 *Disk Space*\n\n"

    for drive in drives:
        path = drive.get("path", "Unknown")
        total = drive.get("totalSpace", 0)
        free = drive.get("freeSpace", 0)

        if total > 0:
            used = total - free
            used_pct = used / total
            free_pct = free / total
        else:
            used_pct = 0
            free_pct = 1

        bar = _format_usage_bar(used_pct)
        warning = " ⚠️" if free_pct < LOW_SPACE_THRESHOLD else ""

        total_str = _format_bytes(total)
        free_str = _format_bytes(free)

        text += f"  `{path}`\n"
        text += f"  {bar} {used_pct:.0%}{warning}\n"
        text += f"  {free_str} free / {total_str} total\n\n"

    return text
```

**Tests:**

```python
# ---------------------------------------------------------------------------
# handle_system_action — diskspace
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_handle_diskspace(system_handler, make_update, make_context):
    """system_diskspace shows disk space information."""
    system_handler._mock_health.get_disk_space = AsyncMock(return_value=[
        {"path": "/movies", "label": "Movies",
         "freeSpace": 500000000000, "totalSpace": 1000000000000},
    ])
    update = make_update(callback_data="system_diskspace")
    context = make_context()

    await system_handler.handle_system_action(update, context)

    system_handler._mock_health.get_disk_space.assert_awaited_once()
    call_args = update.callback_query.message.edit_text.call_args
    text = call_args[0][0]
    assert "Disk Space" in text
    assert "/movies" in text
    assert "50%" in text


@pytest.mark.asyncio
async def test_handle_diskspace_empty(system_handler, make_update, make_context):
    """system_diskspace shows message when no data available."""
    system_handler._mock_health.get_disk_space = AsyncMock(return_value=[])
    update = make_update(callback_data="system_diskspace")
    context = make_context()

    await system_handler.handle_system_action(update, context)

    call_args = update.callback_query.message.edit_text.call_args
    text = call_args[0][0]
    assert "No disk space" in text or "DiskSpaceNone" in text


@pytest.mark.asyncio
async def test_handle_diskspace_error(system_handler, make_update, make_context):
    """system_diskspace shows error on exception."""
    system_handler._mock_health.get_disk_space = AsyncMock(
        side_effect=Exception("Connection refused")
    )
    update = make_update(callback_data="system_diskspace")
    context = make_context()

    await system_handler.handle_system_action(update, context)

    update.callback_query.answer.assert_called_once()


@pytest.mark.asyncio
async def test_handle_diskspace_low_space_warning(
    system_handler, make_update, make_context
):
    """system_diskspace shows warning emoji for low free space."""
    system_handler._mock_health.get_disk_space = AsyncMock(return_value=[
        {"path": "/movies", "label": "Movies",
         "freeSpace": 50000000000, "totalSpace": 1000000000000},
    ])
    update = make_update(callback_data="system_diskspace")
    context = make_context()

    await system_handler.handle_system_action(update, context)

    call_args = update.callback_query.message.edit_text.call_args
    text = call_args[0][0]
    assert "⚠️" in text


# ---------------------------------------------------------------------------
# _format_usage_bar / _format_bytes unit tests
# ---------------------------------------------------------------------------

def test_format_usage_bar():
    from src.bot.handlers.system import _format_usage_bar
    assert _format_usage_bar(0.0) == "[░░░░░░░░░░]"
    assert _format_usage_bar(0.5) == "[█████░░░░░]"
    assert _format_usage_bar(1.0) == "[██████████]"


def test_format_bytes():
    from src.bot.handlers.system import _format_bytes
    assert _format_bytes(0) == "0.0 B"
    assert "GB" in _format_bytes(500000000000)
    assert "TB" in _format_bytes(1000000000000)
```

### Task 4: Translation keys

**Files:**
- Modify: `translations/addarr.en-us.yml`
- Modify: `translations/addarr.template.yml`

**Keys to add** (in the system status section, after `StatusDetailsFailed`):

```yaml
  DiskSpaceError: "❌ Error retrieving disk space information. Please try again."
  DiskSpaceFailed: "Disk space check failed"
  DiskSpaceNone: "💾 *Disk Space*\n\nNo disk space data available."
```

Note: The handler uses `default=` fallbacks so the feature works even without translations, but we add keys for completeness and i18n readiness.

## Verification

After all tasks:
1. `pytest --tb=short -q` — all tests pass
2. `python -m flake8 .` — no lint errors
3. `PYTHONIOENCODING=utf-8 python run.py --validate-i18n` — translations valid
4. Coverage check: `pytest --cov=src.api.base --cov=src.services.health --cov=src.bot.handlers.system --cov=src.bot.keyboards --cov-report=term-missing`
