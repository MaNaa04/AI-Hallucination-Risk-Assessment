"""
Cache utility for memoizing external API calls.
"""

from typing import Any, Coroutine, Callable
from cachetools import TTLCache
from app.core.logging import get_logger

logger = get_logger(__name__)

# Main in-memory cache: 1000 items max, 1 hour (3600 seconds) TTL
api_cache = TTLCache(maxsize=1000, ttl=3600)


def get_cached(key: str) -> Any | None:
    """Retrieve value from cache."""
    return api_cache.get(key)


def set_cached(key: str, value: Any) -> None:
    """Set value in cache."""
    api_cache[key] = value
