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
    metadata including country and duration.
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

        year_raw = movie.get("year", "")
        year = str(year_raw).strip("() ") if year_raw else None

        genres = _to_list(movie.get("genres", ""))
        directors = _to_list(movie.get("directors", ""))
        casts = _to_list(movie.get("casts", ""))

        # country: array of strings or comma-separated string
        country_raw = movie.get("country")
        if isinstance(country_raw, list):
            country = "/".join(country_raw)
        elif isinstance(country_raw, str):
            country = country_raw or None
        else:
            country = None

        # duration: int (minutes) or string
        duration_raw = movie.get("duration")
        if isinstance(duration_raw, (int, float)):
            duration = int(duration_raw)
        elif isinstance(duration_raw, str):
            import re
            m = re.search(r"\d+", duration_raw)
            duration = int(m.group()) if m else None
        else:
            duration = None

        rating = movie.get("rating")
        rating_count = movie.get("ratingCount")

        return {
            "title": movie.get("title"),
            "original_title": movie.get("originalTitle") or None,
            "year": year,
            "genre": genres,
            "director": directors,
            "cast": casts[:10],
            "country": country,
            "duration": duration,
            "douban_rating": float(rating) if rating is not None else None,
            "rating_count": int(rating_count) if rating_count is not None else None,
        }


def _to_list(value: object) -> list[str]:
    """Convert a value to a list of strings (handles both list and comma-separated string)."""
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str) and value:
        return [v.strip() for v in value.split(",") if v.strip()]
    return []
