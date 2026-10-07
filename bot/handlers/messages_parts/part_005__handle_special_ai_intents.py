"""Live product-price gate used by the real messages handler.

This module intentionally contains only the product-shopping interception logic.
The actual handler in ``part_999_core_legacy.py`` imports it before generic AI.
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
# «قیمت آیفون ۱۸ پرو مکس چنده؟», «ارزان‌ترین لپ‌تاپ»، «چه خمیر سیلیکونی بخرم؟».
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

_GENERIC_PRODUCT_RE = re.compile(
    r"(?:جوراب|کفش|کتانی|صندل|لباس|پیراهن|شلوار|مانتو|کت|کاپشن|هودی|سویشرت|"
    r"کیف|کوله|کیف پول|کمربند|عینک|ساعت|گردنبند|دستبند|انگشتر|عطر|ادکلن|"
    r"کتاب|دفتر|خودکار|لوازم تحریر|اسباب بازی|هدیه|ظرف|لیوان|ماگ|قاب|چراغ|"
    r"مبل|صندلی|میز|فرش|پتو|بالش|ملحفه|لوازم آشپزخانه|ظرفشویی|جارو|"
    r"لوازم آرایشی|کرم|شامپو|محصول|product)", re.I)

_PRODUCT_ACTION_RE = re.compile(
    r"(?:قیمت|نرخ|چنده|چقدر|چند(?:ه|ه؟)|ارزان(?:ترین)?|اقتصادی|"
    r"خرید|بخرم|بخریم|فروشگاه|فروشنده|لینک|موجود|موجودی|مقایسه|"
    r"بهترین|پیشنهاد|buy|price|shop|seller|link|available|compare|"
    r"cheapest|budget|best)",
    re.I,
)


def _normalize(text: str) -> str:
    s = str(text or "").strip()
    s = s.replace("ي", "ی").replace("ك", "ک")
    s = re.sub(r"[\u200c\u200f\u200e]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s


def is_live_product_request(text: str) -> bool:
    """Return True only for a real product-shopping/price request."""
    s = _normalize(text)
    if not s or _MARKET_RE.search(s):
        return False

    # Explicit shopping language is enough unless it is clearly a non-product
    # request. This covers generic products not present in the keyword list.
    explicit = re.search(
        r"(?:قیمت|خرید|فروشگاه|فروشنده|لینک\s*خرید|مقایسه\s*(?:قیمت|محصول)|"
        r"ارزان(?:\s*ترین)?|اقتصادی|cheapest|buy|shop|seller|price)\b",
        s,
        re.I,
    )
    if explicit and (_PRODUCT_OBJECT_RE.search(s) or len(s.split()) >= 2):
        return True

    # Recommendation-style shopping without the word «قیمت».
    if _PRODUCT_OBJECT_RE.search(s) and (_PRODUCT_ACTION_RE.search(s) or re.search(r"(?:تا|زیر|حداکثر|بودجه)\s*[0-9۰-۹]+\s*(?:میلیون|م|تومان|تومن)?", s, re.I)):
        return True

    # Generic catalog requests such as «یه جوراب مردانه پیدا کن برام» do not
    # contain the word «خرید» and therefore must bypass generic AI.
    generic_request = re.search(
        r"(?:یه|یک|چند|یه\s*دونه)?\s*(?:.*)\s*(?:پیدا\s*کن|برام\s*پیدا|بگرد|جستجو\s*کن)",
        s, re.I,
    )
    if generic_request and _GENERIC_PRODUCT_RE.search(s):
        return True

    return False


def _shopping_query(text: str) -> str:
    """Remove request verbs but preserve the actual product/model/specs."""
    s = _normalize(text)
    s = re.sub(
        r"(?:لطفاً|لطفا|میشه|میشه\s*بگی|ببین|برام|برای\s*من|میخوام|می\s*خوام|"
        r"قیمت|نرخ|چنده|چقدر|خرید|بخرم|بخریم|فروشگاه|فروشنده|لینک|محصول|"
        r"ارزان(?:\s*ترین)?|اقتصادی|بهترین|پیشنهاد|مقایسه|موجودی|موجود|"
        r"buy|price|shop|seller|link|cheapest|budget|best|compare|available)",
        " ",
        s,
        flags=re.I,
    )
    s = re.sub(r"[؟?!,:;]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


async def run_live_product_search(update, user_id: int, text: str) -> bool:
    """Run the real shopping engine and always consume the request."""
    # Natural-language price alert: «اگر جوراب زیر ۱۰۰ هزار شد خبرم کن».
    alert_match = re.search(r"(?:اگر|وقتی|هر وقت)\s+(.+?)\s+(?:زیر|کمتر از|به کمتر از)\s*([0-9۰-۹.,]+)\s*(میلیون|م|هزار|تومان|تومن)?", _normalize(text), re.I)
    if alert_match and re.search(r"خبرم|اطلاع|هشدار|بگو", _normalize(text), re.I):
        raw_target = alert_match.group(2).replace(',', '').replace('٬', '')
        try:
            target = float(raw_target)
            unit = (alert_match.group(3) or '').lower()
            if 'میلیون' in unit or unit == 'م': target *= 1_000_000
            elif 'هزار' in unit: target *= 1_000
            target = int(target)
            q = _shopping_query(alert_match.group(1))
            from bot.features.market.shopping import create_shopping_price_alert
            msg = create_shopping_price_alert(user_id, q, target)
            await update.message.reply_text(msg)
            return True
        except Exception:
            pass

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
        logger.exception("live product search failed for user=%s query=%r", user_id, query)
        await update.message.reply_text(
            "⚠️ استعلام زنده قیمت فعلاً در دسترس نیست؛ قیمت حدسی ارائه نمی‌کنم."
        )
    finally:
        try:
            await notice.delete()
        except Exception:
            pass
    return True
