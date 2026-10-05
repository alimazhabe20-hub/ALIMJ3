"""Optional AI-tool bridge for the keyless API Hub.

Imported by the stable ai_tools facade. It adds one generic, read-only tool
instead of adding a large number of Telegram buttons.
"""
from __future__ import annotations

from bot.services.tool_runtime import register_tool
from bot.services.api_hub import (
    api_call, list_providers, search_products, geocode, reverse_geocode,
    get_f1_data, search_free_games, search_space_news, search_artworks, get_color,
    shorten_url, get_aircraft_states,
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

register_tool(
    name="hub_f1",
    description="داده‌های فرمول یک شامل برنامه و نتایج از Jolpica/Ergast بدون API key.",
    parameters={"type": "object", "properties": {"season": {"type": "string", "default": "current"}, "round_name": {"type": "string", "default": "next"}}},
    handler=get_f1_data, keywords=[r"فرمول یک", r"f1", r"formula 1", r"گران پری"], risk="read", network=True,
)

register_tool(
    name="hub_free_games",
    description="جست‌وجوی بازی‌های رایگان با فیلتر پلتفرم، ژانر و مرتب‌سازی.",
    parameters={"type": "object", "properties": {"platform": {"type": "string"}, "genre": {"type": "string"}, "sort_by": {"type": "string"}, "limit": {"type": "integer", "default": 20}}},
    handler=search_free_games, keywords=[r"بازی", r"گیم", r"game", r"free game"], risk="read", network=True,
)

register_tool(
    name="hub_space_news",
    description="دریافت و جست‌وجوی اخبار فضایی بدون API key.",
    parameters={"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 10}}},
    handler=search_space_news, keywords=[r"اخبار فضایی", r"space news", r"ناسا", r"ماهواره"], risk="read", network=True,
)

register_tool(
    name="hub_art_search",
    description="جست‌وجوی آثار هنری در Art Institute of Chicago.",
    parameters={"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 10}}, "required": ["query"]},
    handler=search_artworks, keywords=[r"هنر", r"اثر هنری", r"artwork", r"نقاشی"], risk="read", network=True,
)

register_tool(
    name="hub_color",
    description="دریافت مشخصات رنگ و تبدیل‌های رنگی از TheColorAPI.",
    parameters={"type": "object", "properties": {"value": {"type": "string"}}, "required": ["value"]},
    handler=get_color, keywords=[r"رنگ", r"hex", r"color"], risk="read", network=True,
)

register_tool(
    name="hub_shorten_url",
    description="کوتاه‌کردن لینک HTTP/HTTPS با is.gd.",
    parameters={"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
    handler=shorten_url, keywords=[r"کوتاه کردن لینک", r"short url", r"shorten url"], risk="read", network=True,
)

register_tool(
    name="hub_aircraft_states",
    description="دریافت وضعیت هواپیماهای قابل مشاهده از OpenSky؛ امکان تعیین محدوده جغرافیایی.",
    parameters={"type": "object", "properties": {
        "min_latitude": {"type": "number"}, "max_latitude": {"type": "number"},
        "min_longitude": {"type": "number"}, "max_longitude": {"type": "number"},
    }},
    handler=get_aircraft_states, keywords=[r"هواپیما", r"پرواز", r"flight", r"aircraft", r"opensky"], risk="read", network=True,
)

