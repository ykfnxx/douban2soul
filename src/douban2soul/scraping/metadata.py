"""
Field-level metadata scraper (V1).

Fetches movie metadata from a single source (wmdb) and returns a
per-field result structure with provenance tracking.
"""

import logging
from typing import Optional

from douban2soul.scraping.adapters import get_adapter
from douban2soul.scraping.adapters.base import BaseMetadataAdapter
from douban2soul.scraping.cache import MetadataCache

logger = logging.getLogger(__name__)

# Fields we care about and whether they are required for analysis.
FIELD_CONFIG: dict[str, bool] = {
    "genre": True,
    "director": True,
    "country": True,
    "cast": False,
    "duration": False,
    "douban_rating": False,
    "rating_count": False,
}


class FieldLevelScraper:
    """
    Scrape metadata and return a field-level result for each movie.

    ``fetch_success`` indicates whether the HTTP request succeeded and
    returned parseable data.  Individual fields may still be missing
    even when the fetch succeeds; ``core_fields_present`` counts how
    many of the required fields were found.

    Parameters
    ----------
    adapter_name:
        Registered adapter name (default ``"wmdb"``).
    cache:
        An optional pre-configured ``MetadataCache``.
    """

    def __init__(
        self,
        adapter_name: str = "wmdb",
        cache: Optional[MetadataCache] = None,
    ) -> None:
        self._adapter: BaseMetadataAdapter = get_adapter(adapter_name)
        self._cache: MetadataCache = cache if cache is not None else MetadataCache()

    @property
    def cache(self) -> MetadataCache:
        return self._cache

    def scrape(self, movie_id: str) -> dict:
        """
        Scrape metadata for *movie_id*.

        Returns a dict with keys:
            movie_id, fetch_success, fields, core_fields_present,
            all_fields_present, raw_data, error (on failure).
        """
        cached = self._cache.get(movie_id)
        if cached is not None:
            return self._result_from_raw(movie_id, cached, source="cache")

        try:
            raw = self._adapter.fetch(movie_id)
        except Exception as exc:
            logger.error("Unexpected error scraping %s: %s", movie_id, exc)
            return self._error_result(movie_id, str(exc))

        if raw is None:
            return self._error_result(movie_id, "empty_response")

        self._cache.set(movie_id, raw)
        return self._result_from_raw(movie_id, raw, source=self._adapter.name)

    # ------------------------------------------------------------------
    # Result formatting
    # ------------------------------------------------------------------

    def _result_from_raw(self, movie_id: str, raw: dict, *, source: str) -> dict:
        fields: dict[str, dict] = {}
        core_present = 0
        all_present = 0

        for field, required in FIELD_CONFIG.items():
            value = raw.get(field)
            present = _has_value(value)
            fields[field] = {
                "value": value if present else None,
                "present": present,
                "source": source if present else None,
            }
            if present:
                all_present += 1
                if required:
                    core_present += 1

        return {
            "movie_id": movie_id,
            "fetch_success": True,
            "fields": fields,
            "core_fields_present": core_present,
            "all_fields_present": all_present,
            "raw_data": raw,
        }

    @staticmethod
    def _error_result(movie_id: str, error: str) -> dict:
        fields = {
            f: {"value": None, "present": False, "source": None}
            for f in FIELD_CONFIG
        }
        return {
            "movie_id": movie_id,
            "fetch_success": False,
            "fields": fields,
            "core_fields_present": 0,
            "all_fields_present": 0,
            "raw_data": None,
            "error": error,
        }


def _has_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, (str, list)) and len(value) == 0:
        return False
    return True
