"""
Batch metadata scraper with progress bar and resume support.
"""

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Optional

from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
)

from douban2soul.scraping.metadata import FIELD_CONFIG, FieldLevelScraper

logger = logging.getLogger(__name__)

_DEFAULT_RESUME_FILE = "cache/scrape_job.json"
_CHECKPOINT_INTERVAL = 10


class BatchScraper:
    """
    Batch-scrape metadata for a list of movie IDs.

    Features:
    - Rich progress bar with success/fail counters and ETA
    - ``--resume`` support via a checkpoint file
    - Field-level coverage statistics

    On resume, previously completed IDs are re-read from cache so that
    the returned result set is always *complete* (not just the delta).
    """

    def __init__(
        self,
        scraper: Optional[FieldLevelScraper] = None,
        resume_file: str = _DEFAULT_RESUME_FILE,
    ) -> None:
        self._scraper = scraper or FieldLevelScraper()
        self._resume_path = Path(resume_file)

    def run(
        self,
        movie_ids: list[str],
        *,
        resume: bool = False,
        show_progress: bool = True,
    ) -> dict:
        """
        Scrape *movie_ids* and return an aggregate result dict.

        The returned ``results`` list always covers all successfully
        scraped IDs (including those restored from a prior checkpoint).
        """
        completed = self._load_checkpoint() if resume else set()
        if not resume:
            self._clear_checkpoint()

        pending = [mid for mid in movie_ids if mid not in completed]

        success_list: list[dict] = []
        failed_list: list[str] = []
        cached_count = 0
        field_hits: dict[str, int] = defaultdict(int)

        # Replay previously completed IDs from cache so the output is complete.
        # If cache is missing/expired for a checkpoint ID, demote it back to pending.
        if resume and completed:
            still_completed: set[str] = set()
            for mid in movie_ids:
                if mid not in completed:
                    continue
                cached_raw = self._scraper.cache.get(mid)
                if cached_raw is not None:
                    result = self._scraper.scrape(mid)  # guaranteed cache hit
                    success_list.append(result)
                    cached_count += 1
                    still_completed.add(mid)
                    for field, info in result["fields"].items():
                        if info["present"]:
                            field_hits[field] += 1
                else:
                    # Cache lost/expired — need to re-fetch.
                    pending.append(mid)
            completed = still_completed

        # Process pending IDs.
        total_pending = len(pending)
        if total_pending > 0:
            progress_ctx = _build_progress() if show_progress else _noop_progress()
            with progress_ctx as progress:
                task = progress.add_task(
                    "Scraping metadata",
                    total=total_pending,
                    success=0,
                    failed=0,
                ) if show_progress else None

                for i, movie_id in enumerate(pending):
                    result = self._scraper.scrape(movie_id)

                    if result["fetch_success"]:
                        success_list.append(result)
                        completed.add(movie_id)
                        # A true cache hit has source="cache" on its fields.
                        if any(
                            f["source"] == "cache"
                            for f in result["fields"].values()
                            if f["present"]
                        ):
                            cached_count += 1
                        for field, info in result["fields"].items():
                            if info["present"]:
                                field_hits[field] += 1
                    else:
                        failed_list.append(movie_id)

                    if task is not None:
                        progress.update(
                            task,
                            advance=1,
                            success=len(success_list),
                            failed=len(failed_list),
                        )

                    if (i + 1) % _CHECKPOINT_INTERVAL == 0:
                        self._save_checkpoint(completed)

        self._save_checkpoint(completed)
        self._scraper.cache.flush()

        return self._summary(
            success_list, failed_list, cached_count, field_hits, len(movie_ids),
        )

    # ------------------------------------------------------------------
    # Checkpoint helpers
    # ------------------------------------------------------------------

    def _load_checkpoint(self) -> set[str]:
        if not self._resume_path.exists():
            return set()
        try:
            with open(self._resume_path, "r", encoding="utf-8") as fh:
                return set(json.load(fh))
        except (json.JSONDecodeError, OSError):
            return set()

    def _save_checkpoint(self, completed: set[str]) -> None:
        self._resume_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._resume_path, "w", encoding="utf-8") as fh:
            json.dump(sorted(completed), fh)

    def _clear_checkpoint(self) -> None:
        if self._resume_path.exists():
            self._resume_path.unlink()

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    @staticmethod
    def _summary(
        success: list[dict],
        failed: list[str],
        cached: int,
        field_hits: dict[str, int],
        total: int,
    ) -> dict:
        coverage = {
            field: (field_hits[field] / total if total else 0)
            for field in FIELD_CONFIG
        }
        return {
            "results": success,
            "failed": failed,
            "cached": cached,
            "total": total,
            "coverage": coverage,
        }


# ------------------------------------------------------------------
# Progress bar helpers
# ------------------------------------------------------------------

def _build_progress() -> Progress:
    return Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40),
        MofNCompleteColumn(),
        TextColumn("ok:{task.fields[success]}"),
        TextColumn("err:{task.fields[failed]}"),
        TimeRemainingColumn(),
    )


class _noop_progress:
    """Dummy context manager used when progress display is disabled."""

    def __enter__(self) -> "_noop_progress":
        return self

    def __exit__(self, *_: object) -> None:
        pass

    def add_task(self, *_: object, **__: object) -> None:  # type: ignore[override]
        return None

    def update(self, *_: object, **__: object) -> None:
        pass
