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


# Lightweight semantic router for AI: maps common user intents to keyless providers.
_SMART_ROUTES = {
    "book": ("open_library_search", lambda q: {"q": q, "limit": 10}),
    "anime": ("jikan_anime_search", lambda q: {"q": q}),
    "music": ("itunes_search", lambda q: {"term": q, "media": "music", "limit": 10}),
    "tv": ("tvmaze_search", lambda q: {"q": q}),
    "news": ("hackernews_search", lambda q: {"query": q}),
    "quote": ("quotable", lambda q: {"tags": q} if q else {}),
    "joke": ("jokeapi", lambda q: {"safe-mode": "true", "type": "single,twopart"}),
    "crypto": ("coin_gecko_simple", lambda q: {"ids": q, "vs_currencies": "usd"}),
    "country": ("rest_countries", lambda q: {}),
    "weather": ("open_meteo_forecast", lambda q: {}),
    "game": ("freetogame", lambda q: {"search": q}),
    "science": ("europe_pmc", lambda q: {"query": q, "format": "json"}),
}


def _smart_category(text: str) -> str | None:
    t = str(text or "").lower()
    groups = {
        "anime": ("انیمه", "anime", "مانگا", "manga"),
        "book": ("کتاب", "رمان", "نویسنده", "book", "novel"),
        "music": ("آهنگ", "موسیقی", "خواننده", "music", "song"),
        "tv": ("سریال", "فیلم", "tv", "show", "series"),
        "news": ("خبر", "اخبار", "news"),
        "quote": ("نقل قول", "جمله انگیزشی", "quote"),
        "joke": ("جوک", "لطیفه", "joke"),
        "crypto": ("کریپتو", "ارز دیجیتال", "بیت کوین", "bitcoin", "crypto"),
        "game": ("بازی", "game", "گیمر"),
        "science": ("مقاله علمی", "تحقیق علمی", "science", "paper"),
    }
    for name, keys in groups.items():
        if any(k in t for k in keys):
            return name
    return None


async def smart_lookup(query: str, category: str | None = None) -> Any:
    q = str(query or "").strip()
    if not q:
        raise ValueError("query is required")
    cat = (category or _smart_category(q))
    if not cat or cat not in _SMART_ROUTES:
        return {"ok": False, "message": "No confident API category matched", "query": q}
    provider, builder = _SMART_ROUTES[cat]
    params = builder(q)
    if cat == "country":
        params = {}
    return {"category": cat, "provider": provider, "data": await api_hub.call(provider, params=params)}
