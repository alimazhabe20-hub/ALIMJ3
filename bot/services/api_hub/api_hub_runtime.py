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


async def get_f1_data(
    resource: str = "driverstandings", *, season: str = "current", round: str = "last",
) -> dict[str, Any]:
    """Read Formula 1 data from the keyless Jolpica/Ergast-compatible API."""
    allowed = {"driverstandings", "constructorstandings", "results", "qualifying", "sprint", "schedule"}
    resource = str(resource or "driverstandings").strip().lower()
    if resource not in allowed:
        raise ValueError("unsupported F1 resource")
    season = str(season or "current").strip()
    round = str(round or "last").strip()
    return await api_hub.call(
        "jolpica_f1",
        params={"season": season, "round": round, "resource": resource},
    )


async def search_games(
    *, genre: str | None = None, platform: str | None = None,
    sort_by: str | None = None, max_results: int = 20,
) -> Any:
    """Search the FreeToGame catalog without an API key."""
    params: dict[str, Any] = {}
    if genre:
        params["genre"] = str(genre).strip()
    if platform:
        params["platform"] = str(platform).strip()
    if sort_by:
        params["sort-by"] = str(sort_by).strip()
    data = await api_hub.call("freetogame_games", params=params)
    if isinstance(data, list):
        return data[:max(1, min(int(max_results), 50))]
    return data


async def get_game(game_id: int | str) -> Any:
    value = str(game_id).strip()
    if not value:
        raise ValueError("game_id is required")
    return await api_hub.call("freetogame_game", params={"id": value})


async def search_spaceflight_news(
    *, query: str | None = None, limit: int = 10, ordering: str = "-published_at",
) -> dict[str, Any]:
    """Fetch recent spaceflight news; optional query filters title/summary fields."""
    params: dict[str, Any] = {
        "limit": max(1, min(int(limit), 20)),
        "ordering": ordering if ordering in {"published_at", "-published_at", "updated_at", "-updated_at"} else "-published_at",
    }
    if query and str(query).strip():
        params["search"] = str(query).strip()
    return await api_hub.call("spaceflight_news", params=params)
