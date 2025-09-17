"""Simple in-memory TTL cache utilities for Spotify metadata caching."""

from __future__ import annotations

import time
from collections import OrderedDict
from threading import RLock
from typing import Any, Hashable, Tuple

MISSING = object()


class TTLCache:
    """Thread-safe TTL cache with LRU eviction."""

    def __init__(self, maxsize: int = 128, ttl: float = 300.0) -> None:
        if maxsize <= 0:
            raise ValueError("maxsize must be positive")
        if ttl <= 0:
            raise ValueError("ttl must be positive")
        self.maxsize = maxsize
        self.ttl = ttl
        self._data: "OrderedDict[Hashable, Tuple[Any, float]]" = OrderedDict()
        self._lock = RLock()

    def _evict_expired(self) -> None:
        now = time.time()
        expired_keys = [key for key, (_, expiry) in self._data.items() if expiry <= now]
        for key in expired_keys:
            self._data.pop(key, None)

    def get(self, key: Hashable, default: Any = MISSING) -> Any:
        with self._lock:
            self._evict_expired()
            entry = self._data.get(key)
            if not entry:
                return default
            value, expiry = entry
            if expiry <= time.time():
                self._data.pop(key, None)
                return default
            self._data.move_to_end(key)
            return value

    def set(self, key: Hashable, value: Any) -> None:
        with self._lock:
            expiry = time.time() + self.ttl
            if key in self._data:
                self._data.move_to_end(key)
            self._data[key] = (value, expiry)
            while len(self._data) > self.maxsize:
                self._data.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def __contains__(self, key: Hashable) -> bool:  # pragma: no cover - convenience helper
        with self._lock:
            self._evict_expired()
            return key in self._data


__all__ = ["TTLCache", "MISSING"]
