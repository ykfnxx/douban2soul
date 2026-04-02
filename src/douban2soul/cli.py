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

from douban2soul.analysis.llm_client import LLMClientFactory, AnalysisConfig
from douban2soul.analysis.profiler import ProfileAnalyzer
from douban2soul.statistics.engine import StatsEngine


def load_data(data_file: str) -> list:
    """Load movie viewing records from JSON file"""
    with open(data_file, 'r', encoding='utf-8') as f:
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

    config = AnalysisConfig(
        llm_provider=args.provider,
        model=args.model,
    )

    try:
        llm = LLMClientFactory.create(config)
    except ValueError as e:
        print(f"Error: {e}")
        print("  Please set the corresponding environment variable:")
        print('    export MOONSHOT_API_KEY="sk-xxx"   # for Moonshot')
        print('    export OPENAI_API_KEY="sk-xxx"     # for OpenAI')
        return 1

    output_dir = Path(args.output)

    print("=" * 60)
    print("Douban2Soul - Movie Record Personality Profile Analysis")
    print("=" * 60)
    print(f"Data file: {data_path}")
    print(f"LLM provider: {args.provider}")
    print(f"Output directory: {output_dir}")
    print("=" * 60)

    print("\n[1/5] Loading data...")
    data = load_data(str(data_path))
    print(f"  Total movies: {len(data)}")
    print(f"  With comments: {len([d for d in data if d.get('myComment')])}")

    print("\n[2/5] Generating L1 base statistics...")
    stats = StatsEngine()
    l1_report = stats.generate_base_stats(data)
    save_report(output_dir, "01_base_stats.md", l1_report)

    print("\n[3/5] Generating L2 comment analysis (using LLM)...")
    profiler = ProfileAnalyzer(llm)
    l2_report = profiler.generate_comment_analysis(data)
    save_report(output_dir, "02_comment_insights.md", l2_report)

    print("\n[4/5] Generating L3 dimensional analysis...")
    l3_report = stats.generate_dimension_analysis(data)
    save_report(output_dir, "03_dimension_analysis.md", l3_report)

    print("\n[5/5] Generating L4 comprehensive profile (using LLM)...")
    l4_report = profiler.generate_final_profile(data, l2_report, l3_report)
    save_report(output_dir, "04_final_profile.md", l4_report)

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
    scraper = FieldLevelScraper(cache=cache)
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
                           choices=["moonshot", "openai", "dashscope", "deepseek"],
                           help="LLM provider")
    p_analyze.add_argument("--model", "-m", default=None,
                           help="Model name")

    # --- scrape ---
    p_scrape = subparsers.add_parser(
        "scrape",
        help="Scrape movie metadata from wmdb.tv",
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
