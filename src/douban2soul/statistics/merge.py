"""
Merge viewing records with scraped metadata into a unified structure.

Each merged record combines user-level fields (title, rating, comment, date)
with metadata fields (genre, director, cast, country, duration, douban_rating).
"""

from douban2soul.statistics.taxonomy import normalize_country, normalize_genre


def merge_records_with_metadata(
    records: list[dict],
    metadata: dict[str, dict] | None,
) -> list[dict]:
    """
    Join viewing records with scraped metadata by movieId.

    Returns a list of merged dicts.  Fields from metadata are added
    directly; missing metadata results in None values.
    """
    metadata = metadata or {}

    merged: list[dict] = []
    for rec in records:
        movie_id = rec.get("movieId", "")
        meta = metadata.get(movie_id, {})

        # Normalize genres
        raw_genres = meta.get("genre")
        genres: list[str] | None = None
        if raw_genres and isinstance(raw_genres, list):
            genres = [normalize_genre(g) for g in raw_genres]

        # Normalize country — wmdb returns a single string, sometimes with " / "
        raw_country = meta.get("country")
        countries: list[str] | None = None
        if raw_country and isinstance(raw_country, str):
            countries = [normalize_country(c.strip()) for c in raw_country.split("/")]
        elif raw_country and isinstance(raw_country, list):
            countries = [normalize_country(c) for c in raw_country]

        merged.append({
            # From viewing records
            "movie_id": movie_id,
            "title": rec.get("title", ""),
            "year": rec.get("year"),
            "my_rating": rec.get("myRating"),
            "my_comment": rec.get("myComment"),
            "my_date": rec.get("myDate"),
            "my_status": rec.get("myStatus"),
            # From metadata
            "genre": genres,
            "director": meta.get("director"),
            "cast": meta.get("cast"),
            "country": countries,
            "duration": meta.get("duration"),
            "douban_rating": meta.get("douban_rating"),
        })

    return merged
