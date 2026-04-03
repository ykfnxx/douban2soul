"""Tests for the OpenCLI adapter and fallback adapter."""

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from douban2soul.scraping.adapters.opencli import OpenCLIAdapter
from douban2soul.scraping.adapters.fallback import FallbackAdapter


# ------------------------------------------------------------------
# Sample data
# ------------------------------------------------------------------

OPENCLI_OUTPUT = json.dumps([
    {
        "casts": "蒂姆·罗宾斯,摩根·弗里曼,鲍勃·冈顿",
        "directors": "弗兰克·德拉邦特",
        "genres": "剧情,犯罪",
        "id": "1292052",
        "originalTitle": "",
        "rating": 9.7,
        "ratingCount": 3273945,
        "summary": "一场谋杀案...",
        "title": "肖申克的救赎 The Shawshank Redemption",
        "url": "https://movie.douban.com/subject/1292052",
        "year": "(1994)",
    }
])

WMDB_RESULT = {
    "title": "The Shawshank Redemption",
    "original_title": "The Shawshank Redemption",
    "year": "1994",
    "genre": ["Drama", "Crime"],
    "director": ["Frank Darabont"],
    "cast": ["Tim Robbins", "Morgan Freeman"],
    "country": "USA",
    "duration": 142,
    "douban_rating": 9.7,
    "rating_count": None,
}


# ------------------------------------------------------------------
# OpenCLI adapter
# ------------------------------------------------------------------

class TestOpenCLIAdapter:

    @patch("douban2soul.scraping.adapters.opencli.subprocess.run")
    def test_successful_fetch(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=OPENCLI_OUTPUT, stderr="",
        )
        adapter = OpenCLIAdapter()
        result = adapter.fetch("1292052")

        assert result is not None
        assert result["title"] == "肖申克的救赎 The Shawshank Redemption"
        assert result["year"] == "1994"
        assert result["genre"] == ["剧情", "犯罪"]
        assert result["director"] == ["弗兰克·德拉邦特"]
        assert result["cast"] == ["蒂姆·罗宾斯", "摩根·弗里曼", "鲍勃·冈顿"]
        assert result["douban_rating"] == 9.7
        assert result["rating_count"] == 3273945
        assert result["country"] is None
        assert result["duration"] is None

    @patch("douban2soul.scraping.adapters.opencli.subprocess.run")
    def test_opencli_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError()
        adapter = OpenCLIAdapter()
        assert adapter.fetch("123") is None

    @patch("douban2soul.scraping.adapters.opencli.subprocess.run")
    def test_opencli_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="opencli", timeout=30)
        adapter = OpenCLIAdapter()
        assert adapter.fetch("123") is None

    @patch("douban2soul.scraping.adapters.opencli.subprocess.run")
    def test_nonzero_exit(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="error",
        )
        adapter = OpenCLIAdapter()
        assert adapter.fetch("123") is None

    @patch("douban2soul.scraping.adapters.opencli.subprocess.run")
    def test_invalid_json(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="not json", stderr="",
        )
        adapter = OpenCLIAdapter()
        assert adapter.fetch("123") is None

    @patch("douban2soul.scraping.adapters.opencli.subprocess.run")
    def test_empty_array(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="[]", stderr="",
        )
        adapter = OpenCLIAdapter()
        assert adapter.fetch("123") is None

    @patch("douban2soul.scraping.adapters.opencli.subprocess.run")
    def test_year_parsing_variants(self, mock_run):
        """Year field can be '(1994)', '1994', or empty."""
        for year_input, expected in [("(1994)", "1994"), ("1994", "1994"), ("", None), (None, None)]:
            output = json.dumps([{
                "title": "Test", "year": year_input, "genres": "", "directors": "",
                "casts": "", "rating": None, "ratingCount": None,
                "originalTitle": "",
            }])
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout=output, stderr="",
            )
            result = OpenCLIAdapter().fetch("123")
            assert result is not None
            assert result["year"] == expected, f"Input {year_input!r} → expected {expected!r}"


# ------------------------------------------------------------------
# Fallback adapter
# ------------------------------------------------------------------

class TestFallbackAdapter:

    def _make_fallback(self, primary_result, secondary_result):
        adapter = FallbackAdapter.__new__(FallbackAdapter)
        adapter._primary = MagicMock()
        adapter._primary.name = "opencli"
        adapter._primary.fetch.return_value = primary_result
        adapter._secondary = MagicMock()
        adapter._secondary.name = "wmdb"
        adapter._secondary.fetch.return_value = secondary_result
        return adapter

    def test_primary_success_no_gaps(self):
        """Primary returns complete data — secondary not called."""
        primary = {
            "title": "Test", "country": "USA", "duration": 120,
            "douban_rating": 8.0,
        }
        adapter = self._make_fallback(primary, None)
        result = adapter.fetch("123")
        assert result == primary
        adapter._secondary.fetch.assert_not_called()

    def test_primary_with_gaps_filled_by_secondary(self):
        """Primary missing country/duration — secondary fills them."""
        primary = {
            "title": "肖申克的救赎", "country": None, "duration": None,
            "douban_rating": 9.7, "genre": ["剧情"],
        }
        secondary = {
            "title": "The Shawshank Redemption", "country": "USA",
            "duration": 142, "douban_rating": 9.7, "genre": ["Drama"],
        }
        adapter = self._make_fallback(primary, secondary)
        result = adapter.fetch("123")

        assert result["title"] == "肖申克的救赎"  # primary wins
        assert result["genre"] == ["剧情"]  # primary wins
        assert result["country"] == "USA"  # filled from secondary
        assert result["duration"] == 142  # filled from secondary

    def test_primary_fails_falls_back_entirely(self):
        """Primary returns None — secondary used entirely."""
        adapter = self._make_fallback(None, WMDB_RESULT)
        result = adapter.fetch("123")
        assert result == WMDB_RESULT
        adapter._secondary.fetch.assert_called_once_with("123")

    def test_both_fail(self):
        """Both adapters return None."""
        adapter = self._make_fallback(None, None)
        result = adapter.fetch("123")
        assert result is None

    def test_primary_gaps_secondary_also_fails(self):
        """Primary has gaps, secondary returns None — gaps remain."""
        primary = {"title": "Test", "country": None, "duration": None, "douban_rating": 8.0}
        adapter = self._make_fallback(primary, None)
        result = adapter.fetch("123")
        assert result["country"] is None
        assert result["duration"] is None
