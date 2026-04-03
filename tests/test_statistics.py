"""Tests for the statistics module."""

import pytest

from douban2soul.statistics.taxonomy import (
    normalize_genre,
    normalize_country,
    genre_cluster,
    country_region,
)
from douban2soul.statistics.merge import merge_records_with_metadata
from douban2soul.statistics.categories import (
    compute_rating_stats,
    compute_temporal_stats,
    compute_genre_stats,
    compute_director_stats,
    compute_geography_stats,
    compute_comment_stats,
    compute_crowd_comparison,
    compute_habit_stats,
)
from douban2soul.statistics.engine import StatsEngine


# ------------------------------------------------------------------
# Sample data
# ------------------------------------------------------------------

SAMPLE_RECORDS = [
    {
        "movieId": "1",
        "title": "Movie A",
        "year": "2023",
        "myRating": 8,
        "myComment": "Great movie, loved it!",
        "myDate": "2024-01-15",
        "myStatus": "collect",
    },
    {
        "movieId": "2",
        "title": "Movie B",
        "year": "2019",
        "myRating": 6,
        "myComment": None,
        "myDate": "2024-02-20",
        "myStatus": "collect",
    },
    {
        "movieId": "3",
        "title": "Movie C",
        "year": "1995",
        "myRating": 10,
        "myComment": "A masterpiece that changed cinema forever, absolutely stunning visuals and story",
        "myDate": "2024-01-15",
        "myStatus": "collect",
    },
    {
        "movieId": "4",
        "title": "Movie D",
        "year": "2023",
        "myRating": 4,
        "myComment": "Meh",
        "myDate": "2024-03-10",
        "myStatus": "collect",
    },
    {
        "movieId": "5",
        "title": "Movie E",
        "year": "2020",
        "myRating": None,
        "myComment": None,
        "myDate": "2024-01-15",
        "myStatus": "collect",
    },
]

SAMPLE_METADATA = {
    "1": {
        "genre": ["Drama", "Sci-Fi"],
        "director": ["Director X"],
        "cast": ["Actor 1"],
        "country": "USA",
        "duration": 148,
        "douban_rating": 8.5,
    },
    "2": {
        "genre": ["Comedy", "Romance"],
        "director": ["Director Y"],
        "cast": ["Actor 2"],
        "country": "France",
        "duration": 95,
        "douban_rating": 7.2,
    },
    "3": {
        "genre": ["Drama", "Thriller"],
        "director": ["Director X"],
        "cast": ["Actor 3"],
        "country": "USA",
        "duration": 165,
        "douban_rating": 9.1,
    },
    "4": {
        "genre": ["Action", "Adventure"],
        "director": ["Director Z"],
        "cast": ["Actor 4"],
        "country": "中国大陆",
        "duration": 110,
        "douban_rating": 5.5,
    },
}


@pytest.fixture()
def merged() -> list[dict]:
    return merge_records_with_metadata(SAMPLE_RECORDS, SAMPLE_METADATA)


# ------------------------------------------------------------------
# Taxonomy
# ------------------------------------------------------------------

class TestTaxonomy:
    def test_genre_chinese_to_english(self) -> None:
        assert normalize_genre("剧情") == "Drama"
        assert normalize_genre("喜剧") == "Comedy"
        assert normalize_genre("科幻") == "Sci-Fi"

    def test_genre_passthrough(self) -> None:
        assert normalize_genre("Drama") == "Drama"
        assert normalize_genre("UnknownGenre") == "UnknownGenre"

    def test_genre_cluster(self) -> None:
        assert genre_cluster("Drama") == "Emotional Drama"
        assert genre_cluster("Horror") == "Thrill-seeking"
        assert genre_cluster("Documentary") == "Intellectual"
        assert genre_cluster("UnknownGenre") is None

    def test_country_chinese_to_english(self) -> None:
        assert normalize_country("美国") == "USA"
        assert normalize_country("中国大陆") == "China"
        assert normalize_country("日本") == "Japan"

    def test_country_passthrough(self) -> None:
        assert normalize_country("USA") == "USA"

    def test_country_region(self) -> None:
        assert country_region("USA") == "North America"
        assert country_region("China") == "Domestic"
        assert country_region("Japan") == "East Asia"
        assert country_region("UnknownCountry") is None


# ------------------------------------------------------------------
# Merge
# ------------------------------------------------------------------

class TestMerge:
    def test_merge_basic(self, merged: list[dict]) -> None:
        assert len(merged) == 5
        assert merged[0]["movie_id"] == "1"
        assert merged[0]["title"] == "Movie A"

    def test_merge_metadata_present(self, merged: list[dict]) -> None:
        # Movie 1 has metadata
        assert merged[0]["genre"] == ["Drama", "Sci-Fi"]
        assert merged[0]["director"] == ["Director X"]
        assert merged[0]["duration"] == 148
        assert merged[0]["douban_rating"] == 8.5

    def test_merge_metadata_missing(self, merged: list[dict]) -> None:
        # Movie 5 has no metadata
        assert merged[4]["genre"] is None
        assert merged[4]["director"] is None
        assert merged[4]["duration"] is None

    def test_merge_country_normalization(self, merged: list[dict]) -> None:
        # Movie 4 has Chinese country name
        assert merged[3]["country"] == ["China"]

    def test_merge_country_slash_split(self) -> None:
        records = [{"movieId": "x", "title": "X"}]
        metadata = {"x": {"country": "美国 / 英国"}}
        merged = merge_records_with_metadata(records, metadata)
        assert merged[0]["country"] == ["USA", "UK"]

    def test_merge_no_metadata(self) -> None:
        merged = merge_records_with_metadata(SAMPLE_RECORDS, None)
        assert len(merged) == 5
        assert all(r["genre"] is None for r in merged)


# ------------------------------------------------------------------
# Category A: Rating
# ------------------------------------------------------------------

class TestRatingStats:
    def test_basic(self, merged: list[dict]) -> None:
        result = compute_rating_stats(merged)
        assert result["rated_count"] == 4
        assert result["total_count"] == 5
        assert result["mean"] == 7.0  # (8+6+10+4)/4
        assert result["median"] in (6, 8)  # sorted: [4,6,8,10], mid=8
        assert result["stddev"] > 0

    def test_distribution(self, merged: list[dict]) -> None:
        result = compute_rating_stats(merged)
        assert result["distribution"][8] == 1
        assert result["distribution"][10] == 1

    def test_empty(self) -> None:
        result = compute_rating_stats([])
        assert result["rated_count"] == 0
        assert result["mean"] == 0.0


# ------------------------------------------------------------------
# Category B: Temporal
# ------------------------------------------------------------------

class TestTemporalStats:
    def test_decade_distribution(self, merged: list[dict]) -> None:
        result = compute_temporal_stats(merged)
        assert "2020s" in result["decade_distribution"]
        assert "1990s" in result["decade_distribution"]

    def test_recency_ratio(self, merged: list[dict]) -> None:
        result = compute_temporal_stats(merged)
        # 3 movies are 2020+: 2023x2, 2020x1 out of 5
        assert result["recency_ratio"] == 0.6

    def test_date_range(self, merged: list[dict]) -> None:
        result = compute_temporal_stats(merged)
        assert result["date_range"][0] == "2024-01-15"
        assert result["date_range"][1] == "2024-03-10"


# ------------------------------------------------------------------
# Category C: Genre
# ------------------------------------------------------------------

class TestGenreStats:
    def test_genre_distribution(self, merged: list[dict]) -> None:
        result = compute_genre_stats(merged)
        assert result["genre_distribution"]["Drama"] == 2
        assert result["records_with_genre"] == 4

    def test_genre_diversity(self, merged: list[dict]) -> None:
        result = compute_genre_stats(merged)
        # Drama, Sci-Fi, Comedy, Romance, Thriller, Action, Adventure
        assert result["genre_diversity"] == 7

    def test_cluster_scores(self, merged: list[dict]) -> None:
        result = compute_genre_stats(merged)
        assert "Emotional Drama" in result["cluster_scores"]
        assert "Mainstream Action" in result["cluster_scores"]
        assert sum(result["cluster_scores"].values()) == pytest.approx(1.0, abs=0.01)


# ------------------------------------------------------------------
# Category D: Director
# ------------------------------------------------------------------

class TestDirectorStats:
    def test_repeat_director(self, merged: list[dict]) -> None:
        result = compute_director_stats(merged)
        # Director X appears twice
        assert result["distinct_count"] == 3
        assert result["repeat_director_ratio"] > 0

    def test_top_directors_threshold(self, merged: list[dict]) -> None:
        result = compute_director_stats(merged)
        # No director has 3+ films, so top_directors should be empty
        assert result["top_directors"] == []

    def test_director_avg_rating(self, merged: list[dict]) -> None:
        result = compute_director_stats(merged)
        # Director X: ratings 8, 10 -> avg 9.0
        assert result["director_avg_rating"]["Director X"] == 9.0


# ------------------------------------------------------------------
# Category E: Geography
# ------------------------------------------------------------------

class TestGeographyStats:
    def test_country_distribution(self, merged: list[dict]) -> None:
        result = compute_geography_stats(merged)
        assert result["country_distribution"]["USA"] == 2

    def test_domestic_ratio(self, merged: list[dict]) -> None:
        result = compute_geography_stats(merged)
        # 1 out of 4 with country is China
        assert result["domestic_ratio"] == 0.25

    def test_region_scores(self, merged: list[dict]) -> None:
        result = compute_geography_stats(merged)
        assert "North America" in result["region_scores"]
        assert "Domestic" in result["region_scores"]


# ------------------------------------------------------------------
# Category F: Comments
# ------------------------------------------------------------------

class TestCommentStats:
    def test_comment_count(self, merged: list[dict]) -> None:
        result = compute_comment_stats(merged)
        assert result["comment_count"] == 3  # A, C, D have comments
        assert result["comment_rate"] == 0.6

    def test_avg_length(self, merged: list[dict]) -> None:
        result = compute_comment_stats(merged)
        assert result["avg_length"] > 0

    def test_length_distribution(self, merged: list[dict]) -> None:
        result = compute_comment_stats(merged)
        total = sum(result["length_distribution"].values())
        assert total == 3


# ------------------------------------------------------------------
# Category G: User vs. Crowd
# ------------------------------------------------------------------

class TestCrowdComparison:
    def test_gap_mean(self, merged: list[dict]) -> None:
        result = compute_crowd_comparison(merged)
        # Movie 1: 8 - 8.5 = -0.5
        # Movie 2: 6 - 7.2 = -1.2
        # Movie 3: 10 - 9.1 = 0.9
        # Movie 4: 4 - 5.5 = -1.5
        assert result["pair_count"] == 4
        expected_mean = (-0.5 + -1.2 + 0.9 + -1.5) / 4
        assert result["rating_gap_mean"] == pytest.approx(expected_mean, abs=0.01)

    def test_correlation(self, merged: list[dict]) -> None:
        result = compute_crowd_comparison(merged)
        # Both should roughly correlate positively
        assert result["crowd_alignment_score"] > 0

    def test_no_pairs(self) -> None:
        records = [{"my_rating": 8, "douban_rating": None, "title": "X"}]
        result = compute_crowd_comparison(records)
        assert result["pair_count"] == 0


# ------------------------------------------------------------------
# Category H: Habits
# ------------------------------------------------------------------

class TestHabitStats:
    def test_avg_duration(self, merged: list[dict]) -> None:
        result = compute_habit_stats(merged)
        # 148, 95, 165, 110 -> avg 129.5
        assert result["avg_duration"] == 129.5
        assert result["total_with_duration"] == 4

    def test_long_film_ratio(self, merged: list[dict]) -> None:
        result = compute_habit_stats(merged)
        # 1 film >= 150 out of 4
        assert result["long_film_ratio"] == 0.25

    def test_binge_days(self, merged: list[dict]) -> None:
        result = compute_habit_stats(merged)
        # 2024-01-15 has 3 movies (A, C, E)
        assert result["binge_days"] == 1


# ------------------------------------------------------------------
# StatsEngine integration
# ------------------------------------------------------------------

class TestStatsEngine:
    def test_l1_report(self) -> None:
        engine = StatsEngine(records=SAMPLE_RECORDS, metadata=SAMPLE_METADATA)
        report = engine.generate_l1_report()
        assert "# L1: Base Statistics Report" in report
        assert "Total Movies" in report
        assert "Rating Distribution" in report

    def test_l3_report(self) -> None:
        engine = StatsEngine(records=SAMPLE_RECORDS, metadata=SAMPLE_METADATA)
        report = engine.generate_l3_report()
        assert "# L3: Dimensional Deep Analysis" in report
        assert "Genre Profile" in report
        assert "Director Profile" in report
        assert "Cultural Profile" in report

    def test_llm_context(self) -> None:
        engine = StatsEngine(records=SAMPLE_RECORDS, metadata=SAMPLE_METADATA)
        ctx = engine.generate_llm_context()
        assert ctx["overview"]["total_movies"] == 5
        assert ctx["rating"]["mean"] == 7.0
        assert "cluster_scores" in ctx["genre"]
        assert "top_directors" in ctx["director"]
        assert "region_scores" in ctx["geography"]

    def test_backward_compat_base_stats(self) -> None:
        engine = StatsEngine()
        report = engine.generate_base_stats(SAMPLE_RECORDS)
        assert "# L1: Base Statistics Report" in report

    def test_backward_compat_dimension_analysis(self) -> None:
        engine = StatsEngine()
        report = engine.generate_dimension_analysis(SAMPLE_RECORDS)
        assert "# L3: Dimensional Deep Analysis" in report

    def test_no_metadata(self) -> None:
        engine = StatsEngine(records=SAMPLE_RECORDS, metadata=None)
        report = engine.generate_l1_report()
        assert "Metadata Coverage**: 0 (0.0%)" in report

    def test_stats_cached(self) -> None:
        engine = StatsEngine(records=SAMPLE_RECORDS, metadata=SAMPLE_METADATA)
        stats1 = engine.stats
        stats2 = engine.stats
        assert stats1 is stats2  # Same object, computed once
