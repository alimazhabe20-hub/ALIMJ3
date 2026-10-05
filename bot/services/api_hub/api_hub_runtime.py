"""High-level API Hub helpers used by bot features and AI tools."""
from __future__ import annotations

from typing import Any

from .api_hub import api_hub


async def api_call(provider: str, params: dict[str, Any] | None = None) -> Any:
    return await api_hub.call(provider, params=params)


async def get_weather(latitude: float, longitude: float, *, forecast_days: int = 3) -> dict[str, Any]:
    return await api_hub.call(
        "open_meteo_forecast",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "forecast_days": max(1, min(int(forecast_days), 16)),
            "timezone": "auto",
        },
    )


async def get_exchange_rate(base: str = "USD", target: str = "EUR") -> dict[str, Any]:
    return await api_hub.call("frankfurter", params={"from": base.upper(), "to": target.upper()})


async def get_country(name: str) -> Any:
    return await api_hub.call("rest_countries", params={"name": name})


async def search_books(query: str, *, limit: int = 10) -> dict[str, Any]:
    return await api_hub.call(
        "open_library_search",
        params={"q": query, "limit": max(1, min(int(limit), 50))},
    )


async def get_random_joke() -> dict[str, Any]:
    return await api_hub.call("jokeapi", params={"safe-mode": "true", "type": "single,twopart"})


async def search_products(
    query: str, *, country: str = "US", language: str = "en", max_results: int = 10,
    min_price: float | None = None, max_price: float | None = None, free_shipping: bool | None = None,
) -> Any:
    """Search real AliExpress listings through the keyless OneFindMe API."""
    q = str(query or "").strip()
    if not q:
        raise ValueError("query is required")
    params: dict[str, Any] = {
        "query": q,
        "country": str(country or "US").upper(),
        "language": str(language or "en").lower(),
        "max_results": max(1, min(int(max_results), 20)),
    }
    if min_price is not None:
        params["min_price"] = max(0.0, float(min_price))
    if max_price is not None:
        params["max_price"] = max(0.0, float(max_price))
    if free_shipping is not None:
        params["free_shipping"] = bool(free_shipping)
    return await api_hub.call("onefindme_search", params=params)


async def geocode(query: str, *, limit: int = 5, language: str = "fa") -> Any:
    q = str(query or "").strip()
    if not q:
        raise ValueError("query is required")
    return await api_hub.call(
        "nominatim_search",
        params={
            "q": q, "format": "jsonv2", "addressdetails": 1,
            "limit": max(1, min(int(limit), 10)), "accept-language": language or "fa",
        },
    )


async def reverse_geocode(latitude: float, longitude: float, *, language: str = "fa") -> Any:
    return await api_hub.call(
        "nominatim_reverse",
        params={
            "lat": float(latitude), "lon": float(longitude), "format": "jsonv2",
            "addressdetails": 1, "accept-language": language or "fa",
        },
    )


async def search_tv(query: str, *, limit: int = 10) -> dict[str, Any]:
    q = str(query or "").strip()
    if not q:
        raise ValueError("query is required")
    data = await api_hub.call("tvmaze_search", params={"q": q})
    return {"source": "TVmaze", "results": data[: max(1, min(int(limit), 20))] if isinstance(data, list) else data}


async def get_tv_schedule(date: str | None = None, *, country: str = "US") -> Any:
    params: dict[str, Any] = {"country": str(country or "US").upper()}
    if date:
        params["date"] = str(date)
    return await api_hub.call("tvmaze_schedule", params=params)


async def get_web_tv_schedule(date: str | None = None, *, country: str | None = None) -> Any:
    params: dict[str, Any] = {}
    if date:
        params["date"] = str(date)
    if country is not None:
        params["country"] = str(country).upper()
    return await api_hub.call("tvmaze_web_schedule", params=params)


async def get_movie_catalog(*, limit: int = 20) -> dict[str, Any]:
    data = await api_hub.call("cinemeta_catalog_movies")
    metas = data.get("metas", []) if isinstance(data, dict) else []
    return {"source": "Cinemeta", "type": "movie", "results": metas[: max(1, min(int(limit), 50))]}


async def get_series_catalog(*, limit: int = 20) -> dict[str, Any]:
    data = await api_hub.call("cinemeta_catalog_series")
    metas = data.get("metas", []) if isinstance(data, dict) else []
    return {"source": "Cinemeta", "type": "series", "results": metas[: max(1, min(int(limit), 50))]}


async def movie_tv_latest(*, content_type: str = "movie", limit: int = 10) -> dict[str, Any]:
    """Return genuinely current/recent movie/TV releases from live catalogs.

    The current year is derived from the runtime clock. Results are taken from
    the current year first; the previous year is only a fallback when the current
    year has too few catalog entries. No fixed year is embedded in this logic.
    """
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    current_year = now.year
    previous_year = current_year - 1
    n = max(1, min(int(limit), 20))
    wanted = str(content_type or "movie").lower()
    if wanted in {"tv", "series"}:
        wanted = "series"
    elif wanted not in {"movie", "series", "both"}:
        wanted = "movie"

    async def safe(coro):
        try:
            return await coro
        except Exception:
            return None

    movies: list[dict] = []
    series: list[dict] = []
    sources: list[str] = []

    if wanted in {"movie", "both"}:
        data = await safe(get_movie_catalog(limit=100))
        if isinstance(data, dict):
            movies = [x for x in data.get("results", []) if isinstance(x, dict)]
            if movies:
                sources.append("Cinemeta movies")
    if wanted in {"series", "both"}:
        data = await safe(get_series_catalog(limit=100))
        if isinstance(data, dict):
            series = [x for x in data.get("results", []) if isinstance(x, dict)]
            if series:
                sources.append("Cinemeta series")

    def year_of(item: dict) -> int | None:
        for key in ("year", "y", "release_year", "released", "releaseInfo", "premiered", "release_date", "releasedate", "first_air_date"):
            value = item.get(key)
            text = str(value or "").strip()
            match = __import__("re").search(r"(20\d{2})", text)
            if match:
                return int(match.group(1))
        return None

    def rating_of(item: dict) -> float:
        for key in ("rating", "imdbRating", "imdb_rating", "score"):
            try:
                value = float(item.get(key))
                if value == value:
                    return value
            except (TypeError, ValueError):
                pass
        return 0.0

    def prepare(items: list[dict]) -> list[dict]:
        current: list[dict] = []
        previous: list[dict] = []
        for item in items:
            y = year_of(item)
            if y == current_year:
                current.append({**item, "year": y})
            elif y == previous_year:
                previous.append({**item, "year": y})
        current.sort(key=lambda x: rating_of(x), reverse=True)
        previous.sort(key=lambda x: rating_of(x), reverse=True)
        # Current year always wins. Previous year is fallback only.
        return (current + previous)[:n]

    prepared_movies = prepare(movies)
    prepared_series = prepare(series)
    return {
        "current_year": current_year,
        "fallback_year": previous_year,
        "as_of": now.isoformat(),
        "content_type": wanted,
        "movies": prepared_movies,
        "series": prepared_series,
        "sources": sources,
        "live": True,
    }


async def movie_tv_intelligence(*, query: str | None = None, content_type: str = "both", limit: int = 10) -> dict[str, Any]:
    """Multi-source movie/TV discovery with real query search and deduplication.

    Query mode uses TVmaze for series and IMDb's public suggestion endpoint for
    movie/general title discovery. Catalog mode uses Cinemeta when no query is
    supplied. IMDb is intentionally described as an unofficial public endpoint,
    not an official IMDb API.
    """
    import asyncio

    q = str(query or "").strip()
    n = max(1, min(int(limit), 20))
    wanted = str(content_type or "both").lower()
    if wanted not in {"movie", "series", "tv", "both"}:
        wanted = "both"
    result: dict[str, Any] = {"query": q or None, "sources": [], "movies": [], "series": []}

    async def safe(coro, source):
        try:
            value = await coro
            return source, value
        except Exception:
            return source, None

    tasks = []
    if q:
        if wanted in {"series", "tv", "both"}:
            tasks.append(safe(search_tv(q, limit=n), "TVmaze"))
        if wanted in {"movie", "both"}:
            tasks.append(safe(api_hub.call("imdb_suggestion", params={"query": q}), "IMDb suggestion"))
    else:
        if wanted in {"movie", "both"}:
            tasks.append(safe(get_movie_catalog(limit=n), "Cinemeta movies"))
        if wanted in {"series", "tv", "both"}:
            tasks.append(safe(get_series_catalog(limit=n), "Cinemeta series"))
            tasks.append(safe(get_tv_schedule(), "TVmaze schedule"))

    results = await asyncio.gather(*tasks)
    seen_movies: set[str] = set()
    seen_series: set[str] = set()

    for source, data in results:
        if data is None:
            continue
        result["sources"].append(source)

        if source == "TVmaze":
            items = data.get("results", []) if isinstance(data, dict) else []
            for item in items:
                show = item.get("show", {}) if isinstance(item, dict) else {}
                key = str(show.get("id") or show.get("externals", {}).get("imdb") or show.get("name") or "").strip().lower()
                if not key or key in seen_series:
                    continue
                seen_series.add(key)
                result["series"].append({
                    "title": show.get("name"),
                    "rating": (show.get("rating") or {}).get("average"),
                    "premiered": show.get("premiered"),
                    "genres": show.get("genres", []),
                    "imdb_id": (show.get("externals") or {}).get("imdb"),
                    "url": show.get("url"),
                    "source": source,
                })

        elif source == "IMDb suggestion":
            items = data.get("d", []) if isinstance(data, dict) else []
            for item in items:
                title = item.get("l") or item.get("title")
                if not title:
                    continue
                item_type = str(item.get("q") or "").lower()
                is_series = item_type in {"tvseries", "tvminiseries", "tvshort", "tvepisode", "tvmovie"}
                key = str(item.get("id") or title).strip().lower()
                target = result["series"] if is_series else result["movies"]
                seen = seen_series if is_series else seen_movies
                if key in seen:
                    continue
                seen.add(key)
                target.append({
                    "title": title,
                    "year": item.get("y"),
                    "kind": item.get("q"),
                    "imdb_id": item.get("id"),
                    "rank": item.get("rank"),
                    "image": (item.get("i") or {}).get("imageUrl"),
                    "source": source,
                })

        elif source == "Cinemeta movies":
            metas = data.get("results", []) if isinstance(data, dict) else []
            for item in metas:
                key = str(item.get("imdb_id") or item.get("id") or item.get("name") or "").strip().lower()
                if not key or key in seen_movies:
                    continue
                seen_movies.add(key)
                result["movies"].append({**item, "source": "Cinemeta", "rating": item.get("imdbRating", item.get("rating"))})

        elif source == "Cinemeta series":
            metas = data.get("results", []) if isinstance(data, dict) else []
            for item in metas:
                key = str(item.get("imdb_id") or item.get("id") or item.get("name") or "").strip().lower()
                if not key or key in seen_series:
                    continue
                seen_series.add(key)
                result["series"].append({**item, "source": "Cinemeta", "rating": item.get("imdbRating", item.get("rating"))})

        else:
            result["schedule"] = data

    result["movies"] = result["movies"][:n]
    result["series"] = result["series"][:n]
    return result


async def smart_api_query(category: str, params: dict[str, Any] | None = None, *, candidates: list[str] | None = None) -> Any:
    """Choose the healthiest provider in a category and fall back automatically."""
    from .api_hub import FALLBACK_CHAINS
    chain = tuple(candidates or FALLBACK_CHAINS.get(category, ()))
    if not chain:
        from .api_hub_registry import list_providers
        chain = tuple(p.name for p in list_providers(category))
    if not chain:
        raise ValueError(f"No providers registered for category: {category}")
    return await api_hub.call_with_fallback(chain, params=params or {}, retries=1)


async def search_anime(query: str, *, limit: int = 10) -> Any:
    return await api_hub.call("jikan_anime", params={"q": str(query).strip(), "limit": max(1, min(int(limit), 25))})


async def search_games(*, category: str | None = None, platform: str | None = None) -> Any:
    params: dict[str, Any] = {}
    if category: params["category"] = category
    if platform: params["platform"] = platform
    return await api_hub.call("freetogame_games", params=params)


async def search_science(query: str, *, page_size: int = 10) -> Any:
    return await api_hub.call("europe_pmc", params={"query": str(query).strip(), "pageSize": max(1, min(int(page_size), 50))})


async def search_health(query: str, *, page_size: int = 10) -> Any:
    return await api_hub.call("clinical_trials", params={"query.term": str(query).strip(), "pageSize": max(1, min(int(page_size), 50))})


async def search_security(query: str, *, limit: int = 10) -> Any:
    return await api_hub.call("nvd_cves", params={"keywordSearch": str(query).strip(), "resultsPerPage": max(1, min(int(limit), 20))})
