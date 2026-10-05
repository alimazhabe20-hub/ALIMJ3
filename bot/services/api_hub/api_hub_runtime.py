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

async def get_f1_data(season: str = "current", round_name: str = "next") -> dict[str, Any]:
    """Fetch Formula 1 schedule/results through the keyless Jolpica API."""
    season = str(season or "current").strip()
    round_name = str(round_name or "next").strip()
    return await api_hub.call("jolpica_f1", params={"season": season, "round": round_name})


async def search_free_games(
    *, platform: str | None = None, genre: str | None = None,
    sort_by: str | None = None, limit: int = 20,
) -> Any:
    params: dict[str, Any] = {}
    if platform:
        params["platform"] = str(platform)
    if genre:
        params["category"] = str(genre)
    if sort_by:
        params["sort-by"] = str(sort_by)
    data = await api_hub.call("freetogame_games", params=params)
    if isinstance(data, list):
        return data[:max(1, min(int(limit), 100))]
    return data


async def search_space_news(query: str | None = None, *, limit: int = 10) -> Any:
    params: dict[str, Any] = {"limit": max(1, min(int(limit), 50)), "ordering": "-published_at"}
    if query:
        params["search"] = str(query).strip()
    return await api_hub.call("spaceflight_news", params=params)


async def search_artworks(query: str, *, limit: int = 10) -> Any:
    q = str(query or "").strip()
    if not q:
        raise ValueError("query is required")
    return await api_hub.call("artic_search", params={"q": q, "limit": max(1, min(int(limit), 100))})


async def get_color(value: str) -> Any:
    value = str(value or "").strip()
    if not value:
        raise ValueError("value is required")
    return await api_hub.call("thecolorapi", params={"hex": value.lstrip("#")})


async def shorten_url(url: str) -> Any:
    url = str(url or "").strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        raise ValueError("a valid http(s) URL is required")
    return await api_hub.call("isgd_shortener", params={"format": "json", "url": url})


async def get_aircraft_states(
    *, min_latitude: float | None = None, max_latitude: float | None = None,
    min_longitude: float | None = None, max_longitude: float | None = None,
) -> Any:
    params: dict[str, Any] = {}
    bounds = {
        "lamin": min_latitude, "lamax": max_latitude,
        "lomin": min_longitude, "lomax": max_longitude,
    }
    for key, value in bounds.items():
        if value is not None:
            params[key] = float(value)
    return await api_hub.call("opensky_states", params=params)

