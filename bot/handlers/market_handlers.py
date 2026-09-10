"""Domain-specific Telegram handlers. Compatibility-preserving extraction from feature_handlers."""
from __future__ import annotations
import re
from bot.utils.helpers import get_market_keyboard
from bot.features.market.finance import profit_loss, parse_profit, analyze_crypto, get_crypto_chart, get_crypto_analysis_keyboard, register_price_alert, calc_position_size

async def _h_profit(u, c, t, uid):
    c.user_data.pop("waiting_for", None)
    p = parse_profit(t)
    await u.message.reply_text(profit_loss(*p) if p else "❌", reply_markup=get_market_keyboard())

async def _h_currency(u, c, t, uid):
    c.user_data.pop("waiting_for", None)
    from bot.features.market.finance import parse_currency_input, SYMBOL_TO_ID, convert_currency as smart_convert
    parsed = parse_currency_input(t)
    if not parsed:
        await u.message.reply_text(
            "❌ مثال:\n"
            "• `20 ton` یا `۱.۵ بیتکوین`\n"
            "• `100 دلار` یا `۵۰ تتر`\n"
            "• `50000 تومان دلار`\n"
            "• `1 btc eth`\n"
            "• `100 usdt toman`",
            reply_markup=get_market_keyboard(),
        )
        return
    amount, a, b = parsed
    try:
        result = await smart_convert(amount, a or "usd", b or "")
        await u.message.reply_text(result, reply_markup=get_market_keyboard())
    except Exception as e:
        await u.message.reply_text(f"⚠️ خطا در تبدیل: {e}", reply_markup=get_market_keyboard())

async def _send_long_analysis(message, text, reply_markup):
    """ارسال کامل تحلیل بدون بریدن متن و با parse_mode تلگرام."""
    text = (text or "❌ داده‌ای برای تحلیل دریافت نشد.").strip()
    limit = 3800
    chunks = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut < 500:
            cut = text.rfind(" ", 0, limit)
        if cut < 500:
            cut = limit
        chunks.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    chunks.append(text)

    for i, chunk in enumerate(chunks):
        await message.reply_text(
            chunk,
            parse_mode="HTML",
            reply_markup=reply_markup if i == len(chunks) - 1 else None,
            disable_web_page_preview=True,
        )

async def _h_crypto_full(u, c, t, uid):
    """تحلیل کامل + منوی دکمه‌ای زیرش (مثل Algo Analyzer)"""
    c.user_data.pop("waiting_for", None)
    raw = (t or "").strip().translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
    parts = [p for p in raw.replace(",", " ").split() if p]
    symbol = ""
    days = 30
    for p in parts:
        pl = p.lower()
        if pl.replace(".", "", 1).isdigit():
            try:
                days = max(1, min(365, int(float(p))))
            except Exception:
                pass
        elif pl not in ("روز", "day", "days", "نمودار", "chart", "تحلیل", "analyze", "ارز"):
            if not symbol:
                symbol = p
    if not symbol and parts:
        symbol = parts[0]
    if not symbol:
        await u.message.reply_text(
            "❌ نماد را بفرستید. مثال: `btc` یا `eth 30`",
            reply_markup=get_market_keyboard(),
        )
        return

    symbol = symbol.lower().replace("usdt", "").strip()
    c.user_data["crypto_symbol"] = symbol
    wait = await u.message.reply_text(f"⏳ تحلیل {symbol.upper()}...")

    report = ""
    png = None
    try:
        import asyncio as _aio
        chart_task = _aio.create_task(get_crypto_chart(symbol, days))
        report = await analyze_crypto(symbol, ai_summary="", ai_guide="")
        try:
            png, _ = await chart_task
        except Exception:
            png = None
    except Exception as e:
        report = f"⚠️ خطا در تحلیل: {e}"

    try:
        await wait.delete()
    except Exception:
        pass

    menu = get_crypto_analysis_keyboard(symbol)
    # یک پیام واحد (عکس+تحلیل+منو) تا دکمه‌ها همان را ویرایش کنند
    body = (report or "❌ داده نبود.")
    if png:
        try:
            from io import BytesIO
            bio = BytesIO(png)
            bio.name = f"{symbol}_analysis.png"
            # کپشن عکس محدود است؛ تحلیل کامل را جداگانه و بدون قطع شدن می‌فرستیم.
            await u.message.reply_photo(
                photo=bio,
                caption=f"📈 نمودار تحلیل {symbol.upper()}",
            )
            await _send_long_analysis(u.message, body, menu)
        except Exception as e:
            await _send_long_analysis(u.message, body + f"\n\n⚠️ نمودار: {e}", menu)
    else:
        await _send_long_analysis(u.message, body, menu)

async def _h_crypto_pos(u, c, t, uid):
    """پاسخ به ورودی سایز پوزیشن یا قیمت هشدار"""
    mode = c.user_data.pop("waiting_for", None)
    sym = c.user_data.get("crypto_symbol") or "btc"
    if mode == "crypto_pos":
        await u.message.reply_text(calc_position_size(t), reply_markup=get_crypto_analysis_keyboard(sym))
        return
    if mode == "crypto_alert":
        raw = (t or "").translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
        nums = re.findall(r"[\d]+(?:\.\d+)?", raw)
        if not nums:
            await u.message.reply_text("❌ قیمت معتبر بفرستید. مثال: 64000")
            c.user_data["waiting_for"] = "crypto_alert"
            return
        price = float(nums[0])
        msg = await register_price_alert(uid, sym, price)
        await u.message.reply_text(msg, reply_markup=get_crypto_analysis_keyboard(sym))
        return

async def _h_crypto_chart(u, c, t, uid):
    return await _h_crypto_full(u, c, t, uid)

async def _h_crypto_analyze(u, c, t, uid):
    return await _h_crypto_full(u, c, t, uid)

async def _h_economic_calendar(u, c, t, uid):
    """تقویم اقتصادی زنده + تحلیل هوشمند فارسی."""
    c.user_data.pop("waiting_for", None)
    from bot.features.market.economic_calendar import get_calendar_for_user, calendar_text, get_calendar_keyboard
    try:
        events, tz_name = await get_calendar_for_user(uid, "today", "all")
        text = calendar_text(events, title="تقویم اقتصادی امروز", tz_name=tz_name)
        await u.message.reply_text(text, parse_mode="HTML", reply_markup=get_calendar_keyboard(uid, events=events))
    except Exception as e:
        await u.message.reply_text(f"⚠️ تقویم اقتصادی فعلاً در دسترس نیست.\n{e}", reply_markup=get_market_keyboard())
