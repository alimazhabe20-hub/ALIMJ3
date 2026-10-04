"""AI bridge for ALIMJ3's keyless public API Hub.

The bridge exposes a small set of intent-oriented, read-only tools instead of
forcing the model to know provider names.  The generic ``api_hub_call`` remains
available for advanced use, while the helpers below are safer defaults.
"""
from __future__ import annotations

from bot.services.tool_runtime import register_tool
from bot.services.api_hub import (
    api_call,
    get_country,
    get_exchange_rate,
    get_weather,
    list_providers,
    search_books,
    get_random_joke,
)


def _provider_names() -> str:
    return ", ".join(item.name for item in list_providers())


async def _api_hub_call(provider: str, params: dict | None = None):
    return await api_call(provider, params or {})


async def _hub_weather(latitude: float, longitude: float, forecast_days: int = 3):
    return await get_weather(float(latitude), float(longitude), forecast_days=forecast_days)


async def _hub_currency(base: str = "USD", target: str = "EUR"):
    return await get_exchange_rate(base.upper(), target.upper())


async def _hub_country(name: str):
    return await get_country(name.strip())


async def _hub_books(query: str, limit: int = 10):
    return await search_books(query.strip(), limit=limit)


async def _hub_joke():
    return await get_random_joke()


register_tool(
    name="api_hub_call",
    description=(
        "اجرای API عمومی بدون API key از API Hub. فقط providerهای ثبت‌شده و read-only را اجرا می‌کند. "
        f"Providerهای فعال: {_provider_names()}"
    ),
    parameters={
        "type": "object",
        "properties": {
            "provider": {"type": "string", "description": "نام provider ثبت‌شده"},
            "params": {"type": "object", "description": "پارامترهای query/path"},
        },
        "required": ["provider"],
    },
    handler=_api_hub_call,
    keywords=[r"api hub", r"api عمومی", r"public api", r"اطلاعات عمومی"],
    risk="read",
    network=True,
)

register_tool(
    name="hub_weather",
    description="گرفتن وضعیت فعلی و پیش‌بینی هوا از Open-Meteo بدون API key.",
    parameters={
        "type": "object", "properties": {
            "latitude": {"type": "number"},
            "longitude": {"type": "number"},
            "forecast_days": {"type": "integer", "minimum": 1, "maximum": 16},
        }, "required": ["latitude", "longitude"],
    },
    handler=_hub_weather,
    keywords=[],
    risk="read", network=True,
)

register_tool(
    name="hub_currency",
    description="دریافت نرخ مرجع تبدیل دو ارز از Frankfurter بدون API key.",
    parameters={
        "type": "object", "properties": {
            "base": {"type": "string"}, "target": {"type": "string"},
        }, "required": ["base", "target"],
    },
    handler=_hub_currency,
    keywords=[],
    risk="read", network=True,
)

register_tool(
    name="hub_country",
    description="دریافت اطلاعات کشور از REST Countries بدون API key.",
    parameters={
        "type": "object", "properties": {"name": {"type": "string"}},
        "required": ["name"],
    },
    handler=_hub_country,
    keywords=[],
    risk="read", network=True,
)

register_tool(
    name="hub_books",
    description="جست‌وجوی کتاب در Open Library بدون API key.",
    parameters={
        "type": "object", "properties": {
            "query": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 50},
        }, "required": ["query"],
    },
    handler=_hub_books,
    keywords=[],
    risk="read", network=True,
)

register_tool(
    name="hub_joke",
    description="دریافت یک جوک تصادفی ایمن از JokeAPI بدون API key.",
    parameters={"type": "object", "properties": {}},
    handler=_hub_joke,
    keywords=[],
    risk="read", network=True,
)
