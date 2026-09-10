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

async def _h_crypto_full(u, c, t, uid):
    """تحلیل کامل کریپتو با ارسال امن نمودار و متن کامل در چند پیام."""
    import asyncio as _aio
    import html
    from io import BytesIO

    c.user_data.pop("waiting_for", None)
    raw = (t or "").strip().translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
    parts = [p for p in raw.replace(",", " ").split() if p]
    symbol, days = "", 30
    for p in parts:
        pl = p.lower()
        if pl.replace(".", "", 1).isdigit():
            try:
                days = max(1, min(365, int(float(p))))
            except Exception:
                pass
        elif pl not in ("روز", "day", "days", "نمودار", "chart", "تحلیل", "analyze", "ارز") and not symbol:
            symbol = p
    if not symbol and parts:
        symbol = parts[0]
    if not symbol:
        await u.message.reply_text("❌ نماد را بفرستید. مثال: btc یا eth 30", reply_markup=get_market_keyboard())
        return

    symbol = symbol.lower().replace("usdt", "").strip()
    c.user_data["crypto_symbol"] = symbol
    wait = await u.message.reply_text(f"⏳ در حال دریافت تحلیل {symbol.upper()}...")
    chart_task = _aio.create_task(get_crypto_chart(symbol, days))
    try:
        report = await analyze_crypto(symbol, ai_summary="", ai_guide="")
    except Exception as e:
        from bot.logger import logger
        logger.exception("crypto analysis failed for %s", symbol)
        report = f"❌ تحلیل {symbol.upper()} با خطا مواجه شد: {e}"

    png = None
    try:
        png, chart_note = await chart_task
    except Exception as e:
        chart_note = f"⚠️ نمودار در دسترس نیست: {e}"

    try:
        await wait.delete()
    except Exception:
        pass

    menu = get_crypto_analysis_keyboard(symbol)

    # نمودار هرگز با caption بلند ارسال نمی‌شود؛ متن تحلیل جدا و کامل می‌ماند.
    if png:
        try:
            bio = BytesIO(png)
            bio.name = f"{symbol}_analysis.png"
            await u.message.reply_photo(photo=bio, caption=f"📈 <b>نمودار تحلیل {html.escape(symbol.upper())}</b>", parse_mode="HTML")
        except Exception as e:
            chart_note = f"⚠️ ارسال نمودار ناموفق بود: {e}"
    if chart_note and not png:
        try:
            await u.message.reply_text(chart_note[:3500])
        except Exception:
            pass

    def render(line: str) -> str:
        raw_line = line.strip()
        if not raw_line:
            return ""
        esc = html.escape(raw_line)
        if raw_line.startswith("▎") or raw_line[:2].rstrip().isdigit():
            return f"<b>{esc}</b>"
        if raw_line.startswith(("🧠", "📊", "⏱", "🎯", "🧪", "🔬", "🌐")) and ":" not in raw_line:
            return f"<b>{esc}</b>"
        return esc

    # بخش‌ها را در پیام‌های حداکثر ~3500 کاراکتری HTML می‌شکنیم.
    lines = [render(x) for x in (report or "❌ داده‌ای برای تحلیل دریافت نشد.").splitlines()]
    chunks, current = [], ""
    for line in lines:
        candidate = (current + "\n" + line).strip() if current else line
        if len(candidate) > 3400 and current:
            chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)

    if not chunks:
        chunks = ["❌ داده‌ای برای تحلیل دریافت نشد."]
    for i, chunk in enumerate(chunks):
        kwargs = {"parse_mode": "HTML"}
        if i == len(chunks) - 1:
            kwargs["reply_markup"] = menu
        try:
            await u.message.reply_text(chunk, **kwargs)
        except Exception:
            # اگر HTML به هر دلیل نامعتبر بود، متن ساده را کامل و امن بفرست.
            plain = re.sub(r"<[^>]+>", "", chunk)
            await u.message.reply_text(plain[:3500], reply_markup=menu if i == len(chunks)-1 else None)

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
