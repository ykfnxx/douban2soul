"""wmdb.tv metadata adapter (V1 primary and only source)."""

import logging
import re
import time
from typing import Optional

import requests

from douban2soul.scraping.adapters import register
from douban2soul.scraping.adapters.base import BaseMetadataAdapter

logger = logging.getLogger(__name__)

_API_URL = "https://api.wmdb.tv/movie/api"
_TIMEOUT = 10
_MIN_INTERVAL = 1.0  # seconds between requests
_RETRY_WAIT = 5  # seconds to wait after a 429


@register
class WMDBAdapter(BaseMetadataAdapter):
    """
    Fetch movie metadata from wmdb.tv using the Douban movie ID.

    Rate-limited to one request per second.  On HTTP 429 the adapter
    pauses briefly and returns None (the caller can retry later).
    """

    name = "wmdb"

    def __init__(self) -> None:
        self._last_request_time: float = 0

    def fetch(self, movie_id: str) -> Optional[dict]:
        self._wait()

        try:
            resp = requests.get(
                _API_URL,
                params={"id": movie_id},
                timeout=_TIMEOUT,
            )
        except requests.Timeout:
            logger.warning("Timeout fetching %s from wmdb", movie_id)
            return None
        except requests.RequestException as exc:
            logger.warning("Request error for %s: %s", movie_id, exc)
            return None

        if resp.status_code == 429:
            logger.warning("Rate-limited by wmdb for %s, backing off", movie_id)
            time.sleep(_RETRY_WAIT)
            return None

        if resp.status_code != 200:
            logger.warning("wmdb returned %d for %s", resp.status_code, movie_id)
            return None

        return self._parse(resp)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _wait(self) -> None:
        elapsed = time.time() - self._last_request_time
        if elapsed < _MIN_INTERVAL:
            time.sleep(_MIN_INTERVAL - elapsed)
        self._last_request_time = time.time()

    def _parse(self, resp: requests.Response) -> Optional[dict]:
        try:
            payload = resp.json()
        except ValueError:
            return None

        if not payload or "data" not in payload or not payload["data"]:
            return None

        movie = payload["data"][0]
        return {
            "title": movie.get("name"),
            "original_title": movie.get("originalName"),
            "year": movie.get("year"),
            "genre": _split(movie.get("genre", ""), "/"),
            "director": movie.get("director") or [],
            "cast": (movie.get("actor") or [])[:10],
            "country": movie.get("country", ""),
            "duration": _parse_int(movie.get("duration")),
            "douban_rating": _parse_float(movie.get("doubanScore")),
            "rating_count": None,  # wmdb does not provide this
        }


def _split(value: str, sep: str) -> list[str]:
    return [part.strip() for part in value.split(sep) if part.strip()]


def _parse_int(value: object) -> Optional[int]:
    if value is None:
        return None
    match = re.search(r"\d+", str(value))
    return int(match.group()) if match else None


def _parse_float(value: object) -> Optional[float]:
    try:
        return float(value) if value else None
    except (ValueError, TypeError):
        return None
