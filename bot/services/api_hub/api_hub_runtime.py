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


async def get_crypto_prices(
    ids: str = "bitcoin,ethereum",
    *,
    vs_currency: str = "usd",
    include_24h_change: bool = True,
) -> dict[str, Any]:
    """Get current public CoinGecko prices without an API key."""
    return await api_hub.call(
        "coin_gecko_simple",
        params={
            "ids": ids,
            "vs_currencies": vs_currency.lower(),
            "include_24hr_change": str(bool(include_24h_change)).lower(),
        },
    )


async def search_music(query: str, *, limit: int = 10) -> dict[str, Any]:
    """Search music metadata using iTunes Search (no key required)."""
    return await api_hub.call(
        "itunes_search",
        params={
            "term": query,
            "media": "music",
            "entity": "song",
            "limit": max(1, min(int(limit), 50)),
        },
    )


async def search_music_metadata(query: str, *, limit: int = 10) -> dict[str, Any]:
    """Search recording metadata through MusicBrainz."""
    return await api_hub.call(
        "musicbrainz",
        params={"query": query, "fmt": "json", "limit": max(1, min(int(limit), 100))},
    )


async def search_tv(query: str, *, limit: int = 10) -> list[dict[str, Any]]:
    """Search TV shows through TVMaze."""
    return await api_hub.call(
        "tvmaze_search",
        params={"q": query},
    )


async def get_public_holidays(year: int, country_code: str = "IR") -> list[dict[str, Any]]:
    """Return public holidays for a country using Nager.Date."""
    return await api_hub.call(
        "nager_date",
        params={"year": int(year), "country_code": country_code.upper()},
    )
