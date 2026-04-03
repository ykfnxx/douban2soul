"""Fallback adapter that chains multiple sources."""

import logging
from typing import Optional

from douban2soul.scraping.adapters import register, get_adapter
from douban2soul.scraping.adapters.base import BaseMetadataAdapter

logger = logging.getLogger(__name__)

# Fields that, when missing from the primary result, trigger a fallback fetch.
_FALLBACK_FIELDS = ("country", "duration", "douban_rating")


@register
class FallbackAdapter(BaseMetadataAdapter):
    """
    Try *primary* first, then *secondary* to fill missing fields.

    Default chain: opencli → wmdb.  The primary result is authoritative;
    the secondary only supplements fields that are ``None`` or empty.
    """

    name = "fallback"

    def __init__(
        self,
        primary_name: str = "opencli",
        secondary_name: str = "wmdb",
    ) -> None:
        self._primary = get_adapter(primary_name)
        self._secondary = get_adapter(secondary_name)

    def fetch(self, movie_id: str) -> Optional[dict]:
        result = self._primary.fetch(movie_id)

        if result is None:
            logger.info("Primary (%s) failed for %s, trying secondary (%s)",
                        self._primary.name, movie_id, self._secondary.name)
            return self._secondary.fetch(movie_id)

        if self._has_gaps(result):
            logger.debug("Filling missing fields for %s from %s",
                         movie_id, self._secondary.name)
            supplement = self._secondary.fetch(movie_id)
            if supplement is not None:
                result = self._merge(result, supplement)

        return result

    @staticmethod
    def _has_gaps(data: dict) -> bool:
        for field in _FALLBACK_FIELDS:
            value = data.get(field)
            if value is None or value == "" or value == []:
                return True
        return False

    @staticmethod
    def _merge(primary: dict, secondary: dict) -> dict:
        """Fill None/empty fields in *primary* with values from *secondary*."""
        merged = dict(primary)
        for key, value in secondary.items():
            existing = merged.get(key)
            if existing is None or existing == "" or existing == []:
                merged[key] = value
        return merged
