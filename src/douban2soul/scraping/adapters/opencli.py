"""OpenCLI-based metadata adapter (primary source)."""

import json
import logging
import subprocess
from typing import Optional

from douban2soul.scraping.adapters import register
from douban2soul.scraping.adapters.base import BaseMetadataAdapter

logger = logging.getLogger(__name__)

_TIMEOUT = 30  # seconds for the opencli subprocess


@register
class OpenCLIAdapter(BaseMetadataAdapter):
    """
    Fetch movie metadata via ``opencli douban subject <id> -f json``.

    OpenCLI talks directly to Douban, providing authoritative Chinese-language
    metadata.  It does not return ``country`` or ``duration``; callers that
    need those fields should fall back to another adapter (e.g. wmdb).
    """

    name = "opencli"

    def fetch(self, movie_id: str) -> Optional[dict]:
        try:
            proc = subprocess.run(
                ["opencli", "douban", "subject", movie_id, "-f", "json"],
                capture_output=True,
                text=True,
                timeout=_TIMEOUT,
            )
        except FileNotFoundError:
            logger.error("opencli not found on PATH")
            return None
        except subprocess.TimeoutExpired:
            logger.warning("opencli timed out for %s", movie_id)
            return None

        if proc.returncode != 0:
            stderr = proc.stderr.strip()
            logger.warning("opencli failed for %s (rc=%d): %s", movie_id, proc.returncode, stderr)
            return None

        return self._parse(proc.stdout)

    @staticmethod
    def _parse(raw_output: str) -> Optional[dict]:
        try:
            data = json.loads(raw_output)
        except (json.JSONDecodeError, TypeError):
            return None

        if not data or not isinstance(data, list):
            return None

        movie = data[0]

        # Parse year: "(1994)" → "1994"
        year_raw = movie.get("year", "")
        year = year_raw.strip("() ") if year_raw else None

        # Parse comma-separated strings into lists
        genres_raw = movie.get("genres", "")
        genres = [g.strip() for g in genres_raw.split(",") if g.strip()] if genres_raw else []

        directors_raw = movie.get("directors", "")
        directors = [d.strip() for d in directors_raw.split(",") if d.strip()] if directors_raw else []

        casts_raw = movie.get("casts", "")
        casts = [c.strip() for c in casts_raw.split(",") if c.strip()] if casts_raw else []

        rating = movie.get("rating")
        rating_count = movie.get("ratingCount")

        return {
            "title": movie.get("title"),
            "original_title": movie.get("originalTitle") or None,
            "year": year,
            "genre": genres,
            "director": directors,
            "cast": casts[:10],
            "country": None,  # not available from opencli
            "duration": None,  # not available from opencli
            "douban_rating": float(rating) if rating is not None else None,
            "rating_count": int(rating_count) if rating_count is not None else None,
        }
