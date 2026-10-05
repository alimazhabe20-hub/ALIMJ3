"""Optional AI-tool bridge for the keyless API Hub.

Imported by the stable ai_tools facade. It adds one generic, read-only tool
instead of adding a large number of Telegram buttons.
"""
from __future__ import annotations

from bot.services.tool_runtime import register_tool
from bot.services.api_hub import (
    api_call, list_providers, search_products, geocode, reverse_geocode,
    search_art, get_color_info, shorten_url, get_aircraft_states,
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


async def _art_search(query: str, limit: int = 10):
    return await search_art(query, limit=limit)

async def _color_info(color: str):
    return await get_color_info(color)

async def _shorten_url(url: str):
    return await shorten_url(url)

async def _aircraft_states(lamin: float | None = None, lomin: float | None = None, lamax: float | None = None, lomax: float | None = None):
    return await get_aircraft_states(lamin=lamin, lomin=lomin, lamax=lamax, lomax=lomax)


register_tool(
    name="hub_art_search",
    description="جست‌وجوی آثار هنری و اطلاعات تصویر از Art Institute of Chicago بدون API key.",
    parameters={"type":"object","properties":{"query":{"type":"string"},"limit":{"type":"integer","default":10}},"required":["query"]},
    handler=_art_search, keywords=[r"هنر", r"اثر هنری", r"art", r"artwork", r"نقاشی"], risk="read", network=True,
)

register_tool(
    name="hub_color_info",
    description="دریافت اطلاعات دقیق رنگ، نام، RGB/HSL و پالت مرتبط از TheColorAPI.",
    parameters={"type":"object","properties":{"color":{"type":"string"}},"required":["color"]},
    handler=_color_info, keywords=[r"رنگ", r"color", r"hex", r"rgb"], risk="read", network=True,
)

register_tool(
    name="hub_shorten_url",
    description="کوتاه‌کردن لینک http/https با is.gd بدون API key.",
    parameters={"type":"object","properties":{"url":{"type":"string"}},"required":["url"]},
    handler=_shorten_url, keywords=[r"کوتاه کردن لینک", r"short url", r"url کوتاه", r"لینک کوتاه"], risk="read", network=True,
)

register_tool(
    name="hub_aircraft_states",
    description="دریافت وضعیت زنده هواپیماها از OpenSky؛ امکان محدودکردن محدوده جغرافیایی با bounding box.",
    parameters={"type":"object","properties":{
        "lamin":{"type":"number"},"lomin":{"type":"number"},"lamax":{"type":"number"},"lomax":{"type":"number"}
    }},
    handler=_aircraft_states, keywords=[r"هواپیما", r"پرواز", r"flight", r"aircraft", r"aviation"], risk="read", network=True,
)
