"""AI-tool bridge for the keyless API Hub.

The bridge exposes focused read-only capabilities without adding Telegram
buttons.  Generic api_hub_call remains available for advanced requests.
"""
from __future__ import annotations

from bot.services.tool_runtime import register_tool
from bot.services.api_hub import (
    api_call,
    get_crypto_prices,
    get_public_holidays,
    list_providers,
    search_music,
    search_music_metadata,
    search_tv,
)


def _provider_names() -> str:
    return ", ".join(item.name for item in list_providers())


async def _api_hub_call(provider: str, params: dict | None = None):
    return await api_call(provider, params or {})


async def _crypto(ids: str = "bitcoin,ethereum", vs_currency: str = "usd"):
    return await get_crypto_prices(ids, vs_currency=vs_currency)


async def _music(query: str, limit: int = 10):
    return await search_music(query, limit=limit)


async def _music_metadata(query: str, limit: int = 10):
    return await search_music_metadata(query, limit=limit)


async def _tv(query: str, limit: int = 10):
    rows = await search_tv(query, limit=limit)
    return rows[: max(1, min(int(limit), 50))]


async def _calendar(year: int, country_code: str = "IR"):
    return await get_public_holidays(year, country_code)


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
    name="hub_crypto",
    description="قیمت لحظه‌ای عمومی ارزهای دیجیتال و تغییر ۲۴ ساعته از CoinGecko بدون API key.",
    parameters={
        "type": "object",
        "properties": {
            "ids": {"type": "string", "description": "شناسه‌های CoinGecko با کاما؛ مثل bitcoin,ethereum"},
            "vs_currency": {"type": "string", "description": "ارز نمایش قیمت؛ مثل usd یا eur"},
        },
    },
    handler=_crypto,
    risk="read",
    network=True,
)

register_tool(
    name="hub_music",
    description="جست‌وجوی آهنگ، خواننده و اطلاعات موسیقی با iTunes بدون API key.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "نام آهنگ، خواننده یا عبارت جست‌وجو"},
            "limit": {"type": "integer", "description": "تعداد نتایج"},
        },
        "required": ["query"],
    },
    handler=_music,
    risk="read",
    network=True,
)

register_tool(
    name="hub_music_metadata",
    description="جست‌وجوی metadata موسیقی با MusicBrainz بدون API key.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "عبارت جست‌وجوی MusicBrainz"},
            "limit": {"type": "integer", "description": "تعداد نتایج"},
        },
        "required": ["query"],
    },
    handler=_music_metadata,
    risk="read",
    network=True,
)

register_tool(
    name="hub_tv",
    description="جست‌وجوی فیلم و سریال تلویزیونی از TVMaze بدون API key.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "نام سریال یا عبارت جست‌وجو"},
            "limit": {"type": "integer", "description": "تعداد نتایج"},
        },
        "required": ["query"],
    },
    handler=_tv,
    risk="read",
    network=True,
)

register_tool(
    name="hub_calendar",
    description="دریافت تعطیلات رسمی کشورها با Nager.Date بدون API key.",
    parameters={
        "type": "object",
        "properties": {
            "year": {"type": "integer", "description": "سال میلادی"},
            "country_code": {"type": "string", "description": "کد دوحرفی کشور؛ ایران IR"},
        },
        "required": ["year"],
    },
    handler=_calendar,
    risk="read",
    network=True,
)
