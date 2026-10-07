"""Optional AI-tool bridge for the keyless API Hub.

Imported by the stable ai_tools facade. It adds one generic, read-only tool
instead of adding a large number of Telegram buttons.
"""
from __future__ import annotations

from bot.services.tool_runtime import register_tool
from bot.services.api_hub import (
    api_call, list_providers, search_products, geocode, reverse_geocode, smart_api_query,
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


async def _smart_public_api(query: str, max_results: int = 10):
    result = await smart_api_query(query, max_results=max_results)
    if result.get("handled"):
        return result
    # Unknown public-API request: let the existing web-search capability take
    # over rather than pretending an API exists.
    try:
        from bot.services.ai_extras import web_search
        web_result = await web_search(query)
        return {
            "handled": True,
            "source": "web_search_fallback",
            "query": query,
            "results": web_result,
        }
    except Exception as exc:
        return {
            "handled": False,
            "source": result.get("source"),
            "query": query,
            "error": str(exc)[:300],
        }

register_tool(
    name="hub_smart_public_api",
    description=(
        "Fallback هوشمند برای درخواست‌هایی که ابزار اختصاصی ندارند. ابتدا APIهای عمومی "
        "بدون کلید را با توجه به موضوع امتحان می‌کند و اگر API مناسب/در دسترس نبود، "
        "به جستجوی وب موجود ربات fallback می‌کند. از ادعای نتیجه ساختگی خودداری می‌کند."
    ),
    parameters={"type": "object", "properties": {
        "query": {"type": "string"},
        "max_results": {"type": "integer", "default": 10},
    }, "required": ["query"]},
    handler=_smart_public_api,
    keywords=[r"fallback", r"api عمومی", r"public api", r"اطلاعاتی که ابزار اختصاصی ندارد"],
    risk="read", network=True,
)
