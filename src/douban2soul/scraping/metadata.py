#!/usr/bin/env python3
"""
Metadata Fetcher
Multi-source strategy: wmdb.tv (primary) + TMDB (fallback) + Douban direct (last resort)
"""

import json
import time
import random
import requests
from pathlib import Path
from typing import Dict, Optional, List


class MetadataFetcher:
    """Movie metadata fetcher"""

    def __init__(self, cache_file: str = "cache/metadata_cache.json"):
        self.cache_file = Path(cache_file)
        self.cache = self._load_cache()
        self.session = requests.Session()
        self.delay = 1.0  # base delay in seconds

    def _load_cache(self) -> Dict:
        """Load cache from file"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cache(self):
        """Save cache to file"""
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)

    def _is_valid(self, data) -> bool:
        """Check if data is valid"""
        if not data:
            return False
        if isinstance(data, dict):
            return "data" in data or "genre" in data or "director" in data
        return False

    def fetch_wmdb(self, douban_id: str) -> Optional[Dict]:
        """
        Fetch metadata from wmdb.tv
        Source: https://api.wmdb.tv/movie/api?id={id}
        """
        url = f"https://api.wmdb.tv/movie/api?id={douban_id}"

        try:
            time.sleep(self.delay + random.uniform(0, 1))
            resp = self.session.get(url, timeout=15)

            if resp.status_code == 429:
                print("  Rate limited, pausing for 60s...")
                time.sleep(60)
                return self.fetch_wmdb(douban_id)

            if resp.status_code == 200:
                data = resp.json()
                if data and 'data' in data and len(data['data']) > 0:
                    movie = data['data'][0]
                    return {
                        'title': movie.get('name'),
                        'original_title': movie.get('originalName'),
                        'year': movie.get('year'),
                        'genre': [g.strip() for g in movie.get('genre', '').split('/') if g.strip()],
                        'director': movie.get('director', []),
                        'actor': movie.get('actor', [])[:10],
                        'country': movie.get('country', ''),
                        'douban_rating': movie.get('doubanScore'),
                        'duration': movie.get('duration'),
                        'source': 'wmdb'
                    }
        except Exception as e:
            print(f"  wmdb error: {e}")

        return None

    def fetch(self, douban_id: str, title: str = "", year: str = "") -> Dict:
        """
        Smart metadata fetching with cache

        Strategy:
        1. Check cache first
        2. Try wmdb.tv
        3. Return empty structure on failure
        """
        if douban_id in self.cache and self._is_valid(self.cache[douban_id]):
            return self.cache[douban_id]

        data = self.fetch_wmdb(douban_id)

        self.cache[douban_id] = data or {"_failed": True}
        self._save_cache()

        return self.cache[douban_id]

    def batch_fetch(self, movie_ids: List[str], progress_interval: int = 10):
        """
        Batch fetch metadata

        Args:
            movie_ids: List of Douban movie IDs
            progress_interval: Progress print interval
        """
        results = {}
        total = len(movie_ids)
        cached = sum(1 for mid in movie_ids if mid in self.cache and self._is_valid(self.cache.get(mid)))

        print(f"Batch fetching metadata: {total} total, {cached} cached")

        for i, mid in enumerate(movie_ids):
            if i % progress_interval == 0:
                print(f"  Progress: {i}/{total} ({i/total*100:.1f}%)")

            result = self.fetch(mid)
            if result and not result.get("_failed"):
                results[mid] = result

        print(f"Done: successfully fetched {len(results)} movies")
        return results
