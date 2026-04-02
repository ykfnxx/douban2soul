#!/usr/bin/env python3
"""
Douban2Soul - CLI Entry Point
Douban movie record personality profile analysis

Usage:
    douban2soul --data solid-yang.json --output output/
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


def main():
    parser = argparse.ArgumentParser(
        description="Douban movie record personality profile analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using Moonshot
  export MOONSHOT_API_KEY="your_key"
  douban2soul

  # Using OpenAI
  export OPENAI_API_KEY="your_key"
  douban2soul --provider openai

  # Specify data and output paths
  douban2soul --data my-movies.json --output reports/
        """
    )

    parser.add_argument(
        "--data", "-d",
        default="solid-yang.json",
        help="Path to movie records JSON file (default: solid-yang.json)"
    )

    parser.add_argument(
        "--output", "-o",
        default="output",
        help="Output directory (default: output)"
    )

    parser.add_argument(
        "--provider", "-p",
        default="moonshot",
        choices=["moonshot", "openai", "dashscope", "deepseek"],
        help="LLM provider (default: moonshot)"
    )

    parser.add_argument(
        "--model", "-m",
        default=None,
        help="Model name (defaults to provider's default model)"
    )

    args = parser.parse_args()

    # Check data file
    data_path = Path(args.data)
    if not data_path.exists():
        print(f"Data file not found: {data_path}")
        print("  Please ensure the movie records JSON file exists, or use --data to specify the path")
        return 1

    # Configure LLM
    config = AnalysisConfig(
        llm_provider=args.provider,
        model=args.model
    )

    try:
        llm = LLMClientFactory.create(config)
    except ValueError as e:
        print(f"Error: {e}")
        print("  Please set the corresponding environment variable:")
        print('    export MOONSHOT_API_KEY="sk-xxx"   # for Moonshot')
        print('    export OPENAI_API_KEY="sk-xxx"     # for OpenAI')
        return 1

    # Run analysis
    output_dir = Path(args.output)

    print("=" * 60)
    print("Douban2Soul - Movie Record Personality Profile Analysis")
    print("=" * 60)
    print(f"Data file: {data_path}")
    print(f"LLM provider: {args.provider}")
    print(f"Output directory: {output_dir}")
    print("=" * 60)

    # Load data
    print("\n[1/5] Loading data...")
    data = load_data(str(data_path))
    print(f"  Total movies: {len(data)}")
    print(f"  With comments: {len([d for d in data if d.get('myComment')])}")

    # L1: Base statistics (no LLM)
    print("\n[2/5] Generating L1 base statistics...")
    stats = StatsEngine()
    l1_report = stats.generate_base_stats(data)
    save_report(output_dir, "01_base_stats.md", l1_report)

    # L2: Comment analysis (LLM)
    print("\n[3/5] Generating L2 comment analysis (using LLM)...")
    profiler = ProfileAnalyzer(llm)
    l2_report = profiler.generate_comment_analysis(data)
    save_report(output_dir, "02_comment_insights.md", l2_report)

    # L3: Dimensional analysis (no LLM)
    print("\n[4/5] Generating L3 dimensional analysis...")
    l3_report = stats.generate_dimension_analysis(data)
    save_report(output_dir, "03_dimension_analysis.md", l3_report)

    # L4: Comprehensive profile (LLM)
    print("\n[5/5] Generating L4 comprehensive profile (using LLM)...")
    l4_report = profiler.generate_final_profile(data, l2_report, l3_report)
    save_report(output_dir, "04_final_profile.md", l4_report)

    print("\n" + "=" * 60)
    print("Analysis complete!")
    print(f"Reports saved to: {output_dir}/")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
