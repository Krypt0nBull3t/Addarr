"""
Filename: rate_limit.py
Author: Addarr Contributors
Created Date: 2026-03-03
Description: Rate limiting service and decorator.

This module provides per-user, per-category rate limiting for bot handlers.
Uses an in-memory sliding window algorithm to track request timestamps.
"""

import time
from functools import wraps
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from src.config.settings import config
from src.services.translation import TranslationService
from src.utils.logger import get_logger

logger = get_logger("addarr.ratelimit")

# Default limits per category: (max_requests, window_seconds)
DEFAULT_LIMITS = {
    "search": (10, 60),
    "modify": (5, 60),
    "auth": (3, 300),
}
DEFAULT_FALLBACK = (10, 60)


class RateLimitService:
    """Per-user rate limiting using in-memory sliding window."""

    _instance: Optional["RateLimitService"] = None
    _records: dict[tuple[int, str], list[float]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RateLimitService, cls).__new__(cls)
        return cls._instance

    @property
    def is_enabled(self):
        """Check if rate limiting is enabled in config."""
        return config.get("rateLimit", {}).get("enable", False)

    def check(self, user_id, category):
        """Check if a request is allowed under the rate limit.

        Args:
            user_id: Telegram user ID.
            category: Rate limit category (search, modify, auth).

        Returns:
            Tuple of (allowed: bool, retry_after: int).
            retry_after is 0 when allowed, otherwise seconds to wait.
        """
        max_requests, window_seconds = self._get_limit(category)
        now = time.time()
        cutoff = now - window_seconds

        # Initialize nested dicts
        if user_id not in self._records:
            self._records[user_id] = {}
        if category not in self._records[user_id]:
            self._records[user_id][category] = []

        # Prune expired timestamps
        self._records[user_id][category] = [
            ts for ts in self._records[user_id][category] if ts > cutoff
        ]

        timestamps = self._records[user_id][category]

        if len(timestamps) >= max_requests:
            # Blocked — calculate retry_after from oldest timestamp in window
            oldest = min(timestamps)
            retry_after = int(oldest + window_seconds - now) + 1
            return (False, max(retry_after, 1))

        # Allowed — record this request
        timestamps.append(now)
        return (True, 0)

    def _get_limit(self, category):
        """Get the rate limit for a category.

        Reads from config, falls back to hardcoded defaults.

        Returns:
            Tuple of (max_requests, window_seconds).
        """
        rate_config = config.get("rateLimit", {})
        limits = rate_config.get("limits", {})
        cat_config = limits.get(category, {})

        default_max, default_window = DEFAULT_LIMITS.get(
            category, DEFAULT_FALLBACK
        )

        max_req = cat_config.get("maxRequests", default_max)
        window = cat_config.get("windowSeconds", default_window)
        return (max_req, window)

    @classmethod
    def reset(cls):
        """Clear all rate limit records."""
        cls._records = {}


async def enforce_rate_limit(update: Update, category: str) -> bool:
    """Count one call in the category; reply and return False when over the limit.

    Args:
        update: The update that triggered the call.
        category: Rate limit category (search, modify, auth).
    """
    service = RateLimitService()

    # Auth attempts are always limited: they guard the bot password
    if not service.is_enabled and category != "auth":
        return True

    if not update.effective_user:
        return False

    allowed, retry_after = service.check(update.effective_user.id, category)
    if allowed:
        return True

    msg = update.effective_message
    if msg is None:  # pragma: no cover
        return False
    await msg.reply_text(
        TranslationService().get_text(
            "RateLimitExceeded",
            default=(
                f"Slow down! Please wait {retry_after} "
                "seconds before trying again."
            ),
            seconds=retry_after,
        )
    )
    return False


def rate_limit(category):
    """Decorator to enforce rate limiting on handler methods.

    Args:
        category: Rate limit category (search, modify, auth).
    """
    def decorator(func):
        @wraps(func)
        async def wrapped(
            self, update: Update,
            context: ContextTypes.DEFAULT_TYPE,
            *args, **kwargs
        ):
            if not await enforce_rate_limit(update, category):
                return
            return await func(self, update, context, *args, **kwargs)
        return wrapped
    return decorator
