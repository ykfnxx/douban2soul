"""Tests for wmdb adapter retry logic."""

import time
from unittest.mock import MagicMock, patch

import pytest
import requests

from douban2soul.scraping.adapters.wmdb import WMDBAdapter, _MAX_RETRIES


@pytest.fixture()
def adapter() -> WMDBAdapter:
    a = WMDBAdapter()
    # Eliminate inter-request delay for tests
    a._last_request_time = 0
    return a


def _ok_response(payload: dict) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = 200
    resp.json.return_value = payload
    return resp


VALID_PAYLOAD = {
    "data": [
        {
            "name": "Test Movie",
            "originalName": "Test Movie",
            "year": "2024",
            "genre": "Drama/Sci-Fi",
            "director": ["Director A"],
            "actor": ["Actor A"],
            "country": "USA",
            "duration": "120",
            "doubanScore": "8.0",
        }
    ]
}


class TestRetryOnTimeout:
    """Timeout / ConnectionError should trigger retries."""

    @patch("douban2soul.scraping.adapters.wmdb.time.sleep")
    @patch("douban2soul.scraping.adapters.wmdb.requests.get")
    def test_timeout_then_success(self, mock_get, mock_sleep, adapter):
        mock_get.side_effect = [
            requests.Timeout("timed out"),
            _ok_response(VALID_PAYLOAD),
        ]
        result = adapter.fetch("123")
        assert result is not None
        assert result["title"] == "Test Movie"
        assert mock_get.call_count == 2

    @patch("douban2soul.scraping.adapters.wmdb.time.sleep")
    @patch("douban2soul.scraping.adapters.wmdb.requests.get")
    def test_connection_error_then_success(self, mock_get, mock_sleep, adapter):
        mock_get.side_effect = [
            requests.ConnectionError("proxy timeout"),
            _ok_response(VALID_PAYLOAD),
        ]
        result = adapter.fetch("123")
        assert result is not None
        assert mock_get.call_count == 2

    @patch("douban2soul.scraping.adapters.wmdb.time.sleep")
    @patch("douban2soul.scraping.adapters.wmdb.requests.get")
    def test_all_retries_exhausted(self, mock_get, mock_sleep, adapter):
        mock_get.side_effect = [requests.Timeout("t")] * _MAX_RETRIES
        result = adapter.fetch("123")
        assert result is None
        assert mock_get.call_count == _MAX_RETRIES


class TestRetryOnServerError:
    """HTTP 5xx should trigger retries."""

    @patch("douban2soul.scraping.adapters.wmdb.time.sleep")
    @patch("douban2soul.scraping.adapters.wmdb.requests.get")
    def test_500_then_success(self, mock_get, mock_sleep, adapter):
        err_resp = MagicMock(spec=requests.Response)
        err_resp.status_code = 502
        mock_get.side_effect = [err_resp, _ok_response(VALID_PAYLOAD)]
        result = adapter.fetch("123")
        assert result is not None
        assert mock_get.call_count == 2

    @patch("douban2soul.scraping.adapters.wmdb.time.sleep")
    @patch("douban2soul.scraping.adapters.wmdb.requests.get")
    def test_all_5xx_exhausted(self, mock_get, mock_sleep, adapter):
        err_resp = MagicMock(spec=requests.Response)
        err_resp.status_code = 500
        mock_get.side_effect = [err_resp] * _MAX_RETRIES
        result = adapter.fetch("123")
        assert result is None
        assert mock_get.call_count == _MAX_RETRIES


class TestRetryOn429:
    """HTTP 429 (rate limit) should trigger retries."""

    @patch("douban2soul.scraping.adapters.wmdb.time.sleep")
    @patch("douban2soul.scraping.adapters.wmdb.requests.get")
    def test_429_then_success(self, mock_get, mock_sleep, adapter):
        rate_resp = MagicMock(spec=requests.Response)
        rate_resp.status_code = 429
        mock_get.side_effect = [rate_resp, _ok_response(VALID_PAYLOAD)]
        result = adapter.fetch("123")
        assert result is not None
        assert mock_get.call_count == 2

    @patch("douban2soul.scraping.adapters.wmdb.time.sleep")
    @patch("douban2soul.scraping.adapters.wmdb.requests.get")
    def test_all_429_exhausted(self, mock_get, mock_sleep, adapter):
        rate_resp = MagicMock(spec=requests.Response)
        rate_resp.status_code = 429
        mock_get.side_effect = [rate_resp] * _MAX_RETRIES
        result = adapter.fetch("123")
        assert result is None


class TestNoRetryOnOtherErrors:
    """Non-transient errors should NOT retry."""

    @patch("douban2soul.scraping.adapters.wmdb.time.sleep")
    @patch("douban2soul.scraping.adapters.wmdb.requests.get")
    def test_generic_request_exception_no_retry(self, mock_get, mock_sleep, adapter):
        mock_get.side_effect = requests.RequestException("something bad")
        result = adapter.fetch("123")
        assert result is None
        assert mock_get.call_count == 1

    @patch("douban2soul.scraping.adapters.wmdb.time.sleep")
    @patch("douban2soul.scraping.adapters.wmdb.requests.get")
    def test_404_no_retry(self, mock_get, mock_sleep, adapter):
        resp = MagicMock(spec=requests.Response)
        resp.status_code = 404
        mock_get.return_value = resp
        result = adapter.fetch("123")
        assert result is None
        assert mock_get.call_count == 1


class TestBackoffTiming:
    """Verify exponential backoff waits are applied."""

    @patch("douban2soul.scraping.adapters.wmdb.time.sleep")
    @patch("douban2soul.scraping.adapters.wmdb.requests.get")
    def test_backoff_durations(self, mock_get, mock_sleep, adapter):
        mock_get.side_effect = [requests.Timeout("t")] * _MAX_RETRIES
        adapter.fetch("123")
        # Extract the backoff sleep calls (skip _wait sleeps)
        backoff_calls = [
            c.args[0] for c in mock_sleep.call_args_list
            if c.args[0] > 1  # _wait uses _MIN_INTERVAL=1.0
        ]
        assert backoff_calls == [2, 5, 10]
