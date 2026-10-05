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


async def movie_tv_intelligence(*, query: str | None = None, content_type: str = "both", limit: int = 10) -> dict[str, Any]:
    """Combine keyless movie/TV discovery sources without claiming IMDb is a first-party API."""
    q = str(query or "").strip()
    n = max(1, min(int(limit), 20))
    result: dict[str, Any] = {"query": q or None, "sources": [], "movies": [], "series": []}
    if q:
        tv = await search_tv(q, limit=n)
        result["series"] = tv.get("results", []) if isinstance(tv, dict) else []
        result["sources"].append("TVmaze")
        # Cinemeta supports path-based search; use a direct provider dynamically only when the query is requested.
        from .api_hub_registry import APIProvider
        from .api_hub import api_hub as _hub
        # Keep the registry keyless and stable by querying the catalog endpoint through the generic hub is not possible
        # for a path segment, so rely on TVmaze for search and Cinemeta for ranked catalogues.
        catalog = await get_movie_catalog(limit=n)
        result["movies"] = catalog.get("results", [])
        result["sources"].append("Cinemeta")
    else:
        if content_type.lower() in {"movie", "both"}:
            movies = await get_movie_catalog(limit=n)
            result["movies"] = movies.get("results", [])
            result["sources"].append("Cinemeta")
        if content_type.lower() in {"series", "tv", "both"}:
            series = await get_series_catalog(limit=n)
            result["series"] = series.get("results", [])
            result["sources"].append("Cinemeta")
    return result
