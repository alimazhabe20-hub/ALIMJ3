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


async def smart_api_query(query: str, *, max_results: int = 10) -> dict[str, Any]:
    """Best-effort keyless public-API lookup for requests without a dedicated tool.

    This is intentionally conservative: it only uses providers whose parameter
    contract is known. Unknown requests return ``handled=False`` so the AI layer
    can fall back to web search instead of inventing an API call.
    """
    import re
    q = str(query or "").strip()
    if not q:
        return {"handled": False, "reason": "empty_query", "query": q}

    rules = [
        (r"(?:کتاب|نویسنده|رمان|book|author)", "open_library_search", lambda: {"q": q, "limit": max(1, min(int(max_results), 20))}),
        (r"(?:کشور|پایتخت|جمعیت|country|capital|population)", "rest_countries", lambda: {"name": q}),
        (r"(?:موزیک|آهنگ|خواننده|artist|song|music)", "itunes_search", lambda: {"term": q, "limit": max(1, min(int(max_results), 20))}),
        (r"(?:سریال|tv|show|series)", "tvmaze_search", lambda: {"q": q}),
        (r"(?:نقل.?قول|quote)", "quotable", lambda: {}),
    ]
    for pattern, provider, params_factory in rules:
        if re.search(pattern, q, re.I):
            try:
                data = await api_hub.call(provider, params=params_factory())
                return {"handled": True, "source": provider, "query": q, "results": data}
            except Exception as exc:
                return {"handled": False, "source": provider, "query": q, "error": str(exc)[:300]}
    return {"handled": False, "query": q, "reason": "no_matching_public_api"}


async def search_tv(query: str, *, limit: int = 10) -> Any:
    """Search TV shows through the keyless TVMaze provider."""
    q = str(query or "").strip()
    if not q:
        raise ValueError("query is required")
    return await api_hub.call("tvmaze_search", params={"q": q})


async def get_movie_catalog(*, limit: int = 10) -> Any:
    """Return the public Cinemeta movie catalog."""
    data = await api_hub.call("cinemeta_catalog_movies", params={})
    if isinstance(data, dict) and isinstance(data.get("metas"), list):
        data = {**data, "metas": data["metas"][:max(1, min(int(limit), 50))]}
    return data


async def get_series_catalog(*, limit: int = 10) -> Any:
    """Return the public Cinemeta series catalog."""
    data = await api_hub.call("cinemeta_catalog_series", params={})
    if isinstance(data, dict) and isinstance(data.get("metas"), list):
        data = {**data, "metas": data["metas"][:max(1, min(int(limit), 50))]}
    return data


async def movie_tv_intelligence(query: str, *, content_type: str = "movie", limit: int = 10) -> dict[str, Any]:
    """Small, deterministic movie/TV intelligence facade over public APIs."""
    q = str(query or "").strip()
    if not q:
        raise ValueError("query is required")
    kind = str(content_type or "movie").strip().lower()
    if kind in {"tv", "series", "show"}:
        raw = await search_tv(q, limit=limit)
        rows = raw.get("show", []) if isinstance(raw, dict) else raw
        if isinstance(rows, dict): rows = [rows]
        return {"query": q, "content_type": "series", "series": list(rows or [])[:max(1, min(int(limit), 20))]}

    raw = await api_hub.call("imdb_suggestion", params={"query": q})
    rows = raw.get("d", []) if isinstance(raw, dict) else []
    movies = []
    for item in rows[:max(1, min(int(limit), 20))]:
        if not isinstance(item, dict):
            continue
        movies.append({
            "imdb_id": item.get("id", ""),
            "title": item.get("l", ""),
            "year": item.get("y"),
            "type": item.get("q", ""),
            "rank": item.get("rank"),
            "image": (item.get("i") or {}).get("imageUrl", ""),
        })
    return {"query": q, "content_type": "movie", "movies": movies}
