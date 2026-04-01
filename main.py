#!/usr/bin/env python3
"""
Douban2Soul - Entry Point
Douban movie record personality profile analysis

Usage:
    python main.py --data solid-yang.json --output output/
"""

import argparse
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from llm_client import LLMClientFactory, AnalysisConfig
from analysis_engine import DoubanAnalyzer


def main():
    parser = argparse.ArgumentParser(
        description="Douban movie record personality profile analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using Moonshot
  export MOONSHOT_API_KEY="your_key"
  python main.py

  # Using OpenAI
  export OPENAI_API_KEY="your_key"
  python main.py --provider openai

  # Specify data and output paths
  python main.py --data my-movies.json --output reports/
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
    print("=" * 60)
    print("Douban2Soul - Movie Record Personality Profile Analysis")
    print("=" * 60)
    print(f"Data file: {data_path}")
    print(f"LLM provider: {args.provider}")
    print(f"Output directory: {args.output}")
    print("=" * 60)

    analyzer = DoubanAnalyzer(llm, output_dir=args.output)
    analyzer.run_full_analysis(str(data_path))

    return 0


if __name__ == "__main__":
    sys.exit(main())
