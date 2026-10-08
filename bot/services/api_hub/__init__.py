"""Public API Hub facade for ALIMJ3."""
from .api_hub import APIHub, api_hub
from .api_hub_registry import APIProvider, get_provider, list_providers
from .api_hub_runtime import (
    api_call, get_weather, get_exchange_rate, get_country, search_books, get_random_joke,
    search_products, geocode, reverse_geocode, smart_api_query,
)


async def movie_tv_intelligence(query: str, content_type: str = "movie", limit: int = 10):
    """Keyless movie/TV lookup using the registered IMDb suggestion provider."""
    q = (query or "").strip()
    limit = max(1, min(int(limit or 10), 20))
    if not q:
        return {"movies": [], "series": []}
    raw = await api_hub.call("imdb_suggestion", params={"query": q})
    rows = (raw or {}).get("d") if isinstance(raw, dict) else []
    rows = rows if isinstance(rows, list) else []
    movies, series = [], []
    for row in rows[:limit]:
        if not isinstance(row, dict):
            continue
        item = {
            "imdb_id": row.get("id"),
            "title": row.get("l") or row.get("title") or "",
            "year": row.get("y"),
            "kind": row.get("q") or content_type,
            "image_url": (row.get("i") or {}).get("imageUrl") if isinstance(row.get("i"), dict) else None,
        }
        target = series if str(item["kind"]).lower() in {"tv", "tvseries", "series"} else movies
        target.append(item)
    return {"movies": movies, "series": series}

async def search_tv(query: str, limit: int = 10):
    return await movie_tv_intelligence(query=query, content_type="series", limit=limit)

async def get_movie_catalog(query: str = "", limit: int = 10):
    return await movie_tv_intelligence(query=query, content_type="movie", limit=limit)

async def get_series_catalog(query: str = "", limit: int = 10):
    return await movie_tv_intelligence(query=query, content_type="series", limit=limit)

def all_providers():
    return list_providers()

async def health_check():
    return api_hub.provider_status()

__all__ = [
    "APIHub", "APIProvider", "api_hub", "api_call", "get_provider", "list_providers",
    "all_providers", "health_check", "get_weather", "get_exchange_rate", "get_country",
    "search_books", "get_random_joke", "search_products", "geocode", "reverse_geocode", "smart_api_query", "movie_tv_intelligence", "search_tv", "get_movie_catalog", "get_series_catalog",
]
