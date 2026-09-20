"""Short-lived server-side storage for authoritative assessment snapshots."""

from __future__ import annotations

import copy
import secrets
import time
from collections import OrderedDict
from threading import RLock
from typing import Any


class AssessmentStore:
    """Bounded, process-local assessment store with opaque identifiers."""

    def __init__(self, *, ttl_seconds: int = 1800, max_entries: int = 256) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._items: OrderedDict[str, tuple[float, dict[str, Any]]] = OrderedDict()
        self._lock = RLock()

    def _prune(self, now: float) -> None:
        expired = [key for key, (expires, _) in self._items.items() if expires <= now]
        for key in expired:
            self._items.pop(key, None)
        while len(self._items) >= self.max_entries:
            self._items.popitem(last=False)

    def put(self, assessment: dict[str, Any]) -> str:
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            assessment_id = secrets.token_urlsafe(24)
            self._items[assessment_id] = (
                now + self.ttl_seconds,
                copy.deepcopy(assessment),
            )
            return assessment_id

    def get(self, assessment_id: str) -> dict[str, Any] | None:
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            item = self._items.get(assessment_id)
            if item is None:
                return None
            expires, assessment = item
            self._items.move_to_end(assessment_id)
            self._items[assessment_id] = (expires, assessment)
            return copy.deepcopy(assessment)


assessment_store = AssessmentStore()
