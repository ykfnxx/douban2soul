#!/usr/bin/env python3
"""
Statistics Engine - Pure data statistics, no LLM involved
Generates L1 base stats and L3 dimensional analysis reports
"""

from collections import Counter
from typing import List, Dict


class StatsEngine:
    """Data statistics engine for movie viewing records"""

    def generate_base_stats(self, data: List[Dict]) -> str:
        """
        L1: Base statistics report (no LLM required)
        """
        total = len(data)
        rated = [d for d in data if d.get("myRating")]
        comments = [d for d in data if d.get("myComment")]

        # Rating statistics
        ratings = [d["myRating"] for d in rated]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        rating_dist: Dict[int, int] = {}
        for r in ratings:
            rating_dist[r] = rating_dist.get(r, 0) + 1

        # Year distribution
        years: Dict[str, int] = {}
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
            bar = "\u2588" * int(pct / 2)
            report += f"| {score} | {count} | {pct:.1f}% | {bar} |\n"

        report += """
## Year Distribution (Top 10)
| Year | Count |
|------|-------|
"""
        for year, count in sorted(years.items(), key=lambda x: -x[1])[:10]:
            report += f"| {year} | {count} |\n"

        return report

    def generate_dimension_analysis(self, data: List[Dict]) -> str:
        """
        L3: Dimensional deep analysis (basic version, can be enhanced later)

        Dimensions:
        - Era preferences
        - Top-rated / low-rated movies
        - Genre/director/regional analysis (after metadata enrichment)
        """
        # Decade analysis
        years = Counter()
        for d in data:
            y = d.get('year')
            if y and str(y).isdigit():
                decade = f"{str(y)[:3]}0s"
                years[decade] += 1

        # Rating by year
        year_ratings: Dict[str, List] = {}
        for d in data:
            y = d.get('year')
            r = d.get('myRating')
            if y and r:
                if y not in year_ratings:
                    year_ratings[y] = []
                year_ratings[y].append(r)

        # Average rating per decade
        decade_avg: Dict[str, List] = {}
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
            if len(ratings) >= 3:
                avg = sum(ratings) / len(ratings)
                report += f"| {decade} | {avg:.1f} | {len(ratings)} |\n"

        report += """
## 3.2 Top-Rated Movies (Rating = 10)

"""
        high_rated = [d for d in data if d.get('myRating') == 10]
        report += f"Total: {len(high_rated)} perfect-score movies\n\n"

        high_by_decade: Dict[str, List[str]] = {}
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
        low_rated = [d for d in data if d.get('myRating') and d['myRating'] <= 4]
        report += f"Total: {len(low_rated)} low-rated movies\n\n"

        for d in low_rated[:10]:
            report += f"- \u300a{d['title']}\u300b({d.get('year', 'N/A')}): {d.get('myRating')} pts"
            if d.get('myComment'):
                comment = d['myComment'][:50] + "..." if len(d['myComment']) > 50 else d['myComment']
                report += f" - {comment}"
            report += "\n"

        report += """
---

*Note: Full genre/director/regional analysis requires metadata fetching to be completed.*
"""
        return report
