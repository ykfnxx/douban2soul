"""
Static genre and country classification tables.

These mappings convert Chinese genre/country strings from wmdb/Douban into
English canonical names and personality-relevant clusters.  The vocabulary
is finite (~30 genres, ~40 countries) so a static dict is sufficient.

Unmapped values pass through as-is and are logged for future curation.
"""

import logging

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Genre: Chinese name -> English canonical name
# ------------------------------------------------------------------

GENRE_NAME_MAP: dict[str, str] = {
    "剧情": "Drama",
    "喜剧": "Comedy",
    "动作": "Action",
    "爱情": "Romance",
    "科幻": "Sci-Fi",
    "悬疑": "Mystery",
    "惊悚": "Thriller",
    "恐怖": "Horror",
    "犯罪": "Crime",
    "动画": "Animation",
    "冒险": "Adventure",
    "奇幻": "Fantasy",
    "纪录片": "Documentary",
    "战争": "War",
    "历史": "History",
    "传记": "Biography",
    "家庭": "Family",
    "音乐": "Musical",
    "歌舞": "Musical",
    "西部": "Western",
    "武侠": "Wuxia",
    "古装": "Period",
    "运动": "Sports",
    "短片": "Short",
    "儿童": "Children",
    "真人秀": "Reality",
    "情色": "Erotic",
    "同性": "LGBT",
    "灾难": "Disaster",
    "黑色电影": "Film-Noir",
}

# ------------------------------------------------------------------
# Genre: English name -> personality-relevant cluster
# ------------------------------------------------------------------

GENRE_CLUSTERS: dict[str, list[str]] = {
    "Intellectual": ["Documentary", "History", "Biography", "War"],
    "Mainstream Action": ["Action", "Adventure", "Sci-Fi", "Fantasy", "Disaster"],
    "Emotional Drama": ["Drama", "Romance", "Family"],
    "Thrill-seeking": ["Horror", "Thriller", "Crime", "Mystery", "Film-Noir"],
    "Light Entertainment": ["Comedy", "Animation", "Musical", "Children", "Sports"],
    "Artistic": ["Wuxia", "Period", "Western", "Short", "Erotic", "LGBT"],
}

# Reverse lookup: genre -> cluster name
_GENRE_TO_CLUSTER: dict[str, str] = {}
for _cluster, _genres in GENRE_CLUSTERS.items():
    for _g in _genres:
        _GENRE_TO_CLUSTER[_g] = _cluster

# ------------------------------------------------------------------
# Country: Chinese name -> English canonical name
# ------------------------------------------------------------------

COUNTRY_NAME_MAP: dict[str, str] = {
    "中国大陆": "China",
    "中国香港": "Hong Kong",
    "中国台湾": "Taiwan",
    "美国": "USA",
    "英国": "UK",
    "日本": "Japan",
    "韩国": "South Korea",
    "法国": "France",
    "德国": "Germany",
    "意大利": "Italy",
    "西班牙": "Spain",
    "俄罗斯": "Russia",
    "加拿大": "Canada",
    "澳大利亚": "Australia",
    "印度": "India",
    "泰国": "Thailand",
    "巴西": "Brazil",
    "墨西哥": "Mexico",
    "瑞典": "Sweden",
    "丹麦": "Denmark",
    "挪威": "Norway",
    "芬兰": "Finland",
    "荷兰": "Netherlands",
    "比利时": "Belgium",
    "瑞士": "Switzerland",
    "奥地利": "Austria",
    "波兰": "Poland",
    "捷克": "Czech Republic",
    "匈牙利": "Hungary",
    "爱尔兰": "Ireland",
    "新西兰": "New Zealand",
    "阿根廷": "Argentina",
    "土耳其": "Turkey",
    "伊朗": "Iran",
    "以色列": "Israel",
    "南非": "South Africa",
    "马来西亚": "Malaysia",
    "新加坡": "Singapore",
    "菲律宾": "Philippines",
    "印度尼西亚": "Indonesia",
    "越南": "Vietnam",
    "哥伦比亚": "Colombia",
    "智利": "Chile",
    "罗马尼亚": "Romania",
    "希腊": "Greece",
    "葡萄牙": "Portugal",
    "苏联": "Soviet Union",
}

# ------------------------------------------------------------------
# Country region grouping
# ------------------------------------------------------------------

COUNTRY_REGIONS: dict[str, list[str]] = {
    "Domestic": ["China"],
    "Greater China": ["Hong Kong", "Taiwan"],
    "East Asia": ["Japan", "South Korea"],
    "Southeast Asia": ["Thailand", "Malaysia", "Singapore", "Philippines",
                       "Indonesia", "Vietnam"],
    "South Asia": ["India"],
    "North America": ["USA", "Canada"],
    "Western Europe": ["UK", "France", "Germany", "Italy", "Spain",
                       "Netherlands", "Belgium", "Switzerland", "Austria",
                       "Ireland", "Portugal"],
    "Northern Europe": ["Sweden", "Denmark", "Norway", "Finland"],
    "Eastern Europe": ["Russia", "Poland", "Czech Republic", "Hungary",
                       "Romania", "Soviet Union", "Greece"],
    "Oceania": ["Australia", "New Zealand"],
    "Latin America": ["Brazil", "Mexico", "Argentina", "Colombia", "Chile"],
    "Middle East": ["Turkey", "Iran", "Israel"],
    "Africa": ["South Africa"],
}

_COUNTRY_TO_REGION: dict[str, str] = {}
for _region, _countries in COUNTRY_REGIONS.items():
    for _c in _countries:
        _COUNTRY_TO_REGION[_c] = _region


# ------------------------------------------------------------------
# Public helpers
# ------------------------------------------------------------------

_warned_genres: set[str] = set()
_warned_countries: set[str] = set()


def normalize_genre(raw: str) -> str:
    """Map a raw genre string to its English canonical name."""
    mapped = GENRE_NAME_MAP.get(raw)
    if mapped is not None:
        return mapped
    # Already in English or unmapped — pass through.
    if raw not in _warned_genres:
        _warned_genres.add(raw)
        logger.debug("Unmapped genre: %r (passing through as-is)", raw)
    return raw


def genre_cluster(english_genre: str) -> str | None:
    """Return the personality cluster for an English genre name, or None."""
    return _GENRE_TO_CLUSTER.get(english_genre)


def normalize_country(raw: str) -> str:
    """Map a raw country string to its English canonical name."""
    mapped = COUNTRY_NAME_MAP.get(raw)
    if mapped is not None:
        return mapped
    if raw not in _warned_countries:
        _warned_countries.add(raw)
        logger.debug("Unmapped country: %r (passing through as-is)", raw)
    return raw


def country_region(english_country: str) -> str | None:
    """Return the region group for an English country name, or None."""
    return _COUNTRY_TO_REGION.get(english_country)
