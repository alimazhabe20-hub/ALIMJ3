"""Optional AI-tool bridge for the keyless API Hub.

Imported by the stable ai_tools facade. It adds one generic, read-only tool
instead of adding a large number of Telegram buttons.
"""
from __future__ import annotations

from bot.services.tool_runtime import register_tool
from bot.services.api_hub import (
    api_call, list_providers, search_products, geocode, reverse_geocode, movie_tv_intelligence,
)


def _provider_names() -> str:
    return ", ".join(item.name for item in list_providers())


async def _api_hub_call(provider: str, params: dict | None = None):
    return await api_call(provider, params or {})


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


async def _shopping_search(query: str, country: str = "US", language: str = "en", max_results: int = 10, min_price: float | None = None, max_price: float | None = None, free_shipping: bool | None = None):
    return await search_products(
        query, country=country, language=language, max_results=max_results,
        min_price=min_price, max_price=max_price, free_shipping=free_shipping,
    )


async def _geocode(query: str, limit: int = 5, language: str = "fa"):
    return await geocode(query, limit=limit, language=language)


async def _reverse_geocode(latitude: float, longitude: float, language: str = "fa"):
    return await reverse_geocode(latitude, longitude, language=language)


register_tool(
    name="hub_shopping_search",
    description="جست‌وجوی کالای واقعی در AliExpress از طریق OneFindMe؛ قیمت، امتیاز، تعداد سفارش و لینک را برمی‌گرداند.",
    parameters={"type": "object", "properties": {
        "query": {"type": "string"}, "country": {"type": "string", "default": "US"},
        "language": {"type": "string", "default": "en"}, "max_results": {"type": "integer", "default": 10},
        "min_price": {"type": "number"}, "max_price": {"type": "number"},
        "free_shipping": {"type": "boolean"},
    }, "required": ["query"]},
    handler=_shopping_search,
    keywords=[r"خرید", r"قیمت کالا", r"محصول", r"shopping", r"product search", r"کفش", r"لباس"],
    risk="read", network=True,
)

register_tool(
    name="hub_geocode",
    description="تبدیل نام مکان یا آدرس به مختصات جغرافیایی با Nominatim/OpenStreetMap.",
    parameters={"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 5}, "language": {"type": "string", "default": "fa"}}, "required": ["query"]},
    handler=_geocode, keywords=[r"موقعیت", r"مختصات", r"آدرس", r"geocode", r"coordinates"], risk="read", network=True,
)

register_tool(
    name="hub_reverse_geocode",
    description="تبدیل latitude/longitude به آدرس و نام مکان.",
    parameters={"type": "object", "properties": {"latitude": {"type": "number"}, "longitude": {"type": "number"}, "language": {"type": "string", "default": "fa"}}, "required": ["latitude", "longitude"]},
    handler=_reverse_geocode, keywords=[r"reverse geocode", r"آدرس مختصات"], risk="read", network=True,
)


async def _movie_tv(query: str | None = None, content_type: str = "both", limit: int = 10):
    return await movie_tv_intelligence(query=query, content_type=content_type, limit=limit)

register_tool(
    name="hub_movie_tv_intelligence",
    description="پیشنهاد و کشف فیلم و سریال با منابع عمومی بدون کلید؛ شامل IMDb ID/امتیازهای ارائه‌شده توسط Cinemeta و اطلاعات پخش TVmaze. این ابزار ادعا نمی‌کند API رسمی IMDb است.",
    parameters={"type": "object", "properties": {
        "query": {"type": "string"},
        "content_type": {"type": "string", "enum": ["movie", "series", "both"], "default": "both"},
        "limit": {"type": "integer", "default": 10},
    }},
    handler=_movie_tv,
    keywords=[r"فیلم", r"سریال", r"فیلم این ماه", r"سریال این ماه", r"بهترین فیلم", r"بهترین سریال", r"movie", r"series", r"IMDb"],
    risk="read", network=True,
)

from bot.services.api_hub import smart_api_query


async def _smart_public_api(category: str, params: dict | None = None):
    """Route a read-only request to the healthiest keyless provider."""
    return await smart_api_query(category, params or {})


register_tool(
    name="hub_smart_public_api",
    description="انتخاب خودکار سالم‌ترین API بدون کلید بر اساس دسته‌بندی، با fallback داخلی.",
    parameters={
        "type": "object",
        "properties": {
            "category": {"type": "string", "description": "مثلاً weather, books, music, video, science, security"},
            "params": {"type": "object"},
        },
        "required": ["category"],
    },
    handler=_smart_public_api,
    keywords=[r"انتخاب api", r"smart api", r"api سالم", r"fallback api"],
    risk="read", network=True,
)
