"""Small reliability primitives for external WealthPlan services."""

from __future__ import annotations

from collections.abc import Callable, Hashable
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import RLock
from time import monotonic
from typing import Generic, TypeVar


T = TypeVar("T")
K = TypeVar("K", bound=Hashable)


@dataclass(frozen=True, slots=True)
class CacheRecord(Generic[T]):
    """A cached value together with its human-readable storage time."""

    value: T
    stored_at: datetime
    stored_monotonic: float

    @property
    def stored_at_iso(self) -> str:
        return self.stored_at.isoformat()


class TimestampedTTLCache(Generic[K, T]):
    """In-process TTL cache that retains expired entries for safe fallback."""

    def __init__(self, ttl_seconds: float) -> None:
        self.ttl_seconds = max(0.0, ttl_seconds)
        self._records: dict[K, CacheRecord[T]] = {}
        self._lock = RLock()

    def set(self, key: K, value: T) -> CacheRecord[T]:
        record = CacheRecord(
            value=value,
            stored_at=datetime.now(UTC),
            stored_monotonic=monotonic(),
        )
        with self._lock:
            self._records[key] = record
        return record

    def get_fresh(self, key: K) -> CacheRecord[T] | None:
        with self._lock:
            record = self._records.get(key)
        if record is None:
            return None
        if monotonic() - record.stored_monotonic >= self.ttl_seconds:
            return None
        return record

    def get_stale(self, key: K) -> CacheRecord[T] | None:
        """Return an entry even after expiry for an explicitly labeled fallback."""

        with self._lock:
            return self._records.get(key)


def retry_call(
    operation: Callable[[], T],
    *,
    attempts: int = 2,
    is_retryable: Callable[[Exception], bool] | None = None,
) -> tuple[T, int]:
    """Run an operation with a bounded retry and return attempts consumed."""

    maximum = max(1, attempts)
    predicate = is_retryable or (lambda _exc: True)
    for attempt in range(1, maximum + 1):
        try:
            return operation(), attempt
        except Exception as exc:
            if attempt >= maximum or not predicate(exc):
                raise
    raise AssertionError("retry loop completed without returning or raising")
