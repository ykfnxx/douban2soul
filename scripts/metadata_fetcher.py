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
            except:
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
                print(f"  Rate limited, pausing for 60s...")
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
                        'actor': movie.get('actor', [])[:10],  # top 10 actors
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
        # Check cache
        if douban_id in self.cache and self._is_valid(self.cache[douban_id]):
            return self.cache[douban_id]

        # Try wmdb
        data = self.fetch_wmdb(douban_id)

        # Save result (cache failures too to avoid repeated requests)
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


def main():
    """Test run"""
    print("=" * 60)
    print("Metadata Fetcher Test")
    print("=" * 60)

    # Load movie records
    data_file = Path(__file__).parent.parent / "solid-yang.json"
    if not data_file.exists():
        print(f"Data file not found: {data_file}")
        return

    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    movie_ids = list(dict.fromkeys([d["movieId"] for d in data if d.get("movieId")]))
    print(f"Total movies: {len(movie_ids)}")

    # Create fetcher
    fetcher = MetadataFetcher()

    # Batch fetch (test first 5)
    test_ids = movie_ids[:5]
    print(f"\nTest fetching first {len(test_ids)} movies...")

    for mid in test_ids:
        result = fetcher.fetch(mid)
        if result and not result.get("_failed"):
            print(f"OK {mid}: {result.get('title')} ({result.get('year')})")
            print(f"    Genre: {', '.join(result.get('genre', []))}")
            print(f"    Director: {', '.join(result.get('director', [])[:3])}")
        else:
            print(f"FAIL {mid}: fetch failed")

    print("\n" + "=" * 60)
    print("To fetch all metadata, run:")
    print('  python -c "from scripts.metadata_fetcher import MetadataFetcher; \\')
    print('    f = MetadataFetcher(); f.batch_fetch(movie_ids)"')
    print("=" * 60)


if __name__ == "__main__":
    main()
