"""Single-file JSON cache for movie metadata."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_PATH = "cache/metadata_cache.json"
_DEFAULT_TTL_DAYS = 90
_FLUSH_INTERVAL = 10  # flush to disk every N writes


class MetadataCache:
    """
    In-memory metadata cache backed by a single JSON file.

    The full cache is loaded on construction and flushed to disk
    periodically (every *flush_interval* writes) and on ``flush()``.
    Entries older than *ttl_days* are silently evicted on read.
    """

    def __init__(
        self,
        path: str = _DEFAULT_PATH,
        ttl_days: int = _DEFAULT_TTL_DAYS,
    ) -> None:
        self._path = Path(path)
        self._ttl = timedelta(days=ttl_days)
        self._dirty = 0
        self._data: dict[str, dict] = self._load()

    def get(self, movie_id: str) -> Optional[dict]:
        entry = self._data.get(movie_id)
        if entry is None:
            return None

        cached_at = entry.get("_cached_at", "")
        try:
            if datetime.fromisoformat(cached_at) + self._ttl < datetime.now():
                del self._data[movie_id]
                return None
        except (ValueError, TypeError):
            del self._data[movie_id]
            return None

        return entry

    def set(self, movie_id: str, data: dict) -> None:
        entry = {**data, "_cached_at": datetime.now().isoformat()}
        self._data[movie_id] = entry
        self._dirty += 1
        if self._dirty >= _FLUSH_INTERVAL:
            self.flush()

    def flush(self) -> None:
        if self._dirty == 0:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as fh:
            json.dump(self._data, fh, ensure_ascii=False, indent=2)
        self._dirty = 0

    def __len__(self) -> int:
        return len(self._data)

    # ------------------------------------------------------------------

    def _load(self) -> dict[str, dict]:
        if not self._path.exists():
            return {}
        try:
            with open(self._path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load cache from %s: %s", self._path, exc)
            return {}
