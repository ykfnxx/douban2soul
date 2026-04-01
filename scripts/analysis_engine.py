#!/usr/bin/env python3
"""
Analysis Engine - Core analysis logic
Generates layered diagnostic reports (L1-L4)
"""

import json
from pathlib import Path
from typing import List, Dict
from llm_client import LLMClientFactory, AnalysisConfig, BaseLLMClient


class DoubanAnalyzer:
    """Douban movie record analyzer"""

    def __init__(self, llm_client: BaseLLMClient, output_dir: str = "output"):
        self.llm = llm_client
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def load_data(self, data_file: str) -> List[Dict]:
        """Load movie viewing records"""
        with open(data_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def generate_l1_base_stats(self, data: List[Dict]) -> str:
        """
        L1: Base statistics report (no LLM required)
        """
        total = len(data)
        rated = [d for d in data if d.get("myRating")]
        comments = [d for d in data if d.get("myComment")]

        # Rating statistics
        ratings = [d["myRating"] for d in rated]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        rating_dist = {}
        for r in ratings:
            rating_dist[r] = rating_dist.get(r, 0) + 1

        # Year distribution
        years = {}
        for d in data:
            y = d.get("year")
            if y:
                years[y] = years.get(y, 0) + 1

        report = f"""# L1: Base Statistics Report

## Data Overview
- **Total Movies**: {total}
- **Rated**: {len(rated)} ({len(rated)/total*100:.1f}%)
- **With Comments**: {len(comments)} ({len(comments)/total*100:.1f}%)

## Rating Statistics
- **Average Rating**: {avg_rating:.2f} / 10
- **Median Rating**: {sorted(ratings)[len(ratings)//2] if ratings else 'N/A'}

### Rating Distribution
| Rating | Count | Percentage | Visual |
|--------|-------|------------|--------|
"""
        for score in [10, 8, 6, 4, 2]:
            count = rating_dist.get(score, 0)
            pct = count / len(rated) * 100 if rated else 0
            bar = "█" * int(pct / 2)
            report += f"| {score} | {count} | {pct:.1f}% | {bar} |\n"

        report += f"""
## Year Distribution (Top 10)
| Year | Count |
|------|-------|
"""
        for year, count in sorted(years.items(), key=lambda x: -x[1])[:10]:
            report += f"| {year} | {count} |\n"

        return report

    def generate_l2_comment_analysis(self, data: List[Dict]) -> str:
        """
        L2: Comment semantic analysis (requires LLM)

        Key design: ~192 comments can be fed to LLM in one shot, no chunking needed.
        - Total chars: ~15,000
        - Estimated tokens: ~22,500
        - Kimi 128K context: sufficient
        """
        commented = [d for d in data if d.get("myComment")]

        if not commented:
            return "# L2: Comment Semantic Analysis\n\nNo comments found for this user."

        print(f"[L2] Analyzing {len(commented)} comments...")

        # Build comment text
        comments_text = []
        for i, d in enumerate(commented, 1):
            comment = d.get("myComment", "").strip()
            if comment:
                comments_text.append(
                    f"{i}. 《{d['title']}》(rating: {d.get('myRating', 'N/A')}): {comment}"
                )

        full_comments = "\n".join(comments_text)

        # Estimate tokens
        estimated_tokens = int(len(full_comments) * 1.5 + 2000)
        print(f"  Estimated tokens: ~{estimated_tokens} (Kimi 128K limit: sufficient)")

        prompt = f"""You are an expert in film psychology, text analysis, and Big Five personality theory.
Please perform a deep analysis of the following Douban user's movie comments.
Note: The comments are in Chinese. Analyze them in their original language for accuracy,
but write your analysis output in English.

## User Basic Data
- Total movies watched: {len(data)}
- Comments available: {len(commented)}

## User Comment List
{full_comments}

## Analysis Requirements

Please conduct a professional analysis from the following dimensions:

### 1. Topic Focus Distribution (Top 5)
What movie elements does the user discuss most frequently?

### 2. Sentiment Analysis
- Overall sentiment tone (positive / negative / neutral)
- Emotional expression intensity
- Emotional responses to different types of films

### 3. Value Clues
Inferred values, stances, and beliefs from the comments

### 4. Aesthetic Standards
The user's core criteria for evaluating movies
- What earns a positive review?
- What leads to a negative review?
- Does the user prioritize form or content?

### 5. Language Style Features
Expression patterns, expertise level, unique phrasing, humor

### 6. Personality Trait Inference (Big Five)
- Openness
- Conscientiousness
- Extraversion
- Agreeableness
- Neuroticism

### 7. Unique Insights
3-5 unique discoveries about this user

Please output in structured Markdown format."""

        result = self.llm.complete(prompt)
        return f"# L2: Comment Semantic Analysis\n\n{result}"

    def generate_l3_dimension_analysis(self, data: List[Dict]) -> str:
        """
        L3: Dimensional deep analysis (basic version, can be enhanced later)

        Dimensions:
        - Genre preferences
        - Director preferences
        - Regional/era distribution
        """
        from collections import Counter

        # Decade analysis
        years = Counter()
        for d in data:
            y = d.get('year')
            if y and str(y).isdigit():
                decade = f"{str(y)[:3]}0s"
                years[decade] += 1

        # Rating by year
        year_ratings = {}
        for d in data:
            y = d.get('year')
            r = d.get('myRating')
            if y and r:
                if y not in year_ratings:
                    year_ratings[y] = []
                year_ratings[y].append(r)

        # Average rating per decade
        decade_avg = {}
        for y, ratings in year_ratings.items():
            decade = f"{str(y)[:3]}0s"
            if decade not in decade_avg:
                decade_avg[decade] = []
            decade_avg[decade].extend(ratings)

        report = """# L3: Dimensional Deep Analysis

## 3.1 Era Preference Analysis

### Movies by Decade
| Decade | Count | Percentage |
|--------|-------|------------|
"""
        total = len(data)
        for decade, count in sorted(years.items()):
            pct = count / total * 100
            report += f"| {decade} | {count} | {pct:.1f}% |\n"

        report += """
### Average Rating by Decade
| Decade | Avg Rating | Sample Size |
|--------|------------|-------------|
"""
        for decade, ratings in sorted(decade_avg.items()):
            if len(ratings) >= 3:  # at least 3 movies to be statistically meaningful
                avg = sum(ratings) / len(ratings)
                report += f"| {decade} | {avg:.1f} | {len(ratings)} |\n"

        report += """
## 3.2 Top-Rated Movies (Rating = 10)

"""
        # Top-rated movies
        high_rated = [d for d in data if d.get('myRating') == 10]
        report += f"Total: {len(high_rated)} perfect-score movies\n\n"

        # Group by decade
        high_by_decade = {}
        for d in high_rated:
            y = d.get('year', 'Unknown')
            decade = f"{str(y)[:3]}0s" if str(y).isdigit() else 'Unknown'
            if decade not in high_by_decade:
                high_by_decade[decade] = []
            high_by_decade[decade].append(d['title'])

        for decade, titles in sorted(high_by_decade.items()):
            report += f"**{decade}**: {', '.join(titles[:5])}"
            if len(titles) > 5:
                report += f" and {len(titles) - 5} more"
            report += "\n\n"

        report += """
## 3.3 Low-Rated Movies (Rating <= 4)

"""
        # Low-rated movies
        low_rated = [d for d in data if d.get('myRating') and d['myRating'] <= 4]
        report += f"Total: {len(low_rated)} low-rated movies\n\n"

        for d in low_rated[:10]:
            report += f"- 《{d['title']}》({d.get('year', 'N/A')}): {d.get('myRating')} pts"
            if d.get('myComment'):
                comment = d['myComment'][:50] + "..." if len(d['myComment']) > 50 else d['myComment']
                report += f" - {comment}"
            report += "\n"

        report += """
---

*Note: Full genre/director/regional analysis requires metadata fetching to be completed.*
"""
        return report

    def generate_l4_final_profile(self, data: List[Dict], l2_analysis: str, l3_analysis: str) -> str:
        """
        L4: Comprehensive personality profile (requires LLM synthesis)
        Input: L2 comment analysis + L3 dimensional analysis
        """
        total = len(data)
        rated = [d for d in data if d.get("myRating")]
        avg_rating = sum(d["myRating"] for d in rated) / len(rated) if rated else 0

        print("[L4] Generating comprehensive personality profile...")

        prompt = f"""You are a professional psychoanalyst, film critic, and cultural researcher.
Based on the following analysis results, generate a comprehensive Movie Viewer Personality Profile
Diagnostic Report for this Douban user.

## Basic Data
- Total movies watched: {total}
- Average rating: {avg_rating:.1f}/10

## L2: Comment Analysis Summary
{l2_analysis[:2500]}

## L3: Dimensional Analysis Summary
{l3_analysis[:1500]}

## Report Requirements

Please generate a diagnostic report containing the following sections:

# Movie Viewer Personality Profile Diagnostic Report

## 1. Core Personality Profile
Big Five personality analysis based on viewing behavior, with vivid metaphors to describe
the user's "movie personality".

## 2. Aesthetic Orientation & Taste
- Genre preference tendencies
- Balance between art-house and commercial films
- Psychological traits reflected by era preferences
- Personal definition of a "good movie"

## 3. Values & Worldview
Values, social attitudes, and emotional needs inferred from movie choices.

## 4. Psychological Needs Analysis
Core psychological needs fulfilled by viewing behavior (emotional, cognitive, social).

## 5. Unique Labels
3-5 precise labels that encapsulate this user.

## 6. Movie Recommendation Directions
Personalized viewing recommendations based on the profile.

## 7. Summary
A core insight in under 200 words.

Report style: professional but accessible, warm yet insightful, well-reasoned."""

        result = self.llm.complete(prompt)
        return f"# L4: Comprehensive Personality Profile\n\n{result}"

    def run_full_analysis(self, data_file: str):
        """Run the full analysis pipeline"""
        print("=" * 60)
        print("Douban2Soul - Analysis Started")
        print("=" * 60)

        # Load data
        print("\n[1/5] Loading data...")
        data = self.load_data(data_file)
        print(f"  Total movies: {len(data)}")
        print(f"  With comments: {len([d for d in data if d.get('myComment')])}")

        # L1: Base statistics
        print("\n[2/5] Generating L1 base statistics...")
        l1_report = self.generate_l1_base_stats(data)
        self._save_report("01_base_stats.md", l1_report)

        # L2: Comment analysis
        print("\n[3/5] Generating L2 comment analysis (using LLM)...")
        l2_report = self.generate_l2_comment_analysis(data)
        self._save_report("02_comment_insights.md", l2_report)

        # L3: Dimensional deep analysis
        print("\n[4/5] Generating L3 dimensional analysis...")
        l3_report = self.generate_l3_dimension_analysis(data)
        self._save_report("03_dimension_analysis.md", l3_report)

        # L4: Comprehensive profile
        print("\n[5/5] Generating L4 comprehensive profile (using LLM)...")
        l4_report = self.generate_l4_final_profile(data, l2_report, l3_report)
        self._save_report("04_final_profile.md", l4_report)

        print("\n" + "=" * 60)
        print("Analysis complete!")
        print(f"Reports saved to: {self.output_dir}/")
        print("=" * 60)

    def _save_report(self, filename: str, content: str):
        """Save report to file"""
        filepath = self.output_dir / filename
        filepath.write_text(content, encoding="utf-8")
        print(f"  Saved: {filename}")


if __name__ == "__main__":
    import sys
    import os

    print("""
Usage:
------
# 1. Set API Key
export MOONSHOT_API_KEY="your_key"

# 2. Run analysis
python scripts/analysis_engine.py

# Or in Python:
from scripts.llm_client import LLMClientFactory, AnalysisConfig
from scripts.analysis_engine import DoubanAnalyzer

config = AnalysisConfig(llm_provider="moonshot")
llm = LLMClientFactory.create(config)
analyzer = DoubanAnalyzer(llm)
analyzer.run_full_analysis("solid-yang.json")
    """)

    if os.getenv("MOONSHOT_API_KEY") or os.getenv("OPENAI_API_KEY"):
        print("\nAPI Key detected, running analysis...")
        provider = "moonshot" if os.getenv("MOONSHOT_API_KEY") else "openai"
        config = AnalysisConfig(llm_provider=provider)
        llm = LLMClientFactory.create(config)
        analyzer = DoubanAnalyzer(llm)
        analyzer.run_full_analysis("solid-yang.json")
    else:
        print("\nNo API Key detected. Please set the environment variable first.")
