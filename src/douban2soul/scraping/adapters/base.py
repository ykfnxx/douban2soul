"""Base interface for metadata source adapters."""

from abc import ABC, abstractmethod
from typing import Optional


class BaseMetadataAdapter(ABC):
    """
    Metadata source adapter.

    Each adapter fetches movie metadata from a single source.
    Subclasses must set ``name`` and implement ``fetch``.
    """

    name: str = ""

    @abstractmethod
    def fetch(self, movie_id: str) -> Optional[dict]:
        """
        Fetch metadata for a movie by its Douban ID.

        Returns a dict with available fields on success, or None on failure.
        Expected fields (all optional):
            title, original_title, year, genre (list), director (list),
            cast (list), country, duration (int, minutes),
            douban_rating (float), rating_count (int).
        """
        ...
