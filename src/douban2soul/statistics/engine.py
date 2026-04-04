"""
Statistics Engine — orchestrates all statistical computations and report generation.

Produces three output targets from one data pass:
  1. L1 Report (markdown) — base statistics overview
  2. L3 Report (markdown) — dimensional deep analysis
  3. LLM Context (dict)  — structured data for L2/L4 personality profiling
"""

from douban2soul.statistics.categories import (
    compute_cast_stats,
    compute_comment_stats,
    compute_crowd_comparison,
    compute_director_stats,
    compute_genre_stats,
    compute_geography_stats,
    compute_habit_stats,
    compute_rating_stats,
    compute_taste_extremes,
    compute_temporal_stats,
)
from douban2soul.statistics.merge import merge_records_with_metadata


class StatsEngine:
    """
    Orchestrate statistical computations over viewing records + metadata.

    Parameters
    ----------
    records:
        Raw viewing records (list of dicts from the JSON export).
    metadata:
        Scraped metadata keyed by movieId.  Pass None or {} for
        record-only analysis (backward compatible).
    """

    def __init__(
        self,
        records: list[dict] | None = None,
        metadata: dict[str, dict] | None = None,
    ) -> None:
        self._records = records or []
        self._metadata = metadata
        self._merged: list[dict] | None = None
        self._stats: dict[str, dict] | None = None

    @property
    def merged(self) -> list[dict]:
        if self._merged is None:
            self._merged = merge_records_with_metadata(self._records, self._metadata)
        return self._merged

    @property
    def stats(self) -> dict[str, dict]:
        if self._stats is None:
            m = self.merged
            self._stats = {
                "rating": compute_rating_stats(m),
                "temporal": compute_temporal_stats(m),
                "genre": compute_genre_stats(m),
                "director": compute_director_stats(m),
                "geography": compute_geography_stats(m),
                "comments": compute_comment_stats(m),
                "crowd": compute_crowd_comparison(m),
                "habits": compute_habit_stats(m),
                "cast": compute_cast_stats(m),
                "taste_extremes": compute_taste_extremes(m),
            }
        return self._stats

    # ------------------------------------------------------------------
    # Legacy API (backward compatible with old cli.py calls)
    # ------------------------------------------------------------------

    def generate_base_stats(self, data: list[dict] | None = None) -> str:
        """L1: Base statistics overview (markdown)."""
        if data is not None:
            self._records = data
            self._merged = None
            self._stats = None
        return self.generate_l1_report()

    def generate_dimension_analysis(self, data: list[dict] | None = None) -> str:
        """L3: Dimensional deep analysis (markdown)."""
        if data is not None:
            self._records = data
            self._merged = None
            self._stats = None
        return self.generate_l3_report()

    # ------------------------------------------------------------------
    # L1 Report
    # ------------------------------------------------------------------

    def generate_l1_report(self) -> str:
        """L1: Base statistics overview (Categories A, B summary, F)."""
        s = self.stats
        r = s["rating"]
        t = s["temporal"]
        c = s["comments"]

        total = r["total_count"]
        rated = r["rated_count"]
        metadata_count = sum(
            1 for rec in self.merged
            if any(rec.get(f) is not None
                   for f in ("genre", "director", "country", "duration", "douban_rating"))
        )

        report = f"""# L1: Base Statistics Report

## Data Overview
- **Total Movies**: {total}
- **Rated**: {rated} ({rated / total * 100:.1f}%)
- **With Comments**: {c['comment_count']} ({c['comment_rate'] * 100:.1f}%)
- **Metadata Coverage**: {metadata_count} ({metadata_count / total * 100:.1f}%)

## Rating Statistics
- **Average Rating**: {r['mean']:.2f} / 10
- **Median Rating**: {r['median']}
- **Standard Deviation**: {r['stddev']:.2f}

### Rating Distribution
| Rating | Count | Percentage | Visual |
|--------|-------|------------|--------|
"""
        for score in [10, 8, 6, 4, 2]:
            count = r["distribution"].get(score, 0)
            pct = count / rated * 100 if rated else 0
            bar = "\u2588" * int(pct / 2)
            report += f"| {score} | {count} | {pct:.1f}% | {bar} |\n"

        # Comment overview
        report += f"""
## Comment Overview
- **Comment Rate**: {c['comment_rate'] * 100:.1f}%
- **Average Length**: {c['avg_length']:.0f} characters
"""
        return report

    # ------------------------------------------------------------------
    # L3 Report
    # ------------------------------------------------------------------

    def generate_l3_report(self) -> str:
        """L3: Dimensional deep analysis (Categories B-I)."""
        s = self.stats
        t = s["temporal"]
        g = s["genre"]
        d = s["director"]
        geo = s["geography"]
        crowd = s["crowd"]
        h = s["habits"]
        cast = s["cast"]
        taste = s["taste_extremes"]

        report = """# L3: Dimensional Deep Analysis

"""
        # B. Era Preference
        report += """## Era Preference Analysis

### Movies by Decade
| Decade | Count | Avg Rating |
|--------|-------|------------|
"""
        for decade, count in sorted(t["decade_distribution"].items()):
            avg = t["decade_avg_rating"].get(decade, "—")
            report += f"| {decade} | {count} | {avg} |\n"

        report += f"""
### Era Orientation
- **Recency ratio (post-2020)**: {t['recency_ratio'] * 100:.1f}%
- **Classic count (pre-2000)**: {t['pre_2000_count']}

"""
        # C. Genre Profile
        if g["records_with_genre"] > 0:
            report += """## Genre Profile

### Genre Distribution (Top 15)
| Genre | Count | % of Library | Avg Rating |
|-------|-------|-------------|------------|
"""
            total_genres = sum(c for _, c in g["top_genres"])
            for genre, count in g["top_genres"][:15]:
                pct = count / total_genres * 100
                avg = g["genre_avg_rating"].get(genre, "—")
                report += f"| {genre} | {count} | {pct:.1f}% | {avg} |\n"

            report += """
### Genre Cluster Scores
| Cluster | Score | Personality Signal |
|---------|-------|-------------------|
"""
            cluster_signals = {
                "Intellectual": "High Openness",
                "Mainstream Action": "Sensation Seeking",
                "Emotional Drama": "High Agreeableness / Empathy",
                "Thrill-seeking": "Low Neuroticism / Sensation Seeking",
                "Light Entertainment": "High Extraversion",
                "Artistic": "High Openness / Aesthetic Sensitivity",
            }
            for cluster, score in sorted(
                g["cluster_scores"].items(), key=lambda x: -x[1]
            ):
                signal = cluster_signals.get(cluster, "")
                report += f"| {cluster} | {score * 100:.1f}% | {signal} |\n"

            report += f"""
### Genre Diversity
- **Distinct genres**: {g['genre_diversity']}
- **Shannon entropy**: {g['genre_shannon_entropy']:.2f}

"""
        # D. Director Profile
        if d["total_with_director"] > 0:
            report += f"""## Director Profile

### Top Directors (\u22653 films)
| Director | Count | Avg Rating |
|----------|-------|------------|
"""
            for name, count, avg in d["top_directors"][:15]:
                report += f"| {name} | {count} | {avg} |\n"

            report += f"""
### Director Loyalty
- **Repeat director ratio**: {d['repeat_director_ratio'] * 100:.1f}%
- **Distinct directors**: {d['distinct_count']}

"""
        # E. Cultural Profile
        if geo["total_with_country"] > 0:
            report += """## Cultural Profile

### Country Distribution (Top 10)
| Country | Count | Avg Rating |
|---------|-------|------------|
"""
            for country, count in geo["top_countries"]:
                avg = geo["country_avg_rating"].get(country, "—")
                report += f"| {country} | {count} | {avg} |\n"

            report += f"""
### Cultural Orientation
- **Domestic ratio (China)**: {geo['domestic_ratio'] * 100:.1f}%
- **Country diversity**: {geo['country_diversity']} countries

### Region Distribution
| Region | Share |
|--------|-------|
"""
            for region, score in geo["region_scores"].items():
                report += f"| {region} | {score * 100:.1f}% |\n"
            report += "\n"

        # G. User vs. Crowd
        if crowd["pair_count"] > 0:
            report += f"""## User vs. Crowd

- **Average rating gap**: {crowd['rating_gap_mean']:+.2f} ({"rates higher" if crowd['rating_gap_mean'] > 0 else "rates lower"} than Douban crowd)
- **Gap std. deviation**: {crowd['rating_gap_stddev']:.2f}
- **Crowd alignment (Pearson r)**: {crowd['crowd_alignment_score']:.3f}
- **Comparison pairs**: {crowd['pair_count']}
"""
            if crowd["overrated_movies"]:
                report += "\n### Personal Favorites (rated much higher than crowd)\n"
                for title, my, db, gap in crowd["overrated_movies"][:5]:
                    report += f"- \u300a{title}\u300b: {my} vs {db} (gap {gap:+.1f})\n"

            if crowd["underrated_movies"]:
                report += "\n### Against the Grain (rated much lower than crowd)\n"
                for title, my, db, gap in crowd["underrated_movies"][:5]:
                    report += f"- \u300a{title}\u300b: {my} vs {db} (gap {gap:+.1f})\n"
            report += "\n"

        # H. Viewing Habits
        if h["total_with_duration"] > 0:
            report += f"""## Viewing Habits

- **Average film duration**: {h['avg_duration']:.0f} min
- **Long films (\u2265150 min)**: {h['long_film_ratio'] * 100:.1f}%

### Duration Distribution
| Category | Count |
|----------|-------|
| < 90 min | {h['duration_distribution']['short_lt90']} |
| 90-120 min | {h['duration_distribution']['standard_90_120']} |
| 120-150 min | {h['duration_distribution']['long_120_150']} |
| 150+ min | {h['duration_distribution']['very_long_150plus']} |
"""

        # I. Cast Analysis
        if cast["total_with_cast"] > 0:
            report += f"""## Cast Analysis

### Top Actors (\u22652 films)
| Actor | Count | Avg Rating |
|-------|-------|------------|
"""
            for name, count, avg in cast["top_actors"][:15]:
                report += f"| {name} | {count} | {avg} |\n"

            report += f"""
### Actor Loyalty
- **Repeat actor ratio**: {cast['repeat_actor_ratio'] * 100:.1f}%
- **Distinct actors**: {cast['distinct_count']}

"""

        # Taste Extremes
        if taste["hidden_gems"] or taste["avoid_zone"]:
            report += """## Taste Extremes

"""
            if taste["hidden_gems"]:
                report += "### Hidden Gems (user \u22658, crowd <6)\n"
                for title, my, crowd_r in taste["hidden_gems"][:5]:
                    report += f"- \u300a{title}\u300b: {my} vs {crowd_r}\n"
                report += "\n"

            if taste["avoid_zone"]:
                report += "### Against the Grain (user \u22644, crowd \u22657)\n"
                for title, my, crowd_r in taste["avoid_zone"][:5]:
                    report += f"- \u300a{title}\u300b: {my} vs {crowd_r}\n"
                report += "\n"

        return report

    # ------------------------------------------------------------------
    # LLM Context
    # ------------------------------------------------------------------

    def generate_llm_context(self) -> dict:
        """Structured data dict for LLM L2/L4 analysis."""
        s = self.stats
        metadata_count = sum(
            1 for rec in self.merged
            if any(rec.get(f) is not None
                   for f in ("genre", "director", "country", "duration", "douban_rating"))
        )
        total = s["rating"]["total_count"]

        return {
            "overview": {
                "total_movies": total,
                "rated_count": s["rating"]["rated_count"],
                "comment_count": s["comments"]["comment_count"],
                "metadata_coverage": round(metadata_count / total, 3) if total else 0,
            },
            "rating": {
                "mean": s["rating"]["mean"],
                "median": s["rating"]["median"],
                "stddev": s["rating"]["stddev"],
                "distribution": s["rating"]["distribution"],
            },
            "era": {
                "decade_distribution": s["temporal"]["decade_distribution"],
                "decade_avg_rating": s["temporal"]["decade_avg_rating"],
                "recency_ratio": s["temporal"]["recency_ratio"],
                "pre_2000_count": s["temporal"]["pre_2000_count"],
            },
            "genre": {
                "top_genres": s["genre"]["top_genres"][:15],
                "genre_avg_rating": s["genre"]["genre_avg_rating"],
                "cluster_scores": s["genre"]["cluster_scores"],
                "diversity_index": s["genre"]["genre_diversity"],
                "shannon_entropy": s["genre"]["genre_shannon_entropy"],
                "above_personal_mean": s["genre"]["genre_above_mean"],
                "below_personal_mean": s["genre"]["genre_below_mean"],
            },
            "director": {
                "top_directors": [
                    (name, count, avg)
                    for name, count, avg in s["director"]["top_directors"][:15]
                ],
                "repeat_ratio": s["director"]["repeat_director_ratio"],
                "distinct_count": s["director"]["distinct_count"],
            },
            "geography": {
                "top_countries": s["geography"]["top_countries"],
                "country_avg_rating": s["geography"]["country_avg_rating"],
                "domestic_ratio": s["geography"]["domestic_ratio"],
                "diversity_index": s["geography"]["country_diversity"],
                "region_scores": s["geography"]["region_scores"],
            },
            "crowd_comparison": {
                "mean_gap": s["crowd"]["rating_gap_mean"],
                "gap_stddev": s["crowd"]["rating_gap_stddev"],
                "correlation": s["crowd"]["crowd_alignment_score"],
                "pair_count": s["crowd"]["pair_count"],
                "overrated_movies": s["crowd"]["overrated_movies"][:5],
                "underrated_movies": s["crowd"]["underrated_movies"][:5],
            },
            "comments": {
                "rate": s["comments"]["comment_rate"],
                "avg_length": s["comments"]["avg_length"],
                "length_distribution": s["comments"]["length_distribution"],
                "avg_rating_with_comment": s["comments"]["avg_rating_with_comment"],
                "avg_rating_without_comment": s["comments"]["avg_rating_without_comment"],
            },
            "habits": {
                "avg_duration": s["habits"]["avg_duration"],
                "long_film_ratio": s["habits"]["long_film_ratio"],
                "duration_distribution": s["habits"]["duration_distribution"],
            },
            "cast": {
                "top_actors": [
                    (name, count, avg)
                    for name, count, avg in s["cast"]["top_actors"][:10]
                ],
                "repeat_ratio": s["cast"]["repeat_actor_ratio"],
                "distinct_count": s["cast"]["distinct_count"],
            },
            "taste_extremes": {
                "hidden_gems": s["taste_extremes"]["hidden_gems"][:5],
                "avoid_zone": s["taste_extremes"]["avoid_zone"][:5],
            },
        }
