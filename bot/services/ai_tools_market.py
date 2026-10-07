"""ai_tools: market responsibilities."""
from .ai_tools_common import *  # noqa: F401,F403
from . import ai_tools_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


async def _get_market_prices() -> str:
    from bot.features.market.finance import full_market_prices

    return await full_market_prices()

async def _search_shopping(query: str = "", source: str = "all", max_results: int = 12, min_price: int = 0, max_price: int = 0) -> str:
    from bot.features.market.shopping import search_shopping
    return await search_shopping(
        query=query, source=source, max_results=int(max_results or 12),
        min_price=int(min_price or 0), max_price=int(max_price or 0),
    )

def _shopping_price_history(query: str = "", days: int = 30) -> str:
    from bot.features.market.shopping import shopping_price_history
    return shopping_price_history(query=query, days=int(days or 30))

async def _get_crypto_price(symbol: str = "btc", user_id: int = 0) -> str:
    from bot.features.market.finance import get_crypto_price
    return await get_crypto_price(symbol)

async def _get_top_crypto(limit: int = 10) -> str:
    from bot.features.market.finance import get_top_crypto

    return await get_top_crypto(int(limit or 10))

async def _analyze_crypto(symbol: str = "") -> str:
    from bot.features.market.finance import analyze_crypto
    return await analyze_crypto(str(symbol or "btc"))

async def _crypto_chart_info(symbol: str = "", days: int = 7) -> str:
    """برای AI فقط متن توضیح می‌دهد (تصویر جدا از هندلر پیام است)"""
    from bot.features.market.finance import get_crypto_chart
    png, caption = await get_crypto_chart(str(symbol or "btc"), int(days or 7))
    if png:
        return caption + "\n\n(نمودار تصویری در بخش بازار ربات در دسترس است. بنویس: نمودار " + str(symbol) + ")"
    return caption or "داده نمودار در دسترس نیست."

async def _get_economic_calendar(days: int = 1, currency: str = "", impact: str = "all", timezone: str = "", user_id: int = 0) -> str:
    """داده زنده تقویم اقتصادی برای استفاده مستقیم AI."""
    from bot.features.market.economic_calendar import get_calendar_for_user, calendar_text, ai_context
    mode = "week" if int(days or 1) >= 7 else "today"
    if int(days or 1) == 2:
        mode = "tomorrow"
    events, user_tz = await get_calendar_for_user(user_id, mode, impact or "all", currency or "")
    tz_name = timezone.strip() if timezone.strip() else user_tz
    if not events:
        return "برای این فیلتر رویداد اقتصادی‌ای پیدا نشد."
    return "منبع: تقویم اقتصادی زنده\nمنطقه زمانی: %s\n\n%s" % (tz_name, ai_context(events, tz_name, 60))

async def _tool_web_search(query: str = "") -> str:
    from bot.services.ai_extras import web_search
    return await web_search(query)
