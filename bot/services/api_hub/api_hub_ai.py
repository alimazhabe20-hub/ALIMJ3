"""Optional AI-tool bridge for the keyless API Hub.

Imported by the stable ai_tools facade. It adds one generic, read-only tool
instead of adding a large number of Telegram buttons.
"""
from __future__ import annotations

from bot.services.tool_runtime import register_tool
from bot.services.api_hub import (
    api_call, list_providers, search_products, geocode, reverse_geocode,
    get_f1_data, search_games, get_game, search_spaceflight_news,
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


async def _f1(resource: str = "driverstandings", season: str = "current", round: str = "last"):
    return await get_f1_data(resource, season=season, round=round)

async def _games(genre: str | None = None, platform: str | None = None, sort_by: str | None = None, max_results: int = 20):
    return await search_games(genre=genre, platform=platform, sort_by=sort_by, max_results=max_results)

async def _game(game_id: int | str):
    return await get_game(game_id)

async def _space_news(query: str | None = None, limit: int = 10):
    return await search_spaceflight_news(query=query, limit=limit)

register_tool(
    name="hub_f1",
    description="داده‌های فرمول یک شامل برنامه، نتایج و جدول رانندگان/سازندگان بدون API key.",
    parameters={"type":"object","properties":{
        "resource":{"type":"string"},"season":{"type":"string","default":"current"},"round":{"type":"string","default":"last"}
    }}, handler=_f1, keywords=[r"فرمول یک", r"f1", r"formula 1", r"رانندگان", r"مسابقه"], risk="read", network=True,
)

register_tool(
    name="hub_games",
    description="جست‌وجو در کاتالوگ بازی‌های رایگان FreeToGame بدون API key.",
    parameters={"type":"object","properties":{
        "genre":{"type":"string"},"platform":{"type":"string"},"sort_by":{"type":"string"},"max_results":{"type":"integer","default":20}
    }}, handler=_games, keywords=[r"بازی", r"game", r"بازی رایگان", r"free to play"], risk="read", network=True,
)

register_tool(
    name="hub_game",
    description="دریافت جزئیات یک بازی رایگان از FreeToGame.",
    parameters={"type":"object","properties":{"game_id":{"type":"integer"}},"required":["game_id"]},
    handler=_game, keywords=[r"جزئیات بازی", r"game details"], risk="read", network=True,
)

register_tool(
    name="hub_spaceflight_news",
    description="جست‌وجو و دریافت اخبار فضایی/پروازهای فضایی از Spaceflight News API بدون API key.",
    parameters={"type":"object","properties":{"query":{"type":"string"},"limit":{"type":"integer","default":10}}},
    handler=_space_news, keywords=[r"اخبار فضایی", r"space news", r"ناسا", r"موشک", r"ماهواره"], risk="read", network=True,
)
