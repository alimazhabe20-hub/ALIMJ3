"""Live product-price gate used by the real messages handler.

This module intentionally contains only the product-shopping interception logic.
The actual handler in ``handlers_messages_parts_part_999_core_legacy.py`` imports it before generic AI.

v1.1 changes:
- Budget-style requests are treated as live product requests
  e.g. «یه گوشی شیائومی تا 50 میلیون تومان»
- Budget numbers are preserved in the query passed to search_shopping
"""

from __future__ import annotations

import re


# Financial/market requests must stay on the market path even when they contain
# words such as «قیمت» or "price".
_MARKET_RE = re.compile(
    r"(?:تحلیل|آنالیز|analysis|analyze|بازار|market|کریپتو|رمزارز|crypto|"
    r"بیت\s*کوین|bitcoin|btc|اتریوم|ethereum|eth|تتر|usdt|سولانا|solana|sol|"
    r"طلا|gold|xau|forex|فارکس|حمایت|مقاومت|RSI|ADX|ATR|BOS|CHOCH|"
    r"لانگ|شورت|ترید|trade|trading|سیگنال|تایم\s*فریم|funding|open\s*interest|"
    r"دلار|یورو|پوند|درهم|لیر|یوان|روبل|افغانی|دینار|usd|eur|gbp|aed|try|cny|rub|afn|iqd)",
    re.I,
)

# A product request can be phrased without «خرید» at all:
# «قیمت آیفون ۱۸ پرو مکس چنده؟», «ارزان‌ترین لپ‌تاپ», «چه خمیر سیلیکونی بخرم؟».
_PRODUCT_OBJECT_RE = re.compile(
    r"(?:آیفون|iphone|سامسونگ|samsung|شیائومی|xiaomi|redmi|پوکو|poco|"
    r"لپ\s*تاپ|لپتاپ|laptop|کامپیوتر|pc|مانیتور|monitor|تلویزیون|tv|"
    r"گوشی|موبایل|mobile|تبلت|tablet|هدفون|هندزفری|headphone|earbuds|"
    r"کیبورد|keyboard|ماوس|mouse|پرینتر|printer|ssd|هارد|hard|ram|رم|"
    r"پردازنده|cpu|گرافیک|gpu|کارت\s*گرافیک|مادربرد|motherboard|پاور|psu|"
    r"خمیر\s*سیلیکون|خمیر\s*حرارتی|thermal\s*paste|کولر|cooler|"
    r"شارژر|charger|کابل|cable|پاوربانک|powerbank|ساعت\s*هوشمند|smartwatch|"
    r"دوربین|camera|کنسول|console|پلی\s*استیشن|playstation|xbox|نینتندو|nintendo|"
    r"کتانی|کفش|shoe|لباس|عطر|perfume|لوازم\s*خانگی|یخچال|ماشین\s*لباسشویی|"
    r"محصول|product|مدل|model|برند|brand)",
    re.I,
)

# Explicit shopping / recommendation verbs.
_PRODUCT_ACTION_RE = re.compile(
    r"(?:قیمت|نرخ|چنده|چقدر|چند(?:ه|ه؟)|ارزان(?:ترین)?|اقتصادی|"
    r"خرید|بخرم|بخریم|بخر|فروشگاه|فروشنده|لینک|موجود|موجودی|مقایسه|"
    r"بهترین|پیشنهاد|چی\s*بخر|چه\s*بخر|buy|price|shop|seller|link|"
    r"available|compare|cheapest|budget|best)",
    re.I,
)

# Budget / price-ceiling language — common without the word «خرید» or «قیمت».
# Examples:
#   «تا ۵۰ میلیون»، «زیر ۳۰ میلیون»، «بودجه ۱۵ تومن»، «حداکثر ۲۰ میلیون تومان»
_BUDGET_RE = re.compile(
    r"(?:"
    r"(?:تا|زیر|حداکثر|حدود|حد|بودجه)\s*"
    r"[0-9۰-۹٠-٩]+(?:[.,٬]?[0-9۰-۹٠-٩]+)?\s*"
    r"(?:میلیون|م|هزار|تومان|تومن)?"
    r"|"
    r"[0-9۰-۹٠-٩]+(?:[.,٬]?[0-9۰-۹٠-٩]+)?\s*"
    r"(?:میلیون|م)\s*(?:تومان|تومن)?"
    r")",
    re.I,
)

# Explicit shopping keywords (strong signal).
_EXPLICIT_SHOP_RE = re.compile(
    r"(?:قیمت|خرید|فروشگاه|فروشنده|لینک\s*خرید|مقایسه\s*(?:قیمت|محصول)|"
    r"ارزان(?:\s*ترین)?|اقتصادی|cheapest|buy|shop|seller|price)\b",
    re.I,
)


def _normalize(text: str) -> str:
    s = str(text or "").strip()
    s = s.replace("ي", "ی").replace("ك", "ک")
    s = re.sub(r"[\u200c\u200f\u200e]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s


def is_live_product_request(text: str) -> bool:
    """Return True only for a real product-shopping/price/budget request."""
    s = _normalize(text)
    if not s or _MARKET_RE.search(s):
        return False

    has_object = bool(_PRODUCT_OBJECT_RE.search(s))
    has_action = bool(_PRODUCT_ACTION_RE.search(s))
    has_budget = bool(_BUDGET_RE.search(s))
    has_explicit = bool(_EXPLICIT_SHOP_RE.search(s))

    # Explicit shopping language is enough unless it is clearly non-product.
    if has_explicit and (has_object or len(s.split()) >= 2):
        return True

    # Recommendation-style: product object + action verb.
    if has_object and has_action:
        return True

    # Budget-style without «خرید/قیمت»:
    # «یه گوشی شیائومی تا ۵۰ میلیون تومان»
    # «لپ‌تاپ تا ۳۰ میلیون»
    if has_object and has_budget:
        return True

    return False


def _shopping_query(text: str) -> str:
    """Remove request verbs but preserve product/model/specs and budget numbers."""
    s = _normalize(text)
    # Do NOT strip budget markers (تا/زیر/میلیون/تومان) so search_shopping
    # can detect max_price via its own _budget() helper.
    s = re.sub(
        r"(?:لطفاً|لطفا|میشه|میشه\s*بگی|ببین|برام|برای\s*من|میخوام|می\s*خوام|"
        r"قیمت|نرخ|چنده|چقدر|خرید|بخرم|بخریم|بخر|فروشگاه|فروشنده|لینک|محصول|"
        r"ارزان(?:\s*ترین)?|اقتصادی|بهترین|پیشنهاد|مقایسه|موجودی|موجود|"
        r"چی\s*بخرم|چه\s*بخرم|buy|price|shop|seller|link|cheapest|best|"
        r"compare|available)",
        " ",
        s,
        flags=re.I,
    )
    s = re.sub(r"[؟?!,:;]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


async def run_live_product_search(update, user_id: int, text: str) -> bool:
    """Run the real shopping engine and always consume the request."""
    query = _shopping_query(text)
    if len(query) < 2:
        await update.message.reply_text(
            "⚠️ نام یا مدل محصول برای استعلام قیمت مشخص نیست."
        )
        return True

    notice = await update.message.reply_text(
        "🔎 در حال استعلام زنده قیمت و فروشنده‌ها..."
    )
    try:
        from bot.features.market.shopping import search_shopping

        result = await search_shopping(
            query,
            source="all",
            max_results=8,
            user_id=user_id,
        )
        # search_shopping never delegates to AI. Even when no price is found it
        # returns real links or an explicit no-result message.
        await update.message.reply_text(result)
    except Exception:
        from bot.logger import logger
        logger.exception(
            "live product search failed for user=%s query=%r", user_id, query
        )
        await update.message.reply_text(
            "⚠️ استعلام زنده قیمت فعلاً در دسترس نیست؛ قیمت حدسی ارائه نمی‌کنم."
        )
    finally:
        try:
            await notice.delete()
        except Exception:
            pass
    return True
