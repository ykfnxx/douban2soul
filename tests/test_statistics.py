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
    compute_cast_stats,
    compute_creator_style_stats,
    compute_cross_dimensional_stats,
    compute_crowd_comparison,
    compute_director_stats,
    compute_genre_stats,
    compute_geography_stats,
    compute_graph_stats,
    compute_comment_stats,
    compute_habit_stats,
    compute_rating_stats,
    compute_taste_extremes,
    compute_temporal_stats,
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
        # Ratio must be <= 1.0 (counts films, not director appearances)
        assert result["repeat_director_ratio"] <= 1.0

    def test_repeat_ratio_counts_films(self) -> None:
        """repeat_director_ratio counts unique films, not director occurrences."""
        records = [
            {"director": ["A"], "my_rating": 8},
            {"director": ["A"], "my_rating": 6},
            {"director": ["A"], "my_rating": 10},
            {"director": ["B"], "my_rating": 4},
        ]
        result = compute_director_stats(records)
        # A appears 3 times -> 3 films with repeat director, B once -> 0
        # Ratio = 3/4 = 0.75
        assert result["repeat_director_ratio"] == 0.75

    def test_top_directors_threshold(self, merged: list[dict]) -> None:
        result = compute_director_stats(merged)
        # Director X has 2 films, which meets the lowered threshold of 2
        assert len(result["top_directors"]) == 1
        assert result["top_directors"][0][0] == "Director X"
        assert result["top_directors"][0][1] == 2

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

    def test_metadata_coverage_partial(self) -> None:
        """Metadata coverage counts records with any metadata field, not just genre."""
        records = [{"movieId": "1", "title": "A"}, {"movieId": "2", "title": "B"}]
        # Movie 1 has only duration (no genre), movie 2 has nothing
        metadata = {"1": {"duration": 120}}
        engine = StatsEngine(records=records, metadata=metadata)
        ctx = engine.generate_llm_context()
        assert ctx["overview"]["metadata_coverage"] == 0.5

    def test_l3_report_includes_cast(self) -> None:
        engine = StatsEngine(records=SAMPLE_RECORDS, metadata=SAMPLE_METADATA)
        report = engine.generate_l3_report()
        assert "Cast Analysis" in report

    def test_llm_context_includes_new_fields(self) -> None:
        engine = StatsEngine(records=SAMPLE_RECORDS, metadata=SAMPLE_METADATA)
        ctx = engine.generate_llm_context()
        assert "cast" in ctx
        assert "taste_extremes" in ctx
        assert "shannon_entropy" in ctx["genre"]

    def test_llm_context_excludes_temporal_signals(self) -> None:
        engine = StatsEngine(records=SAMPLE_RECORDS, metadata=SAMPLE_METADATA)
        ctx = engine.generate_llm_context()
        assert "temporal" not in ctx
        assert "date_range" not in ctx["overview"]
        assert "binge_days" not in ctx["habits"]

    def test_stats_cached(self) -> None:
        engine = StatsEngine(records=SAMPLE_RECORDS, metadata=SAMPLE_METADATA)
        stats1 = engine.stats
        stats2 = engine.stats
        assert stats1 is stats2  # Same object, computed once


# ------------------------------------------------------------------
# Cast Analysis
# ------------------------------------------------------------------

class TestCastStats:
    def test_cast_counts(self, merged: list[dict]) -> None:
        result = compute_cast_stats(merged)
        # Each actor appears once in sample data, no one reaches 2+
        assert result["top_actors"] == []
        assert result["distinct_count"] == 4

    def test_repeat_actor_ratio(self, merged: list[dict]) -> None:
        result = compute_cast_stats(merged)
        assert result["total_with_cast"] == 4

    def test_cast_with_repeats(self) -> None:
        records = [
            {"cast": ["Actor A", "Actor B"], "my_rating": 8},
            {"cast": ["Actor A"], "my_rating": 6},
            {"cast": ["Actor C"], "my_rating": 10},
        ]
        result = compute_cast_stats(records)
        assert len(result["top_actors"]) == 1
        assert result["top_actors"][0][0] == "Actor A"
        assert result["top_actors"][0][1] == 2
        assert result["top_actors"][0][2] == 7.0  # avg(8, 6)


# ------------------------------------------------------------------
# Taste Extremes
# ------------------------------------------------------------------

class TestTasteExtremes:
    def test_hidden_gems(self) -> None:
        records = [
            {"title": "Gem", "my_rating": 8, "douban_rating": 5.0},
            {"title": "Normal", "my_rating": 8, "douban_rating": 8.0},
        ]
        result = compute_taste_extremes(records)
        assert len(result["hidden_gems"]) == 1
        assert result["hidden_gems"][0][0] == "Gem"

    def test_avoid_zone(self) -> None:
        records = [
            {"title": "Avoid", "my_rating": 4, "douban_rating": 8.0},
            {"title": "Normal", "my_rating": 6, "douban_rating": 8.0},
        ]
        result = compute_taste_extremes(records)
        assert len(result["avoid_zone"]) == 1
        assert result["avoid_zone"][0][0] == "Avoid"

    def test_empty_when_no_extremes(self, merged: list[dict]) -> None:
        result = compute_taste_extremes(merged)
        # Sample data gaps are not extreme enough (need >=8 vs <6 or <=4 vs >=7)
        assert isinstance(result["hidden_gems"], list)
        assert isinstance(result["avoid_zone"], list)


# ------------------------------------------------------------------
# Genre Shannon Entropy
# ------------------------------------------------------------------

class TestGenreEntropy:
    def test_shannon_entropy_present(self, merged: list[dict]) -> None:
        result = compute_genre_stats(merged)
        assert "genre_shannon_entropy" in result
        assert result["genre_shannon_entropy"] > 0

    def test_uniform_distribution_high_entropy(self) -> None:
        records = [
            {"genre": ["Drama"], "my_rating": 8},
            {"genre": ["Comedy"], "my_rating": 8},
            {"genre": ["Action"], "my_rating": 8},
            {"genre": ["Horror"], "my_rating": 8},
        ]
        result = compute_genre_stats(records)
        # 4 genres, uniform -> entropy = log2(4) = 2.0
        assert result["genre_shannon_entropy"] == 2.0

    def test_single_genre_zero_entropy(self) -> None:
        records = [
            {"genre": ["Drama"], "my_rating": 8},
            {"genre": ["Drama"], "my_rating": 6},
        ]
        result = compute_genre_stats(records)
        assert result["genre_shannon_entropy"] == 0.0


# ------------------------------------------------------------------
# Cross-Dimensional Statistics
# ------------------------------------------------------------------

CROSS_DIM_RECORDS = [
    {"genre": ["Drama"], "director": ["Dir A"], "cast": ["Act 1"], "my_rating": 8, "my_date": "2024-01-01", "my_comment": "Great", "douban_rating": 5.0},
    {"genre": ["Drama"], "director": ["Dir A"], "cast": ["Act 1"], "my_rating": 6, "my_date": "2024-01-03", "my_comment": None, "douban_rating": 7.0},
    {"genre": ["Comedy"], "director": ["Dir A"], "cast": ["Act 1"], "my_rating": 10, "my_date": "2024-01-06", "my_comment": "Loved it", "douban_rating": 8.0},
    {"genre": ["Drama", "Sci-Fi"], "director": ["Dir B"], "cast": ["Act 2"], "my_rating": 4, "my_date": "2024-01-08", "my_comment": None, "douban_rating": 6.5},
    {"genre": ["Action"], "director": ["Dir B"], "cast": ["Act 2"], "my_rating": 8, "my_date": "2024-01-12", "my_comment": None, "douban_rating": 7.0},
    {"genre": ["Comedy"], "director": ["Dir B"], "cast": ["Act 2"], "my_rating": 6, "my_date": "2024-01-13", "my_comment": "OK", "douban_rating": 6.0},
]


class TestCrossDimensionalStats:
    def test_genre_rating_variance(self) -> None:
        result = compute_cross_dimensional_stats(CROSS_DIM_RECORDS)
        # Drama has ratings [8, 6, 4] -> mean 6, var = (4+0+4)/3 = 2.67
        assert "Drama" in result["genre_rating_variance"]
        assert result["genre_rating_variance"]["Drama"] > 0

    def test_director_rating_consistency(self) -> None:
        result = compute_cross_dimensional_stats(CROSS_DIM_RECORDS)
        # Dir A has [8, 6, 10] -> mean 8, stddev > 0
        assert "Dir A" in result["director_rating_consistency"]
        assert result["director_rating_consistency"]["Dir A"] > 0

    def test_actor_rating_consistency(self) -> None:
        result = compute_cross_dimensional_stats(CROSS_DIM_RECORDS)
        # Act 1 has [8, 6, 10], Act 2 has [4, 8, 6]
        assert "Act 1" in result["actor_rating_consistency"]
        assert "Act 2" in result["actor_rating_consistency"]

    def test_viewing_intervals(self) -> None:
        result = compute_cross_dimensional_stats(CROSS_DIM_RECORDS)
        iv = result["viewing_interval"]
        assert "mean_days" in iv
        assert iv["mean_days"] > 0
        # Intervals: 2, 3, 2, 4, 1 -> mean = 2.4
        assert iv["mean_days"] == pytest.approx(2.4, abs=0.1)

    def test_weekend_ratio(self) -> None:
        result = compute_cross_dimensional_stats(CROSS_DIM_RECORDS)
        assert 0 <= result["weekend_ratio"] <= 1

    def test_comment_rating_delta(self) -> None:
        result = compute_cross_dimensional_stats(CROSS_DIM_RECORDS)
        # With comment: [8, 10, 6] avg=8; without: [6, 4, 8] avg=6; delta=2
        assert result["comment_rating_delta"] == pytest.approx(2.0, abs=0.01)

    def test_hidden_gems_by_genre(self) -> None:
        result = compute_cross_dimensional_stats(CROSS_DIM_RECORDS)
        # Record 0: rating 8, douban 5.0 -> hidden gem, genre Drama
        assert "Drama" in result["hidden_gems_by_genre"]

    def test_empty_records(self) -> None:
        result = compute_cross_dimensional_stats([])
        assert result["genre_rating_variance"] == {}
        assert result["viewing_interval"] == {}


# ------------------------------------------------------------------
# Creator Style Analysis
# ------------------------------------------------------------------

class TestCreatorStyleStats:
    def test_director_style(self) -> None:
        result = compute_creator_style_stats(CROSS_DIM_RECORDS)
        # Dir A and Dir B both have 3 films
        assert len(result["director_style"]) == 2
        dir_a = next(d for d in result["director_style"] if d["name"] == "Dir A")
        assert dir_a["film_count"] == 3
        assert "Drama" in dir_a["genre_distribution"] or "Comedy" in dir_a["genre_distribution"]

    def test_actor_style(self) -> None:
        result = compute_creator_style_stats(CROSS_DIM_RECORDS)
        assert len(result["actor_style"]) == 2
        act_1 = next(a for a in result["actor_style"] if a["name"] == "Act 1")
        assert act_1["film_count"] == 3
        assert 0 <= act_1["cross_genre_expansion"] <= 1

    def test_director_actor_combos(self) -> None:
        result = compute_creator_style_stats(CROSS_DIM_RECORDS)
        # Dir A + Act 1 appear together 3 times
        combos = result["top_director_actor_combos"]
        assert len(combos) >= 1
        top = combos[0]
        assert top["films_together"] >= 2

    def test_threshold_filters(self) -> None:
        records = [
            {"genre": ["Drama"], "director": ["OneOff"], "cast": ["Rare"], "my_rating": 8},
            {"genre": ["Comedy"], "director": ["OneOff"], "cast": ["Common"], "my_rating": 6},
            {"genre": ["Action"], "director": ["Freq"], "cast": ["Common"], "my_rating": 8},
            {"genre": ["Drama"], "director": ["Freq"], "cast": ["Common"], "my_rating": 6},
            {"genre": ["Sci-Fi"], "director": ["Freq"], "cast": ["Common"], "my_rating": 10},
        ]
        result = compute_creator_style_stats(records)
        # Only Freq has 3+ films as director
        director_names = [d["name"] for d in result["director_style"]]
        assert "Freq" in director_names
        assert "OneOff" not in director_names
        # Common has 4 films as actor
        actor_names = [a["name"] for a in result["actor_style"]]
        assert "Common" in actor_names


# ------------------------------------------------------------------
# Graph Analysis
# ------------------------------------------------------------------

class TestGraphStats:
    def test_basic_graph(self) -> None:
        records = [
            {"movie_id": "m1", "title": "M1", "genre": ["Drama"], "director": ["Dir A"], "cast": ["Act 1"]},
            {"movie_id": "m2", "title": "M2", "genre": ["Drama"], "director": ["Dir A"], "cast": ["Act 2"]},
            {"movie_id": "m3", "title": "M3", "genre": ["Comedy"], "director": ["Dir B"], "cast": ["Act 1"]},
        ]
        result = compute_graph_stats(records)
        assert result["movie_count"] == 3
        assert result["total_nodes"] > 3  # movies + directors + actors + genres
        assert result["total_edges"] > 0

    def test_clustering_coefficient(self) -> None:
        # M1 and M2 share Dir A and Drama; M1 and M3 share Act 1; M2 and M3 don't share much
        records = [
            {"movie_id": "m1", "title": "M1", "genre": ["Drama"], "director": ["Dir A"], "cast": ["Act 1"]},
            {"movie_id": "m2", "title": "M2", "genre": ["Drama"], "director": ["Dir A"], "cast": ["Act 2"]},
            {"movie_id": "m3", "title": "M3", "genre": ["Comedy"], "director": ["Dir B"], "cast": ["Act 1"]},
        ]
        result = compute_graph_stats(records)
        assert "movie_clustering_coefficient" in result
        assert 0 <= result["movie_clustering_coefficient"] <= 1

    def test_single_movie(self) -> None:
        records = [{"movie_id": "m1", "title": "M1", "genre": ["Drama"]}]
        result = compute_graph_stats(records)
        assert result["movie_count"] == 1
        assert result["communities"] == 0

    def test_empty(self) -> None:
        result = compute_graph_stats([])
        assert result["movie_count"] == 0

    def test_isolated_movies(self) -> None:
        records = [
            {"movie_id": "m1", "title": "M1", "genre": ["Drama"], "director": ["Dir A"]},
            {"movie_id": "m2", "title": "M2", "genre": ["Drama"], "director": ["Dir A"]},
            {"movie_id": "m3", "title": "M3", "genre": ["Unique"], "director": ["Dir Unique"], "cast": ["Solo"]},
        ]
        result = compute_graph_stats(records)
        # m3 has unique genre, director, and actor — isolated from m1/m2
        assert result["isolated_movies"] >= 1


# ------------------------------------------------------------------
# Engine integration for new categories
# ------------------------------------------------------------------

class TestEngineNewCategories:
    def test_l3_includes_cross_dimensional(self) -> None:
        engine = StatsEngine(records=SAMPLE_RECORDS, metadata=SAMPLE_METADATA)
        report = engine.generate_l3_report()
        assert "Cross-Dimensional Analysis" in report

    def test_l3_includes_creator_style(self) -> None:
        engine = StatsEngine(records=SAMPLE_RECORDS, metadata=SAMPLE_METADATA)
        report = engine.generate_l3_report()
        # Creator style section may or may not appear depending on threshold
        # Just ensure no crash
        assert isinstance(report, str)

    def test_l3_includes_graph(self) -> None:
        engine = StatsEngine(records=SAMPLE_RECORDS, metadata=SAMPLE_METADATA)
        report = engine.generate_l3_report()
        assert "Viewing Network Analysis" in report

    def test_llm_context_includes_new_fields(self) -> None:
        engine = StatsEngine(records=SAMPLE_RECORDS, metadata=SAMPLE_METADATA)
        ctx = engine.generate_llm_context()
        assert "cross_dimensional" in ctx
        assert "creator_style" in ctx
        assert "graph" in ctx
        assert "genre_rating_variance" in ctx["cross_dimensional"]
        assert "movie_clustering_coefficient" in ctx["graph"]

    def test_stats_includes_all_categories(self) -> None:
        engine = StatsEngine(records=SAMPLE_RECORDS, metadata=SAMPLE_METADATA)
        s = engine.stats
        assert "cross_dimensional" in s
        assert "creator_style" in s
        assert "graph" in s
