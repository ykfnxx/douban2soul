#!/usr/bin/env python3
"""
Douban2Soul - CLI Entry Point

Usage:
    douban2soul analyze --data solid-yang.json --output output/
    douban2soul scrape  --data solid-yang.json [--resume] [--refresh-cache]
"""

import argparse
import json
import sys
from pathlib import Path

from douban2soul.statistics.engine import StatsEngine


_DEFAULT_METADATA_PATH = "cache/metadata.json"


def load_data(data_file: str) -> list:
    """Load movie viewing records from JSON file"""
    with open(data_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_metadata(path: str = _DEFAULT_METADATA_PATH) -> dict[str, dict]:
    """Load scraped metadata JSON. Returns empty dict if file is missing."""
    p = Path(path)
    if not p.exists():
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def save_report(output_dir: Path, filename: str, content: str):
    """Save report to file"""
    output_dir.mkdir(exist_ok=True)
    filepath = output_dir / filename
    filepath.write_text(content, encoding="utf-8")
    print(f"  Saved: {filename}")


# ------------------------------------------------------------------
# Subcommand: analyze
# ------------------------------------------------------------------

def cmd_analyze(args: argparse.Namespace) -> int:
    data_path = Path(args.data)
    if not data_path.exists():
        print(f"Data file not found: {data_path}")
        print("  Please ensure the movie records JSON file exists, or use --data to specify the path")
        return 1

    stats_only = args.stats_only
    output_dir = Path(args.output)

    # LLM is only needed for L2/L4
    llm = None
    if not stats_only:
        from douban2soul.analysis.llm_client import LLMClientFactory, AnalysisConfig
        from douban2soul.analysis.profiler import ProfileAnalyzer

        config = AnalysisConfig(
            llm_provider=args.provider,
            model=args.model,
            base_url=args.base_url,
        )
        try:
            llm = LLMClientFactory.create(config)
        except ValueError as e:
            print(f"Error: {e}")
            print("  Please set the corresponding environment variable:")
            print('    export MOONSHOT_API_KEY="sk-xxx"   # for Moonshot')
            print('    export OPENAI_API_KEY="sk-xxx"     # for OpenAI')
            print('    export LLM_API_KEY="sk-xxx" LLM_BASE_URL="https://..." # for openai-compat')
            return 1

    mode = "Statistics Only (L1 + L3)" if stats_only else "Full Analysis (L1-L5)"
    total_steps = 3 if stats_only else 6

    print("=" * 60)
    print("Douban2Soul - Movie Record Personality Profile Analysis")
    print("=" * 60)
    print(f"Data file: {data_path}")
    print(f"Mode: {mode}")
    if not stats_only:
        print(f"LLM provider: {args.provider}")
    print(f"Output directory: {output_dir}")
    print("=" * 60)

    step = 0

    step += 1
    print(f"\n[{step}/{total_steps}] Loading data...")
    data = load_data(str(data_path))
    metadata = load_metadata(args.metadata)
    print(f"  Total movies: {len(data)}")
    print(f"  With comments: {len([d for d in data if d.get('myComment')])}")
    print(f"  Metadata entries: {len(metadata)}")

    step += 1
    print(f"\n[{step}/{total_steps}] Generating L1 base statistics...")
    stats = StatsEngine(records=data, metadata=metadata)
    l1_report = stats.generate_l1_report()
    save_report(output_dir, "01_base_stats.md", l1_report)

    if not stats_only:
        step += 1
        print(f"\n[{step}/{total_steps}] Generating L2 comment analysis (using LLM)...")
        profiler = ProfileAnalyzer(llm, stream=args.stream)
        l2_report = profiler.generate_comment_analysis(data)
        save_report(output_dir, "02_comment_insights.md", l2_report)

    step += 1
    print(f"\n[{step}/{total_steps}] Generating L3 dimensional analysis...")
    l3_report = stats.generate_l3_report()
    save_report(output_dir, "03_dimension_analysis.md", l3_report)

    if not stats_only:
        step += 1
        print(f"\n[{step}/{total_steps}] Generating L4 comprehensive profile (using LLM)...")
        l4_report = profiler.generate_final_profile(data, l2_report, l3_report)
        save_report(output_dir, "04_final_profile.md", l4_report)

        step += 1
        print(f"\n[{step}/{total_steps}] Generating L5 comprehensive Chinese report (using LLM)...")
        llm_context = stats.generate_llm_context()
        l5_report = profiler.generate_comprehensive_report(
            llm_context, l1_report, l2_report, l3_report, l4_report,
        )
        save_report(output_dir, "05_comprehensive_report.md", l5_report)

    print("\n" + "=" * 60)
    print("Analysis complete!")
    print(f"Reports saved to: {output_dir}/")
    print("=" * 60)
    return 0


# ------------------------------------------------------------------
# Subcommand: scrape
# ------------------------------------------------------------------

def cmd_scrape(args: argparse.Namespace) -> int:
    from douban2soul.scraping.batch import BatchScraper
    from douban2soul.scraping.cache import MetadataCache
    from douban2soul.scraping.metadata import FieldLevelScraper

    data_path = Path(args.data)
    if not data_path.exists():
        print(f"Data file not found: {data_path}")
        return 1

    records = load_data(str(data_path))
    movie_ids = [r["movieId"] for r in records if "movieId" in r]

    if not movie_ids:
        print("No movie IDs found in data file.")
        return 1

    print(f"Scraping metadata for {len(movie_ids)} movies...")

    cache = MetadataCache() if not args.refresh_cache else MetadataCache(ttl_days=0)
    scraper = FieldLevelScraper(adapter_name=args.adapter, cache=cache)
    batch = BatchScraper(scraper=scraper, resume_file=args.resume_file)

    summary = batch.run(movie_ids, resume=args.resume)

    # Print summary
    print(f"\nDone!")
    print(f"  Total:   {summary['total']}")
    print(f"  Success: {len(summary['results'])}")
    print(f"  Failed:  {len(summary['failed'])}")
    print(f"  Cached:  {summary['cached']}")
    print(f"\nField coverage:")
    for field, rate in sorted(summary["coverage"].items()):
        print(f"  {field:20s} {rate:6.1%}")

    # Save results (strip cache internals from exported data)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results_data = {}
    for r in summary["results"]:
        raw = r.get("raw_data")
        if raw:
            clean = {k: v for k, v in raw.items() if not k.startswith("_")}
            results_data[r["movie_id"]] = clean
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(results_data, fh, ensure_ascii=False, indent=2)
    print(f"\nMetadata saved to: {output_path}")

    if summary["failed"]:
        print(f"\nFailed IDs ({len(summary['failed'])}):")
        for mid in summary["failed"][:10]:
            print(f"  {mid}")
        if len(summary["failed"]) > 10:
            print(f"  ... and {len(summary['failed']) - 10} more")

    return 0


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Douban2Soul - Movie record personality profile analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command")

    # --- analyze ---
    p_analyze = subparsers.add_parser(
        "analyze",
        help="Run L1-L4 personality profile analysis",
    )
    p_analyze.add_argument("--data", "-d", default="solid-yang.json",
                           help="Path to movie records JSON file")
    p_analyze.add_argument("--output", "-o", default="output",
                           help="Output directory")
    p_analyze.add_argument("--provider", "-p", default="moonshot",
                           choices=["moonshot", "openai", "dashscope", "deepseek", "openai-compat"],
                           help="LLM provider (use openai-compat for any OpenAI API-compatible service)")
    p_analyze.add_argument("--model", "-m", default=None,
                           help="Model name")
    p_analyze.add_argument("--base-url", default=None,
                           help="API base URL (required for openai-compat provider)")
    p_analyze.add_argument("--metadata", default=_DEFAULT_METADATA_PATH,
                           help="Path to scraped metadata JSON")
    p_analyze.add_argument("--stream", action="store_true",
                           help="Stream LLM output to terminal in real-time")
    p_analyze.add_argument("--stats-only", action="store_true",
                           help="Generate only L1+L3 statistics reports (no LLM needed)")

    # --- scrape ---
    p_scrape = subparsers.add_parser(
        "scrape",
        help="Scrape movie metadata (opencli → wmdb fallback)",
    )
    p_scrape.add_argument("--data", "-d", required=True,
                          help="Path to movie records JSON file")
    p_scrape.add_argument("--output", "-o", default="cache/metadata.json",
                          help="Output metadata JSON file")
    p_scrape.add_argument("--resume", "-r", action="store_true",
                          help="Resume from last checkpoint")
    p_scrape.add_argument("--resume-file", default="cache/scrape_job.json",
                          help="Checkpoint file path")
    p_scrape.add_argument("--refresh-cache", action="store_true",
                          help="Ignore cached entries and re-fetch")
    p_scrape.add_argument("--adapter", default="fallback",
                          choices=["fallback", "opencli", "wmdb"],
                          help="Metadata source adapter (default: fallback)")

    args = parser.parse_args()

    if args.command == "analyze":
        return sys.exit(cmd_analyze(args))
    elif args.command == "scrape":
        return sys.exit(cmd_scrape(args))
    else:
        parser.print_help()
        return sys.exit(0)


if __name__ == "__main__":
    main()
