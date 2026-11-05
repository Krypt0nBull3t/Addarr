"""
Tests for src/services/rate_limit.py - RateLimitService.

RateLimitService is a singleton that tracks per-user request timestamps
using an in-memory sliding window. It enforces configurable rate limits
per command category (search, modify, auth).
"""

from unittest.mock import patch


# ---------------------------------------------------------------------------
# Singleton pattern
# ---------------------------------------------------------------------------


def test_singleton_pattern():
    """Two instantiations return the same object."""
    from src.services.rate_limit import RateLimitService

    a = RateLimitService()
    b = RateLimitService()
    assert a is b


def test_reset_clears_all():
    """reset() empties all records."""
    from src.services.rate_limit import RateLimitService

    service = RateLimitService()
    service.check(12345, "search")
    service.reset()
    assert service._records == {}


# ---------------------------------------------------------------------------
# check() — core sliding window logic
# ---------------------------------------------------------------------------


def test_check_allows_first_request():
    """First request for a user/category returns (True, 0)."""
    from src.services.rate_limit import RateLimitService

    service = RateLimitService()
    allowed, retry_after = service.check(12345, "search")
    assert allowed is True
    assert retry_after == 0


def test_check_allows_under_limit():
    """Multiple requests under limit all return (True, 0)."""
    from src.services.rate_limit import RateLimitService

    service = RateLimitService()
    # Default search limit is 10/60s
    for _ in range(9):
        allowed, retry_after = service.check(12345, "search")
        assert allowed is True
        assert retry_after == 0


def test_check_blocks_over_limit():
    """Requests exceeding limit return (False, retry_seconds > 0)."""
    from src.services.rate_limit import RateLimitService

    service = RateLimitService()
    # Default search limit is 10/60s — make 10 allowed, 11th blocked
    for _ in range(10):
        allowed, _ = service.check(12345, "search")
        assert allowed is True

    allowed, retry_after = service.check(12345, "search")
    assert allowed is False
    assert retry_after > 0


@patch("src.services.rate_limit.time")
def test_check_allows_after_window_expires(mock_time):
    """After window passes, requests are allowed again."""
    from src.services.rate_limit import RateLimitService

    service = RateLimitService()

    # Fill up limit at t=1000
    mock_time.time.return_value = 1000.0
    for _ in range(10):
        service.check(12345, "search")

    # Blocked at t=1000
    allowed, _ = service.check(12345, "search")
    assert allowed is False

    # Window expires at t=1061 (60s window + 1)
    mock_time.time.return_value = 1061.0
    allowed, retry_after = service.check(12345, "search")
    assert allowed is True
    assert retry_after == 0


@patch("src.services.rate_limit.time")
def test_check_prunes_expired_timestamps(mock_time):
    """Old timestamps are removed when check() runs."""
    from src.services.rate_limit import RateLimitService

    service = RateLimitService()

    # Add timestamps at t=100
    mock_time.time.return_value = 100.0
    service.check(12345, "search")

    # Move far into the future
    mock_time.time.return_value = 200.0
    service.check(12345, "search")

    # Only the recent timestamp should remain
    timestamps = service._records[12345]["search"]
    assert len(timestamps) == 1
    assert timestamps[0] == 200.0


# ---------------------------------------------------------------------------
# Isolation between categories and users
# ---------------------------------------------------------------------------


def test_different_categories_independent():
    """Hitting search limit doesn't affect modify limit."""
    from src.services.rate_limit import RateLimitService

    service = RateLimitService()

    # Exhaust search limit (10 requests)
    for _ in range(10):
        service.check(12345, "search")

    # search should be blocked
    allowed, _ = service.check(12345, "search")
    assert allowed is False

    # modify should still work
    allowed, retry_after = service.check(12345, "modify")
    assert allowed is True
    assert retry_after == 0


def test_different_users_independent():
    """User A's limits don't affect User B."""
    from src.services.rate_limit import RateLimitService

    service = RateLimitService()

    # Exhaust search limit for user 111
    for _ in range(10):
        service.check(111, "search")

    allowed, _ = service.check(111, "search")
    assert allowed is False

    # User 222 should be unaffected
    allowed, retry_after = service.check(222, "search")
    assert allowed is True
    assert retry_after == 0


# ---------------------------------------------------------------------------
# _get_limit() — defaults and config reading
# ---------------------------------------------------------------------------


def test_get_limit_defaults():
    """Unknown category returns the default fallback (10, 60)."""
    from src.services.rate_limit import RateLimitService

    service = RateLimitService()
    max_req, window = service._get_limit("unknown_category")
    assert max_req == 10
    assert window == 60


def test_get_limit_known_category_defaults():
    """Known categories return their specific defaults."""
    from src.services.rate_limit import RateLimitService

    service = RateLimitService()

    max_req, window = service._get_limit("search")
    assert max_req == 10
    assert window == 60

    max_req, window = service._get_limit("modify")
    assert max_req == 5
    assert window == 60

    max_req, window = service._get_limit("auth")
    assert max_req == 3
    assert window == 300


def test_get_limit_from_config():
    """Config values override defaults."""
    from src.services.rate_limit import RateLimitService

    service = RateLimitService()

    # Patch config to return custom limits
    custom_config = {
        "enable": True,
        "limits": {
            "search": {"maxRequests": 20, "windowSeconds": 120},
        },
    }
    with patch("src.services.rate_limit.config") as mock_cfg:
        mock_cfg.get.return_value = custom_config
        max_req, window = service._get_limit("search")

    assert max_req == 20
    assert window == 120


def test_get_limit_missing_category_uses_default():
    """Category not in config falls back to hardcoded defaults."""
    from src.services.rate_limit import RateLimitService

    service = RateLimitService()

    custom_config = {
        "enable": True,
        "limits": {},  # no categories configured
    }
    with patch("src.services.rate_limit.config") as mock_cfg:
        mock_cfg.get.return_value = custom_config
        max_req, window = service._get_limit("search")

    assert max_req == 10
    assert window == 60


# ---------------------------------------------------------------------------
# is_enabled property
# ---------------------------------------------------------------------------


def test_is_enabled_true():
    """Returns True when config rateLimit.enable is true."""
    from src.services.rate_limit import RateLimitService

    service = RateLimitService()
    with patch("src.services.rate_limit.config") as mock_cfg:
        mock_cfg.get.return_value = {"enable": True}
        assert service.is_enabled is True


def test_is_enabled_false():
    """Returns False when config rateLimit.enable is false."""
    from src.services.rate_limit import RateLimitService

    service = RateLimitService()
    with patch("src.services.rate_limit.config") as mock_cfg:
        mock_cfg.get.return_value = {"enable": False}
        assert service.is_enabled is False


def test_is_enabled_missing_config():
    """Returns False when rateLimit section is missing from config."""
    from src.services.rate_limit import RateLimitService

    service = RateLimitService()
    with patch("src.services.rate_limit.config") as mock_cfg:
        mock_cfg.get.return_value = {}
        assert service.is_enabled is False


# ---------------------------------------------------------------------------
# check() does not count blocked requests
# ---------------------------------------------------------------------------


@patch("src.services.rate_limit.time")
def test_check_does_not_count_blocked_requests(mock_time):
    """Blocked requests should not add timestamps (don't penalize further)."""
    from src.services.rate_limit import RateLimitService

    service = RateLimitService()
    mock_time.time.return_value = 1000.0

    # Fill up limit (10 allowed)
    for _ in range(10):
        service.check(12345, "search")

    timestamps_before = len(service._records[12345]["search"])

    # These should be blocked and NOT add timestamps
    for _ in range(5):
        allowed, _ = service.check(12345, "search")
        assert allowed is False

    timestamps_after = len(service._records[12345]["search"])
    assert timestamps_after == timestamps_before
