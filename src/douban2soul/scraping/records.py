#!/usr/bin/env python3
"""
Movie Records Scraper
Fetches user viewing records from Douban via OpenCLI

TODO: Implement scraping logic. Currently, records are loaded from
a pre-exported JSON file (e.g. solid-yang.json via OpenCLI).
"""

import json
from pathlib import Path
from typing import List, Dict


def load_records(data_file: str) -> List[Dict]:
    """
    Load movie viewing records from a JSON file.

    Args:
        data_file: Path to the JSON file containing viewing records

    Returns:
        List of movie record dicts
    """
    path = Path(data_file)
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {data_file}")

    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)
