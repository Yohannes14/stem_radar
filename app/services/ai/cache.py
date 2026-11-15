"""High-performance in-memory cache for reusable AI intelligence results."""

import hashlib
import logging
import time
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class AICache:
    """In-memory cache with TTL and automatic expiration for LLM outputs."""

    def __init__(self, default_ttl_seconds: int = 86400, max_entries: int = 2000) -> None:
        self.default_ttl = default_ttl_seconds
        self.max_entries = max_entries
        self._store: Dict[str, Tuple[float, Any]] = {}
        self.hits: int = 0
        self.misses: int = 0

    def _generate_key(self, task_type: str, identifier: str, mode: str = "default") -> str:
        """Create a deterministic hash key for a task and input content."""
        payload = f"{task_type}:{identifier}:{mode}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def get(self, task_type: str, identifier: str, mode: str = "default") -> Optional[Any]:
        """Retrieve cached value if present and unexpired."""
        key = self._generate_key(task_type, identifier, mode)
        entry = self._store.get(key)
        if not entry:
            self.misses += 1
            return None

        expires_at, value = entry
        if time.time() > expires_at:
            # Expired
            self._store.pop(key, None)
            self.misses += 1
            return None

        self.hits += 1
        logger.debug("AI Cache HIT for %s:%s (mode=%s)", task_type, identifier[:30], mode)
        return value

    def set(
        self,
        task_type: str,
        identifier: str,
        value: Any,
        mode: str = "default",
        ttl: Optional[int] = None,
    ) -> None:
        """Store value with expiration."""
        # Evict oldest entries if capacity exceeded
        if len(self._store) >= self.max_entries:
            oldest_key = min(self._store.keys(), key=lambda k: self._store[k][0])
            self._store.pop(oldest_key, None)

        expires_at = time.time() + (ttl if ttl is not None else self.default_ttl)
        key = self._generate_key(task_type, identifier, mode)
        self._store[key] = (expires_at, value)

    def clear(self) -> None:
        """Clear cache entries and hit/miss counters."""
        self._store.clear()
        self.hits = 0
        self.misses = 0


ai_cache = AICache()
