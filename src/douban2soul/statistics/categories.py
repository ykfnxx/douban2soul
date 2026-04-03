"""
Statistical category computations.

Each function takes a list of merged records and returns a dict of metrics.
Categories are independent — no cross-category dependencies.
"""

import math
from collections import Counter, defaultdict

from douban2soul.statistics.taxonomy import GENRE_CLUSTERS, genre_cluster, country_region


# ------------------------------------------------------------------
# A. Rating Behavior
# ------------------------------------------------------------------

def compute_rating_stats(records: list[dict]) -> dict:
    """Category A: Rating behavior metrics."""
    ratings = [r["my_rating"] for r in records if r["my_rating"] is not None]
    total = len(records)
    rated_count = len(ratings)

    if not ratings:
        return {
            "mean": 0.0,
            "median": 0,
            "stddev": 0.0,
            "distribution": {},
            "rated_count": 0,
            "total_count": total,
        }

    mean = sum(ratings) / len(ratings)
    sorted_r = sorted(ratings)
    median = sorted_r[len(sorted_r) // 2]
    variance = sum((r - mean) ** 2 for r in ratings) / len(ratings)
    stddev = math.sqrt(variance)

    distribution: dict[int, int] = Counter(ratings)

    return {
        "mean": round(mean, 2),
        "median": median,
        "stddev": round(stddev, 2),
        "distribution": dict(sorted(distribution.items(), reverse=True)),
        "rated_count": rated_count,
        "total_count": total,
    }


# ------------------------------------------------------------------
# B. Temporal Patterns
# ------------------------------------------------------------------

def compute_temporal_stats(records: list[dict]) -> dict:
    """Category B: Temporal pattern metrics."""
    decade_counts: Counter[str] = Counter()
    decade_ratings: dict[str, list[int]] = defaultdict(list)
    viewing_year_counts: Counter[str] = Counter()
    viewing_month_counts: Counter[int] = Counter()

    for r in records:
        year = r.get("year")
        if year and str(year).isdigit():
            decade = f"{str(year)[:3]}0s"
            decade_counts[decade] += 1
            if r["my_rating"] is not None:
                decade_ratings[decade].append(r["my_rating"])

        my_date = r.get("my_date")
        if my_date and len(my_date) >= 7:
            viewing_year_counts[my_date[:4]] += 1
            try:
                month = int(my_date[5:7])
                viewing_month_counts[month] += 1
            except ValueError:
                pass

    # Decade average ratings
    decade_avg = {}
    for decade, ratings in decade_ratings.items():
        if len(ratings) >= 3:
            decade_avg[decade] = round(sum(ratings) / len(ratings), 1)

    # Movies per viewing year
    movies_per_year = dict(sorted(viewing_year_counts.items()))

    # Peak viewing years
    peak_years = [y for y, _ in viewing_year_counts.most_common(3)]

    # Recency ratio
    total = len(records)
    post_2020 = sum(1 for r in records
                    if r.get("year") and str(r["year"]).isdigit()
                    and int(str(r["year"])) >= 2020)
    pre_2000 = sum(1 for r in records
                   if r.get("year") and str(r["year"]).isdigit()
                   and int(str(r["year"])) < 2000)
    recency_ratio = post_2020 / total if total else 0

    # Date range
    dates = sorted(r["my_date"] for r in records if r.get("my_date"))
    date_range = [dates[0], dates[-1]] if dates else []

    return {
        "decade_distribution": dict(sorted(decade_counts.items())),
        "decade_avg_rating": dict(sorted(decade_avg.items())),
        "viewing_year_distribution": movies_per_year,
        "viewing_monthly_pattern": dict(sorted(viewing_month_counts.items())),
        "movies_per_year": movies_per_year,
        "peak_years": peak_years,
        "recency_ratio": round(recency_ratio, 3),
        "post_2020_count": post_2020,
        "pre_2000_count": pre_2000,
        "date_range": date_range,
    }


# ------------------------------------------------------------------
# C. Genre Analysis
# ------------------------------------------------------------------

def compute_genre_stats(records: list[dict]) -> dict:
    """Category C: Genre analysis metrics."""
    genre_counts: Counter[str] = Counter()
    genre_ratings: dict[str, list[int]] = defaultdict(list)
    records_with_genre = 0

    for r in records:
        genres = r.get("genre")
        if not genres:
            continue
        records_with_genre += 1
        for g in genres:
            genre_counts[g] += 1
            if r["my_rating"] is not None:
                genre_ratings[g].append(r["my_rating"])

    # Genre diversity
    distinct_genres = len(genre_counts)

    # Top genres
    top_genres = genre_counts.most_common(15)

    # Genre average ratings
    genre_avg_rating = {}
    for g, ratings in genre_ratings.items():
        if len(ratings) >= 3:
            genre_avg_rating[g] = round(sum(ratings) / len(ratings), 1)

    # Genre cluster scores
    cluster_counts: Counter[str] = Counter()
    for g, count in genre_counts.items():
        cluster = genre_cluster(g)
        if cluster:
            cluster_counts[cluster] += count

    cluster_total = sum(cluster_counts.values())
    cluster_scores = {}
    if cluster_total > 0:
        for cluster in GENRE_CLUSTERS:
            cluster_scores[cluster] = round(
                cluster_counts[cluster] / cluster_total, 3
            )

    # Genre rating contrast: genres above/below personal mean
    all_ratings = [r["my_rating"] for r in records if r["my_rating"] is not None]
    personal_mean = sum(all_ratings) / len(all_ratings) if all_ratings else 0
    genre_above = []
    genre_below = []
    for g, avg in genre_avg_rating.items():
        if avg > personal_mean + 0.5:
            genre_above.append((g, avg))
        elif avg < personal_mean - 0.5:
            genre_below.append((g, avg))

    return {
        "genre_distribution": dict(genre_counts.most_common()),
        "genre_diversity": distinct_genres,
        "top_genres": top_genres,
        "genre_avg_rating": genre_avg_rating,
        "cluster_scores": cluster_scores,
        "genre_above_mean": sorted(genre_above, key=lambda x: -x[1]),
        "genre_below_mean": sorted(genre_below, key=lambda x: x[1]),
        "records_with_genre": records_with_genre,
    }


# ------------------------------------------------------------------
# D. Director Analysis
# ------------------------------------------------------------------

def compute_director_stats(records: list[dict]) -> dict:
    """Category D: Director analysis metrics."""
    director_counts: Counter[str] = Counter()
    director_ratings: dict[str, list[int]] = defaultdict(list)

    for r in records:
        directors = r.get("director")
        if not directors:
            continue
        for d in directors:
            director_counts[d] += 1
            if r["my_rating"] is not None:
                director_ratings[d].append(r["my_rating"])

    distinct_directors = len(director_counts)
    total_with_director = sum(1 for r in records if r.get("director"))

    # Top directors (3+ movies)
    top_directors = []
    for name, count in director_counts.most_common():
        if count < 3:
            break
        ratings = director_ratings[name]
        avg = round(sum(ratings) / len(ratings), 1) if ratings else 0
        top_directors.append((name, count, avg))

    # Repeat director ratio
    repeat_films = sum(c for c in director_counts.values() if c >= 2)
    repeat_ratio = repeat_films / total_with_director if total_with_director else 0

    # Director average ratings (for directors with 2+ movies)
    director_avg = {}
    for name, ratings in director_ratings.items():
        if len(ratings) >= 2:
            director_avg[name] = round(sum(ratings) / len(ratings), 1)

    return {
        "top_directors": top_directors,
        "distinct_count": distinct_directors,
        "repeat_director_ratio": round(repeat_ratio, 3),
        "director_avg_rating": director_avg,
        "total_with_director": total_with_director,
    }


# ------------------------------------------------------------------
# E. Geography & Culture
# ------------------------------------------------------------------

def compute_geography_stats(records: list[dict]) -> dict:
    """Category E: Geography & culture metrics."""
    country_counts: Counter[str] = Counter()
    country_ratings: dict[str, list[int]] = defaultdict(list)
    region_counts: Counter[str] = Counter()

    for r in records:
        countries = r.get("country")
        if not countries:
            continue
        for c in countries:
            country_counts[c] += 1
            if r["my_rating"] is not None:
                country_ratings[c].append(r["my_rating"])
            region = country_region(c)
            if region:
                region_counts[region] += 1

    distinct_countries = len(country_counts)
    total_with_country = sum(1 for r in records if r.get("country"))

    # Top countries
    top_countries = country_counts.most_common(10)

    # Country average ratings
    country_avg = {}
    for c, ratings in country_ratings.items():
        if len(ratings) >= 3:
            country_avg[c] = round(sum(ratings) / len(ratings), 1)

    # Domestic vs foreign
    domestic_count = country_counts.get("China", 0)
    domestic_ratio = domestic_count / total_with_country if total_with_country else 0

    # Region distribution
    region_total = sum(region_counts.values())
    region_scores = {}
    if region_total > 0:
        for region, count in region_counts.most_common():
            region_scores[region] = round(count / region_total, 3)

    return {
        "country_distribution": dict(country_counts.most_common()),
        "country_diversity": distinct_countries,
        "top_countries": top_countries,
        "country_avg_rating": country_avg,
        "domestic_ratio": round(domestic_ratio, 3),
        "region_scores": region_scores,
        "total_with_country": total_with_country,
    }


# ------------------------------------------------------------------
# F. Comment Overview
# ------------------------------------------------------------------

def compute_comment_stats(records: list[dict]) -> dict:
    """Category F: Comment overview metrics."""
    comments = [r["my_comment"] for r in records if r.get("my_comment")]
    total = len(records)
    comment_count = len(comments)
    comment_rate = comment_count / total if total else 0

    lengths = [len(c) for c in comments]
    avg_length = sum(lengths) / len(lengths) if lengths else 0

    # Length distribution
    buckets = {"short": 0, "medium": 0, "long": 0, "very_long": 0}
    for length in lengths:
        if length < 20:
            buckets["short"] += 1
        elif length < 50:
            buckets["medium"] += 1
        elif length < 100:
            buckets["long"] += 1
        else:
            buckets["very_long"] += 1

    # Comment-rating correlation: do extreme ratings get more comments?
    rated_with_comment = [r for r in records
                         if r.get("my_comment") and r["my_rating"] is not None]
    rated_without_comment = [r for r in records
                            if not r.get("my_comment") and r["my_rating"] is not None]
    avg_rating_with = (
        sum(r["my_rating"] for r in rated_with_comment) / len(rated_with_comment)
        if rated_with_comment else 0
    )
    avg_rating_without = (
        sum(r["my_rating"] for r in rated_without_comment) / len(rated_without_comment)
        if rated_without_comment else 0
    )

    return {
        "comment_count": comment_count,
        "comment_rate": round(comment_rate, 3),
        "avg_length": round(avg_length, 1),
        "length_distribution": buckets,
        "avg_rating_with_comment": round(avg_rating_with, 2),
        "avg_rating_without_comment": round(avg_rating_without, 2),
    }


# ------------------------------------------------------------------
# G. User vs. Crowd
# ------------------------------------------------------------------

def compute_crowd_comparison(records: list[dict]) -> dict:
    """Category G: User vs. crowd comparison metrics."""
    pairs = []
    for r in records:
        my = r["my_rating"]
        crowd = r.get("douban_rating")
        if my is not None and crowd is not None:
            # Douban user ratings are 2/4/6/8/10; crowd is float 0-10.
            # Use round(crowd * 2) / 2 ... no, design says use raw values.
            pairs.append((my, crowd))

    if not pairs:
        return {
            "rating_gap_mean": 0.0,
            "rating_gap_stddev": 0.0,
            "overrated_movies": [],
            "underrated_movies": [],
            "crowd_alignment_score": 0.0,
            "pair_count": 0,
        }

    gaps = [my - crowd for my, crowd in pairs]
    gap_mean = sum(gaps) / len(gaps)
    gap_var = sum((g - gap_mean) ** 2 for g in gaps) / len(gaps)
    gap_stddev = math.sqrt(gap_var)

    # Correlation (Pearson)
    my_vals = [p[0] for p in pairs]
    crowd_vals = [p[1] for p in pairs]
    my_mean = sum(my_vals) / len(my_vals)
    crowd_mean = sum(crowd_vals) / len(crowd_vals)
    numerator = sum((m - my_mean) * (c - crowd_mean) for m, c in pairs)
    denom_my = math.sqrt(sum((m - my_mean) ** 2 for m in my_vals))
    denom_crowd = math.sqrt(sum((c - crowd_mean) ** 2 for c in crowd_vals))
    correlation = (
        numerator / (denom_my * denom_crowd)
        if denom_my > 0 and denom_crowd > 0
        else 0
    )

    # Notable over/underrated
    overrated = []
    underrated = []
    for r in records:
        my = r["my_rating"]
        crowd = r.get("douban_rating")
        if my is None or crowd is None:
            continue
        gap = my - crowd
        if gap >= 4:
            overrated.append((r["title"], my, crowd, round(gap, 1)))
        elif gap <= -4:
            underrated.append((r["title"], my, crowd, round(gap, 1)))

    overrated.sort(key=lambda x: -x[3])
    underrated.sort(key=lambda x: x[3])

    return {
        "rating_gap_mean": round(gap_mean, 2),
        "rating_gap_stddev": round(gap_stddev, 2),
        "overrated_movies": overrated[:10],
        "underrated_movies": underrated[:10],
        "crowd_alignment_score": round(correlation, 3),
        "pair_count": len(pairs),
    }


# ------------------------------------------------------------------
# H. Viewing Habits
# ------------------------------------------------------------------

def compute_habit_stats(records: list[dict]) -> dict:
    """Category H: Viewing habit metrics."""
    durations = [r["duration"] for r in records
                 if r.get("duration") is not None and r["duration"] > 0]

    avg_duration = sum(durations) / len(durations) if durations else 0

    # Duration buckets
    buckets = {"short_lt90": 0, "standard_90_120": 0,
               "long_120_150": 0, "very_long_150plus": 0}
    for d in durations:
        if d < 90:
            buckets["short_lt90"] += 1
        elif d < 120:
            buckets["standard_90_120"] += 1
        elif d < 150:
            buckets["long_120_150"] += 1
        else:
            buckets["very_long_150plus"] += 1

    long_film_ratio = (
        buckets["very_long_150plus"] / len(durations) if durations else 0
    )

    # Binge sessions (days with 3+ movies)
    date_counts: Counter[str] = Counter()
    for r in records:
        if r.get("my_date"):
            date_counts[r["my_date"]] += 1
    binge_days = sum(1 for count in date_counts.values() if count >= 3)

    return {
        "avg_duration": round(avg_duration, 1),
        "duration_distribution": buckets,
        "long_film_ratio": round(long_film_ratio, 3),
        "binge_days": binge_days,
        "total_with_duration": len(durations),
    }
