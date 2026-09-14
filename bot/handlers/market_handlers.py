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

    # Keyboard construction/sending must never turn a successful analysis
    # into the generic "خطا در پردازش" response.  If Telegram rejects a
    # callback/markup, the analysis itself is still useful without a keyboard.
    try:
        menu = get_crypto_analysis_keyboard(symbol)
    except Exception:
        from bot.logger import logger
        logger.exception("crypto keyboard build failed for %s", symbol)
        menu = None

    # نمودار هرگز با caption بلند ارسال نمی‌شود؛ متن تحلیل جدا و کامل می‌ماند.
    if png:
        try:
            bio = BytesIO(png)
            bio.name = f"{symbol}_analysis.png"
            chart_msg = await u.message.reply_photo(
                photo=bio, caption=f"📈 <b>نمودار تحلیل {html.escape(symbol.upper())}</b>", parse_mode="HTML"
            )
            c.user_data["market_chart_message_id"] = chart_msg.message_id
            c.user_data["market_chart_chat_id"] = u.effective_chat.id
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
        # گزارش تحلیل خودش شامل تگ‌های Telegram HTML مثل <b>/<code> است.
        # بعد از escape کردن متن، فقط همین تگ‌های مجاز را برمی‌گردانیم تا
        # تگ‌ها به‌صورت خام (مثل <b>) به کاربر نمایش داده نشوند.
        for _tag in ("b", "/b", "code", "/code", "i", "/i", "u", "/u", "s", "/s"):
            esc = esc.replace(f"&lt;{_tag}&gt;", f"<{_tag}>")
        if raw_line.startswith("▎") or raw_line[:2].rstrip().isdigit():
            return f"<b>{esc}</b>"
        if raw_line.startswith(("🧠", "📊", "⏱", "🎯", "🧪", "🔬", "🌐")) and ":" not in raw_line:
            return f"<b>{esc}</b>"
        return esc

    # متن تحلیل کاملاً جدا از تصویر ارسال می‌شود؛ کیبورد فقط زیر آخرین پیام متن است.
    def _split_report(text: str, limit: int = 3900) -> list[str]:
        raw = (text or "").strip()
        if not raw:
            return ["داده کافی برای تحلیل در دسترس نیست."]
        out, current = [], ""
        for line in raw.splitlines():
            candidate = line if not current else current + "\n" + line
            if len(candidate) <= limit:
                current = candidate
                continue
            if current:
                out.append(current)
                current = ""
            rest = line
            while len(rest) > limit:
                cut = rest.rfind(" ", 0, limit + 1)
                if cut < max(1, limit // 2):
                    cut = limit
                out.append(rest[:cut].rstrip())
                rest = rest[cut:].lstrip()
            current = rest
        if current:
            out.append(current)
        return out or ["داده کافی برای تحلیل در دسترس نیست."]

    chunks = _split_report(report)
    text_ids = []
    for i, chunk in enumerate(chunks):
        is_last = i == len(chunks) - 1
        markup = menu if is_last else None
        try:
            mtxt = await u.message.reply_text(chunk, parse_mode="HTML", reply_markup=markup)
        except Exception:
            plain = re.sub(r"<[^>]+>", "", chunk)
            try:
                mtxt = await u.message.reply_text(plain[:3900], reply_markup=markup)
            except Exception:
                # A bad inline keyboard must not suppress the actual report.
                mtxt = await u.message.reply_text(plain[:3900], reply_markup=None)
        text_ids.append(mtxt.message_id)
    c.user_data["market_analysis_text_ids"] = text_ids
    c.user_data["market_analysis_chat_id"] = u.effective_chat.id

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


async def _h_ict(u, c, t, uid):
    """تحلیل ICT برای نماد درخواستی."""
    from bot.features.market.finance_ict import analyze_ict
    from bot.utils.keyboard_factory import get_market_keyboard
    text = (t or "").strip()
    if not text or text in ("📐 تحلیل ICT", "تحلیل ICT", "ICT", "ict"):
        c.user_data["waiting_for"] = "ict_analyze"
        await u.message.reply_text(
            "📐 تحلیل به روش ICT\n\n"
            "نماد را بفرستید، مثلاً:\n"
            "• btc\n• eth\n• sol\n• btc 4h\n• eth 1h\n\n"
            "تایم‌فریم اختیاری: 15m / 1h / 4h / 1d",
            reply_markup=get_market_keyboard(),
        )
        return
    parts = text.replace("،", " ").split()
    symbol = parts[0] if parts else "btc"
    interval = "1h"
    for p in parts[1:]:
        pl = p.lower()
        if pl in ("15m", "15", "1h", "4h", "1d", "1day", "daily", "hour", "h1", "h4"):
            interval = {
                "15": "15m", "15m": "15m",
                "1h": "1h", "hour": "1h", "h1": "1h",
                "4h": "4h", "h4": "4h",
                "1d": "1d", "1day": "1d", "daily": "1d",
            }.get(pl, "1h")
    c.user_data.pop("waiting_for", None)
    progress = await u.message.reply_text("⏳ در حال تحلیل ICT...")
    try:
        report = await analyze_ict(symbol, interval=interval)
    except Exception:
        from bot.logger import logger
        logger.exception("ICT analysis failed for %s/%s", symbol, interval)
        report = "❌ تحلیل ICT فعلاً در دسترس نیست؛ دوباره تلاش کنید."

    # Telegram hard limit is 4096 chars. Keep a safety margin and, crucially,
    # reuse the same message IDs on subsequent ICT/Smart updates instead of
    # deleting/re-sending every chunk.
    import asyncio
    import re as _re

    def _split_long(text: str, limit: int = 3900) -> list[str]:
        raw = (text or "").strip()
        if not raw:
            return ["داده کافی نیست."]
        out, cur = [], ""
        for line in raw.splitlines():
            candidate = line if not cur else cur + "\n" + line
            if len(candidate) <= limit:
                cur = candidate
                continue
            if cur:
                out.append(cur)
                cur = ""
            rest = line
            while len(rest) > limit:
                cut = rest.rfind(" ", 0, limit + 1)
                if cut < max(1, limit // 2):
                    cut = limit
                out.append(rest[:cut].rstrip())
                rest = rest[cut:].lstrip()
            cur = rest
        if cur:
            out.append(cur)
        return out or ["داده کافی نیست."]

    lock = c.user_data.get("_market_analysis_update_lock")
    if lock is None:
        lock = asyncio.Lock()
        c.user_data["_market_analysis_update_lock"] = lock

    async with lock:
        old_ids = list(c.user_data.get("market_analysis_text_ids") or [])
        chat_id = c.user_data.get("market_analysis_chat_id") or u.effective_chat.id
        chunks = _split_long(report)
        ids = []
        for i, chunk in enumerate(chunks):
            old_id = old_ids[i] if i < len(old_ids) else None
            if old_id is not None:
                try:
                    await c.bot.edit_message_text(
                        chat_id=chat_id, message_id=old_id, text=chunk,
                        parse_mode="HTML", reply_markup=None
                    )
                    ids.append(old_id)
                    continue
                except Exception:
                    pass
            try:
                m = await c.bot.send_message(
                    chat_id=chat_id, text=chunk, parse_mode="HTML",
                    reply_markup=get_market_keyboard() if i == len(chunks) - 1 else None,
                )
            except Exception:
                m = await c.bot.send_message(
                    chat_id=chat_id, text=_re.sub(r"<[^>]*>", "", chunk),
                    reply_markup=get_market_keyboard() if i == len(chunks) - 1 else None,
                )
            ids.append(m.message_id)

        for old_id in old_ids[len(chunks):]:
            try:
                await c.bot.delete_message(chat_id=chat_id, message_id=old_id)
            except Exception:
                pass

        for msg_id in ids[:-1]:
            try:
                await c.bot.edit_message_reply_markup(
                    chat_id=chat_id, message_id=msg_id, reply_markup=None
                )
            except Exception:
                pass
        try:
            await c.bot.edit_message_reply_markup(
                chat_id=chat_id, message_id=ids[-1], reply_markup=get_market_keyboard()
            )
        except Exception:
            pass

        c.user_data["market_analysis_text_ids"] = ids
        c.user_data["market_analysis_chat_id"] = chat_id

    try:
        await progress.delete()
    except Exception:
        pass


