"""finance: tools responsibilities."""
from .finance_common import *  # noqa: F401,F403
from . import finance_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


async def get_crypto_analysis_short(symbol: str) -> str:
    """نسخه کوتاه‌تر برای ابزار AI"""
    return await analyze_crypto(symbol)

async def market_scanner(limit: int = 10) -> str:
    """اسکن سریع نمادهای برتر از نظر ستاپ MTF"""
    symbols = [
        "btc", "eth", "bnb", "sol", "xrp", "doge", "ada", "avax", "link", "dot",
        "ton", "near", "sui", "ltc", "atom", "uni", "apt", "fil", "arb", "op",
    ]
    rows = []
    for sym in symbols:
        try:
            pair = _pair_from_symbol(sym)
            mtf = await _mtf_bundle(pair)
            conv, power = _mtf_convergence(mtf)
            sc = mtf.get("scores") or {}
            di = mtf.get("dirs") or {}
            # فقط اگر force_wait نباشد و امتیاز 4H خوب باشد
            if mtf.get("force_wait"):
                continue
            score4 = sc.get("4H") or 0
            if score4 < 6:
                continue
            direction = di.get("4H") or "—"
            rows.append((power, score4, sym.upper(), direction, conv, sc))
        except Exception:
            continue
    rows.sort(key=lambda x: (x[0], x[1]), reverse=True)
    rows = rows[:limit]
    lines = [
        "🔍 اسکنر بازار — ستاپ‌های برتر",
        "────────────────────",
    ]
    if not rows:
        lines.append("الان ستاپ قوی هم‌راستا پیدا نشد (بازار رنج یا ADX ضعیف).")
    else:
        for i, (power, score4, sym, direction, conv, sc) in enumerate(rows, 1):
            lines.append(
                f"{i}. {sym} | {direction} | قدرت {power}/10 | 4H:{score4} 1H:{sc.get('1H','—')} 1D:{sc.get('1D','—')}"
            )
            lines.append(f"   {conv}")
    lines.append("")
    lines.append("⚠️ آموزشی است؛ قبل از ورود خودت تأیید کن.")
    return chr(10).join(lines)

def get_crypto_analysis_keyboard(symbol: str) -> "InlineKeyboardMarkup":
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    s = (symbol or "btc").lower().replace("usdt", "").strip()
    rows = [
            [
                InlineKeyboardButton("📅 تحلیل و نمودار روزانه", callback_data=f"cx:day:{s}"),
                InlineKeyboardButton("⏰ تحلیل و نمودار ساعتی", callback_data=f"cx:hr:{s}"),
            ],
            [InlineKeyboardButton("🕓 تحلیل و نمودار 4 ساعته", callback_data=f"cx:4h:{s}")],
    ]
    if s in ("gold", "xau", "xauusd", "xau/usd"):
        rows.append([InlineKeyboardButton("🕒 تحلیل 15 دقیقه‌ای طلا", callback_data="cx:15m:gold")])
    else:
        rows.append([InlineKeyboardButton("🕒 تحلیل و نمودار 15 دقیقه‌ای", callback_data=f"cx:15m:{s}")])
    rows += [
            [
                InlineKeyboardButton("🎯 توصیه معاملاتی", callback_data=f"cx:rec:{s}"),
                InlineKeyboardButton("📡 رادار مشتقات", callback_data=f"cx:der:{s}"),
            ],
            [
                InlineKeyboardButton("🎲 ریسک و سناریوها", callback_data=f"cx:risk:{s}"),
                InlineKeyboardButton("🔍 اسکنر بازار", callback_data=f"cx:scan:{s}"),
            ],
            [
                InlineKeyboardButton("📐 سایز پوزیشن", callback_data=f"cx:pos:{s}"),
                InlineKeyboardButton("🔔 هشدار ورود", callback_data=f"cx:al:{s}"),
            ],
            [InlineKeyboardButton("🧠 تحلیل هوشمند حرفه‌ای", callback_data=f"cx:ai:{s}")],
            [InlineKeyboardButton("📐 تحلیل ICT", callback_data=f"cx:ict:{s}")],
            [InlineKeyboardButton("🔄 بروزرسانی تحلیل", callback_data=f"cx:ref:{s}")],
        ]
    return InlineKeyboardMarkup(rows)

def _pair_from_symbol(symbol: str) -> str:
    symbol_clean = (symbol or "btc").lower().strip().replace(" ", "").replace("‌", "")
    for junk in ("تحلیل", "analyze", "ارز", "کریپتو", "usdt"):
        symbol_clean = symbol_clean.replace(junk, "")
    symbol_clean = symbol_clean.strip() or "btc"
    _sym_map = {
        "bitcoin": "BTC", "ethereum": "ETH", "binancecoin": "BNB", "solana": "SOL",
        "ripple": "XRP", "the-open-network": "TON", "dogecoin": "DOGE", "cardano": "ADA",
        "tron": "TRX", "chainlink": "LINK", "litecoin": "LTC", "polkadot": "DOT",
        "avalanche-2": "AVAX", "shiba-inu": "SHIB", "matic-network": "MATIC",
        "near": "NEAR", "pepe": "PEPE", "sui": "SUI", "btc": "BTC", "eth": "ETH",
        "sol": "SOL", "ton": "TON", "bnb": "BNB", "xrp": "XRP", "doge": "DOGE",
    }
    base = _sym_map.get(symbol_clean, symbol_clean.upper())
    if len(base) > 10:
        base = symbol_clean.upper()[:10]
    return base + "USDT"

async def trading_recommendation(symbol: str) -> str:
    """توصیه معاملاتی + حد ضرر پویا بر اساس ATR + فیلتر MTF"""
    pair = _pair_from_symbol(symbol)
    mtf = await _mtf_bundle(pair)
    binance = await _fetch_binance_futures(symbol)
    fg = await _fetch_fear_greed(7)

    ta = mtf.get("4h") or mtf.get("1h") or {}
    klines = await _fetch_klines_interval(pair, "4h", 120)
    opens, highs, lows, closes, vols = [], [], [], [], []
    for k in klines or []:
        try:
            opens.append(float(k[1]))
            highs.append(float(k[2]))
            lows.append(float(k[3]))
            closes.append(float(k[4]))
            vols.append(float(k[5]))
        except Exception:
            continue
    if len(closes) >= 30 and not ta:
        ta = _compute_ta(closes, highs, lows, vols)
        ta["atr"] = _atr(highs, lows, closes, 14)
        ta["patterns"] = _detect_candle_patterns(opens, highs, lows, closes)

    cur = closes[-1] if closes else None
    support, resistance = _support_resistance(closes, highs, lows, cur)
    signal, sem, score, rr, risk, status = _derive_signal(
        ta, None, binance or {}, current=cur, support=support, resistance=resistance
    )

    if mtf.get("force_wait"):
        signal, sem = "خنثی / احتیاط", "🟡"
        status = "صبر کنید ❌ — ADX روزانه ضعیف"
        score = min(score, 5)

    atr = ta.get("atr") or (_atr(highs, lows, closes, 14) if len(closes) > 20 else None)
    atr_mult = 1.5
    tp2 = None
    if "لانگ" in signal and support:
        entry = support
        stop = (entry - atr_mult * atr) if atr else entry * 0.985
        tp1 = resistance or ((entry + 2 * atr_mult * atr) if atr else entry * 1.03)
        tp2 = (entry + 3 * atr_mult * atr) if atr else None
    elif "شورت" in signal and resistance:
        entry = resistance
        stop = (entry + atr_mult * atr) if atr else entry * 1.015
        tp1 = support or ((entry - 2 * atr_mult * atr) if atr else entry * 0.97)
        tp2 = (entry - 3 * atr_mult * atr) if atr else None
    else:
        entry = cur
        stop = (cur - atr_mult * atr) if (cur and atr) else (cur * 0.98 if cur else None)
        tp1 = (cur + 2 * atr_mult * atr) if (cur and atr) else (cur * 1.02 if cur else None)

    def f(v):
        if v is None:
            return "—"
        try:
            v = float(v)
        except Exception:
            return "—"
        return f"{v:,.2f}" if abs(v) >= 1 else f"{v:,.6f}"

    rr_txt = rr
    try:
        if entry and stop and tp1 and entry != stop:
            risk_d = abs(float(entry) - float(stop))
            reward = abs(float(tp1) - float(entry))
            if risk_d > 0:
                rr_txt = f"{reward / risk_d:.1f} : 1"
    except Exception:
        pass

    out = [
        f"🎯 توصیه معاملاتی — {pair}",
        "────────────────────",
        f"سیگنال: {signal} {sem}",
        f"امتیاز ستاپ: {score}/10",
        f"وضعیت: {status}",
        f"ریسک: {risk} | R:R: {rr_txt}",
        "",
        "⏱ تایم‌فریم‌ها:",
    ]
    for k in ("1H", "4H", "1D"):
        out.append(
            f"  {k}: {(mtf.get('scores') or {}).get(k, '—')}/10 | {(mtf.get('dirs') or {}).get(k, '—')}"
        )
    if mtf.get("conflict"):
        out.append("⚠️ تضاد تایم‌فریم — حجم را کم کنید")
    if mtf.get("force_wait"):
        out.append("⚠️ فیلتر ADX روزانه: صبر اولویت دارد")

    out += [
        "",
        f"📍 ورود تقریبی: {f(entry)}",
        f"🛑 حد ضرر (ATR×{atr_mult}): {f(stop)}",
        f"🎯 هدف ۱: {f(tp1)}",
    ]
    if tp2:
        out.append(f"🎯 هدف ۲: {f(tp2)}")
    if atr:
        out.append(f"📐 ATR(14): {f(atr)}")
    pats = ta.get("patterns") or []
    if pats:
        out.append("🕯 الگو: " + " | ".join(pats[:2]))
    out.append("")
    out.extend(_format_fear_greed(fg))
    out.append("")
    out.append("نکته: ورود پله‌ای؛ حد ضرر را جابه‌جا نکنید.")
    out.append("⚠️ آموزشی است؛ توصیه سرمایه‌گذاری قطعی نیست.")
    return chr(10).join(out)

async def derivatives_radar(symbol: str) -> str:
    """رادار مشتقات: Funding, OI, حجم فیوچرز"""
    pair = _pair_from_symbol(symbol)
    base = pair.replace("USDT", "")
    data = await _fetch_binance_futures(symbol)
    lines = [
        f"📡 رادار مشتقات — {pair}",
        "────────────────────",
    ]
    if not data:
        lines.append("❌ داده فیوچرز در دسترس نیست (ممکن است نماد فیوچرز نداشته باشد).")
        return "\n".join(lines)

    fr = data.get("funding_rate")
    if fr is not None:
        em = "🟢" if fr > 0 else "🔴" if fr < 0 else "⚪"
        lines.append(f"Funding Rate: {em} {fr:+.4f}%")
        if fr > 0.03:
            lines.append("  → لانگ‌ها هزینه می‌دهند؛ احتمال اصلاح/فشار فروش")
        elif fr < -0.03:
            lines.append("  → شورت‌ها هزینه می‌دهند؛ احتمال اسکوییز صعودی")
        else:
            lines.append("  → فاندینگ متعادل")
    if data.get("open_interest"):
        lines.append(f"Open Interest: {data['open_interest']:,.0f}")
    if data.get("volume_24h"):
        lines.append(f"حجم فیوچرز ۲۴س: ${data['volume_24h']:,.0f}")
    if data.get("mark_price"):
        lines.append(f"Mark Price: ${data['mark_price']:,.4f}")
    if data.get("price_change_pct") is not None:
        chg = data["price_change_pct"]
        em = "🟢" if chg >= 0 else "🔴"
        lines.append(f"تغییر فیوچرز ۲۴س: {em} {chg:+.2f}%")

    ls_lines = _format_long_short(data)
    if ls_lines:
        lines.append("")
        lines.append("📊 نسبت لانگ / شورت")
        lines.extend(ls_lines)

    lines.append("")
    lines.append("منبع: Binance Futures")
    lines.append("⚠️ صرفاً اطلاعاتی است.")
    return chr(10).join(lines)

async def risk_scenarios(symbol: str) -> str:
    """سناریوهای صعودی/نزولی و ریسک"""
    pair = _pair_from_symbol(symbol)
    klines = await _fetch_klines_for_ta(pair, limit=120)
    closes, highs, lows, vols = [], [], [], []
    for k in klines or []:
        try:
            highs.append(float(k[2])); lows.append(float(k[3]))
            closes.append(float(k[4])); vols.append(float(k[5]))
        except Exception:
            continue
    if len(closes) < 20:
        return f"❌ داده کافی برای سناریوی {pair} نیست."

    cur = closes[-1]
    ta = _compute_ta(closes, highs, lows, vols)
    support, resistance = _support_resistance(closes, highs, lows, cur)
    atr = 0
    if len(highs) >= 15:
        trs = []
        for i in range(1, min(15, len(closes))):
            trs.append(max(highs[-i] - lows[-i], abs(highs[-i] - closes[-i - 1]), abs(lows[-i] - closes[-i - 1])))
        atr = sum(trs) / len(trs) if trs else cur * 0.02

    bull = resistance or (cur + atr * 2)
    bear = support or (cur - atr * 2)
    invalid = (support * 0.99) if support else (cur - atr * 3)

    def f(v):
        return f"{v:,.2f}" if v >= 1 else f"{v:,.6f}"

    lines = [
        f"🎲 ریسک و سناریوها — {pair}",
        "────────────────────",
        f"قیمت فعلی: ${f(cur)}",
        f"ATR تقریبی: ${f(atr)}",
        "",
        "🟢 سناریو صعودی:",
        f"  شکست مقاومت ~{f(bull)} می‌تواند مسیر رشد را باز کند.",
        f"  هدف بعدی تقریبی: ${f(bull + atr)}",
        "",
        "🔴 سناریو نزولی:",
        f"  از دست رفتن حمایت ~{f(bear)} فشار فروش را تشدید می‌کند.",
        f"  سطح خطرناک‌تر: ${f(invalid)}",
        "",
        f"روند فعلی سیستم: {ta.get('trend', '—')}",
        f"RSI: {ta.get('rsi', 0):.1f}" if ta.get("rsi") is not None else "RSI: —",
        "",
        "مدیریت ریسک: حداکثر ۱–۲٪ سرمایه در هر معامله پیشنهاد می‌شود.",
        "⚠️ سناریوها احتمالی‌اند؛ قطعی نیستند.",
    ]
    return "\n".join(lines)

def position_size_guide(symbol: str = "") -> str:
    pair = _pair_from_symbol(symbol) if symbol else "BTCUSDT"
    return (
        f"📐 محاسبه سایز پوزیشن — {pair}\n"
        "────────────────────\n"
        "فرمت پیام بعدی:\n"
        "`سرمایه حدضرر درصد`\n\n"
        "مثال:\n"
        "• `1000 2`  → سرمایه ۱۰۰۰ دلار، حد ضرر ۲٪\n"
        "• `5000 1.5` → سرمایه ۵۰۰۰، حد ضرر ۱.۵٪\n\n"
        "فرمول:\n"
        "ریسک دلاری = سرمایه × (درصد حدضرر / ۱۰۰)\n"
        "اگر فاصله ورود تا حدضرر را هم بفرستید:\n"
        "`سرمایه حدضرر٪ فاصله٪`\n"
        "مثال: `1000 1 2`\n"
        "حجم تقریبی = ریسک / فاصله٪"
    )

def calc_position_size(text: str) -> str:
    t = (text or "").translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
    nums = re.findall(r"[\d]+(?:\.\d+)?", t)
    if len(nums) < 2:
        return "❌ فرمت: `1000 2` یا `1000 1 2`"
    capital = float(nums[0])
    risk_pct = float(nums[1])
    risk_usd = capital * (risk_pct / 100.0)
    lines = [
        "📐 نتیجه سایز پوزیشن",
        "────────────────────",
        f"سرمایه: ${capital:,.2f}",
        f"ریسک: {risk_pct}%",
        f"حداکثر ضرر دلاری: **${risk_usd:,.2f}**",
    ]
    if len(nums) >= 3:
        dist = float(nums[2])
        if dist > 0:
            size = risk_usd / (dist / 100.0)
            lines.append(f"فاصله حدضرر: {dist}%")
            lines.append(f"حجم تقریبی پوزیشن: **${size:,.2f}**")
            lines.append("(فرض: حرکت خلاف جهت به اندازه فاصله٪)")
    lines.append("")
    lines.append("⚠️ این فقط محاسبه ریسک است، نه سیگنال ورود.")
    return "\n".join(lines)

async def entry_alert_text(symbol: str) -> str:
    pair = _pair_from_symbol(symbol)
    klines = await _fetch_klines_for_ta(pair, limit=80)
    closes, highs, lows = [], [], []
    for k in klines or []:
        try:
            highs.append(float(k[2])); lows.append(float(k[3])); closes.append(float(k[4]))
        except Exception:
            continue
    cur = closes[-1] if closes else None
    support, resistance = _support_resistance(closes, highs, lows, cur)
    ta = _compute_ta(closes, highs, lows, [1] * len(closes)) if len(closes) >= 30 else {}
    signal, _, _, _, _, _ = _derive_signal(ta, None, {})
    level = support if "لانگ" in signal else resistance
    if level is None:
        level = cur

    def f(v):
        if v is None:
            return "—"
        return f"{v:,.2f}" if v >= 1 else f"{v:,.6f}"

    return (
        f"🔔 هشدار نقطه ورود — {pair}\n"
        "────────────────────\n"
        f"قیمت فعلی: ${f(cur)}\n"
        f"سطح پیشنهادی ورود: **${f(level)}**\n"
        f"حمایت: ${f(support)} | مقاومت: ${f(resistance)}\n\n"
        "برای ثبت هشدار، قیمت هدف را بفرستید:\n"
        f"مثال: `{f(level)}`\n\n"
        "ربات وقتی نزدیک شد می‌تواند یادآوری ثبت کند.\n"
        "⚠️ مانیتورینگ لحظه‌ای ۲۴ساعته تضمینی نیست."
    )

async def register_price_alert(user_id: int, symbol: str, price: float) -> str:
    """ثبت یادآوری متنی برای قیمت هدف"""
    pair = _pair_from_symbol(symbol)
    try:
        from bot.database import add_reminder
        from datetime import datetime, timedelta
        import pytz
        # یادآوری ۱ ساعت بعد به‌عنوان یادآور بررسی قیمت (چون قیمت‌استریم نداریم)
        tz = pytz.timezone("Asia/Tehran")
        remind_at = (datetime.now(tz) + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
        text = f"🔔 بررسی قیمت {pair} — هدف شما: ${price:,.4f}"
        add_reminder(user_id, text, remind_at, repeat_type="once", repeat_every=0)
        return (
            f"✅ هشدار ثبت شد\n"
            f"{pair} → هدف ${price:,.4f}\n"
            f"یادآوری بررسی حدود: {remind_at}\n"
            "می‌توانید چند هدف دیگر هم بفرستید."
        )
    except Exception as e:
        return f"⚠️ ثبت هشدار ناموفق: {e}\nهدف شما: ${price:,.4f} برای {pair}"
