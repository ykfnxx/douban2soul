"""Tests for the metadata scraping module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from douban2soul.scraping.adapters.base import BaseMetadataAdapter
from douban2soul.scraping.adapters import register, get_adapter, _registry
from douban2soul.scraping.cache import MetadataCache
from douban2soul.scraping.metadata import FieldLevelScraper, FIELD_CONFIG
from douban2soul.scraping.batch import BatchScraper


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

SAMPLE_RAW = {
    "title": "The Wandering Earth",
    "original_title": "The Wandering Earth",
    "year": "2019",
    "genre": ["Sci-Fi", "Adventure"],
    "director": ["Frant Gwo"],
    "cast": ["Qu Chuxiao", "Li Guangjie"],
    "country": "China",
    "duration": 125,
    "douban_rating": 7.9,
    "rating_count": None,
}


class FakeAdapter(BaseMetadataAdapter):
    """Deterministic adapter for tests."""

    name = "fake"

    def __init__(self) -> None:
        self.data: dict[str, dict | None] = {}

    def fetch(self, movie_id: str) -> dict | None:
        return self.data.get(movie_id)


@pytest.fixture()
def tmp_cache(tmp_path: Path) -> MetadataCache:
    return MetadataCache(path=str(tmp_path / "cache.json"), ttl_days=90)


@pytest.fixture()
def fake_adapter() -> FakeAdapter:
    adapter = FakeAdapter()
    adapter.data["12345"] = SAMPLE_RAW.copy()
    return adapter


@pytest.fixture()
def scraper(fake_adapter: FakeAdapter, tmp_cache: MetadataCache) -> FieldLevelScraper:
    s = FieldLevelScraper(cache=tmp_cache)
    s._adapter = fake_adapter
    return s


# ------------------------------------------------------------------
# MetadataCache
# ------------------------------------------------------------------

class TestMetadataCache:
    def test_set_and_get(self, tmp_cache: MetadataCache) -> None:
        tmp_cache.set("111", {"genre": ["Drama"]})
        assert tmp_cache.get("111") is not None
        assert tmp_cache.get("111")["genre"] == ["Drama"]

    def test_miss(self, tmp_cache: MetadataCache) -> None:
        assert tmp_cache.get("nonexistent") is None

    def test_expired(self, tmp_cache: MetadataCache) -> None:
        cache = MetadataCache(path=str(tmp_cache._path), ttl_days=0)
        cache.set("111", {"genre": ["Drama"]})
        assert cache.get("111") is None

    def test_flush_and_reload(self, tmp_path: Path) -> None:
        path = str(tmp_path / "c.json")
        c1 = MetadataCache(path=path)
        c1.set("a", {"x": 1})
        c1.flush()

        c2 = MetadataCache(path=path)
        assert c2.get("a") is not None


# ------------------------------------------------------------------
# FieldLevelScraper
# ------------------------------------------------------------------

class TestFieldLevelScraper:
    def test_successful_scrape(self, scraper: FieldLevelScraper) -> None:
        result = scraper.scrape("12345")
        assert result["fetch_success"] is True
        assert result["fields"]["genre"]["present"] is True
        assert result["fields"]["genre"]["value"] == ["Sci-Fi", "Adventure"]
        assert result["core_fields_present"] == 3  # genre, director, country

    def test_missing_movie(self, scraper: FieldLevelScraper) -> None:
        result = scraper.scrape("99999")
        assert result["fetch_success"] is False
        assert result["core_fields_present"] == 0

    def test_cache_hit(self, scraper: FieldLevelScraper) -> None:
        scraper.scrape("12345")  # populates cache
        result = scraper.scrape("12345")  # should hit cache
        assert result["fetch_success"] is True
        assert result["fields"]["genre"]["source"] == "cache"

    def test_partial_data(self, scraper: FieldLevelScraper, fake_adapter: FakeAdapter) -> None:
        fake_adapter.data["partial"] = {"genre": ["Drama"]}
        result = scraper.scrape("partial")
        assert result["fetch_success"] is True
        assert result["fields"]["genre"]["present"] is True
        assert result["fields"]["director"]["present"] is False
        assert result["core_fields_present"] == 1


# ------------------------------------------------------------------
# BatchScraper
# ------------------------------------------------------------------

class TestBatchScraper:
    def test_batch_run(self, scraper: FieldLevelScraper, fake_adapter: FakeAdapter,
                       tmp_path: Path) -> None:
        fake_adapter.data["a"] = SAMPLE_RAW.copy()
        fake_adapter.data["b"] = SAMPLE_RAW.copy()

        batch = BatchScraper(scraper=scraper, resume_file=str(tmp_path / "job.json"))
        summary = batch.run(["a", "b", "missing"], show_progress=False)

        assert len(summary["results"]) == 2
        assert len(summary["failed"]) == 1
        assert summary["total"] == 3
        assert summary["coverage"]["genre"] > 0

    def test_resume(self, scraper: FieldLevelScraper, fake_adapter: FakeAdapter,
                    tmp_path: Path) -> None:
        fake_adapter.data["a"] = SAMPLE_RAW.copy()
        fake_adapter.data["b"] = SAMPLE_RAW.copy()
        resume_file = str(tmp_path / "job.json")

        batch = BatchScraper(scraper=scraper, resume_file=resume_file)

        # First run - only "a" and "b" succeed
        batch.run(["a", "b"], show_progress=False)

        # Second run with resume - "a" and "b" already done, "c" is new
        fake_adapter.data["c"] = SAMPLE_RAW.copy()
        summary = batch.run(["a", "b", "c"], resume=True, show_progress=False)

        # Only "c" was pending
        assert len(summary["results"]) == 1
        assert summary["results"][0]["movie_id"] == "c"
