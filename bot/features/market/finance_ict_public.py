"""finance_ict: public responsibilities."""
from .finance_ict_common import *  # noqa: F401,F403
from . import finance_ict_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def analyze_ict_from_ohlc(
    opens: list[float],
    highs: list[float],
    lows: list[float],
    closes: list[float],
    *,
    symbol: str = "",
    interval: str = "1h",
) -> dict[str, Any]:
    n = len(closes)
    if n < 40:
        return {"ok": False, "error": "داده کافی نیست (حداقل ۴۰ کندل لازم است)"}

    opens = [_f(x) for x in opens]
    highs = [_f(x) for x in highs]
    lows = [_f(x) for x in lows]
    closes = [_f(x) for x in closes]

    atr = _atr(highs, lows, closes)
    # External swings (stronger) vs internal (tighter)
    sh_ext, sl_ext = _swings(highs, lows, left=4, right=4)
    sh_int, sl_int = _swings(highs, lows, left=2, right=2)

    ext = _structure_from_swings(sh_ext, sl_ext, closes[-1], "external")
    internal = _structure_from_swings(sh_int, sl_int, closes[-1], "internal")
    fvgs = _fair_value_gaps(opens, highs, lows, closes, atr=atr)
    obs = _order_blocks(opens, highs, lows, closes, atr=atr)
    liq = _liquidity(sh_ext, sl_ext, highs, lows, closes)
    dr = _dealing_range(sh_ext, sl_ext, closes, ext.get("phase") or "neutral")
    disp = _displacement(opens, highs, lows, closes, atr)
    kz = _killzone()
    bias = _compute_bias(ext, internal, fvgs, obs, liq, dr, disp)
    scenarios = _scenarios(bias, dr, liq, ext)

    return {
        "ok": True,
        "symbol": symbol,
        "interval": interval,
        "price": closes[-1],
        "atr": atr,
        "candles": n,
        "external": ext,
        "internal": internal,
        "fvgs": fvgs,
        "order_blocks": obs,
        "liquidity": liq,
        "dealing_range": dr,
        "displacement": disp,
        "killzone": kz,
        "bias": bias,
        "scenarios": scenarios,
        "swings": {
            "ext_highs": sh_ext[-5:],
            "ext_lows": sl_ext[-5:],
        },
    }

def format_ict_report(data: dict) -> str:
    if not data.get("ok"):
        return f"❌ تحلیل ICT ممکن نیست: {data.get('error', 'خطا')}"

    sym = (data.get("symbol") or "").upper()
    b = data["bias"]
    ext = data["external"]
    internal = data["internal"]
    dr = data["dealing_range"]
    liq = data["liquidity"]
    kz = data["killzone"]

    lines = [
        f"📐 تحلیل ICT حرفه‌ای — {sym or 'SYMBOL'}",
        f"⏱ تایم‌فریم: {data.get('interval')} | کندل‌ها: {data.get('candles')}",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        f"💵 قیمت: {data['price']:.6g}",
        f"🎯 بایاس: {b['bias']}",
        f"📊 امتیاز: {b['score']:+.2f}  |  اطمینان: {b['confidence']:.0f}%",
        "",
        "🔹 ساختار خارجی (External)",
        f"• {ext['trend']}",
    ]
    if ext.get("bos"):
        lines.append(f"• {ext['bos']['text']}")
    if ext.get("mss"):
        lines.append(f"• {ext['mss']['text']}")
    if ext.get("last_high") is not None:
        lines.append(f"• سقف سوئینگ: {ext['last_high']:.6g}")
    if ext.get("last_low") is not None:
        lines.append(f"• کف سوئینگ: {ext['last_low']:.6g}")

    lines += [
        "",
        "🔸 ساختار داخلی (Internal)",
        f"• {internal['trend']}",
    ]
    if internal.get("bos"):
        lines.append(f"• {internal['bos']['text']}")
    if internal.get("mss"):
        lines.append(f"• {internal['mss']['text']}")

    lines += ["", "⚖️ Dealing Range / Premium–Discount"]
    lines.append(f"• {dr.get('zone_fa') or dr.get('zone')}")
    if dr.get("eq") is not None:
        lines.append(f"• High: {dr['high']:.6g}  |  EQ: {dr['eq']:.6g}  |  Low: {dr['low']:.6g}")
        lines.append(f"• موقعیت در رنج: {dr.get('position_pct')}%")
    if dr.get("bull_ote"):
        lo, hi = dr["bull_ote"]
        mark = " ✅" if dr.get("in_bull_ote") else ""
        lines.append(f"• OTE صعودی (۶۲–۷۹٪): {lo:.6g} — {hi:.6g}{mark}")
    if dr.get("bear_ote"):
        lo, hi = dr["bear_ote"]
        mark = " ✅" if dr.get("in_bear_ote") else ""
        lines.append(f"• OTE نزولی (۶۲–۷۹٪): {lo:.6g} — {hi:.6g}{mark}")

    lines += ["", "🟩 Fair Value Gaps"]
    fvgs = data.get("fvgs") or []
    if not fvgs:
        lines.append("• FVG مرتبطی در پنجره اخیر نیست")
    else:
        for g in fvgs[:5]:
            side = "صعودی" if g["type"] == "bullish" else "نزولی"
            st = {"open": "باز", "partial": "نیمه‌پر", "filled": "پرشده"}.get(g["state"], g["state"])
            lines.append(
                f"• FVG {side} [{st}]: {g['bottom']:.6g}—{g['top']:.6g} "
                f"| CE {g['ce']:.6g} | عمر {g['age']} کندل"
            )

    lines += ["", "📦 Order Block / Breaker"]
    obs = data.get("order_blocks") or []
    if not obs:
        lines.append("• OB معتبری در پنجره اخیر نیست")
    else:
        for o in obs[:5]:
            if o["type"] == "bullish_ob":
                tag = "Demand OB"
            elif o["type"] == "bearish_ob":
                tag = "Supply OB"
            elif o["type"] == "breaker_bearish":
                tag = "Breaker↓ (OB صعودی شکسته‌شده)"
            else:
                tag = "Breaker↑ (OB نزولی شکسته‌شده)"
            flags = []
            if o.get("mitigated"):
                flags.append("mitigated")
            if o.get("broken"):
                flags.append("broken")
            flag_s = f" [{', '.join(flags)}]" if flags else ""
            lines.append(f"• {tag}: {o['low']:.6g}—{o['high']:.6g}{flag_s}")

    lines += ["", "💧 نقدینگی"]
    if liq.get("bsl") is not None:
        lines.append(f"• BSL (بالای سقف): {liq['bsl']:.6g}")
    if liq.get("ssl") is not None:
        lines.append(f"• SSL (زیر کف): {liq['ssl']:.6g}")
    if liq.get("equal_highs"):
        lines.append(f"• Equal Highs: {len(liq['equal_highs'])} خوشه")
    if liq.get("equal_lows"):
        lines.append(f"• Equal Lows: {len(liq['equal_lows'])} خوشه")
    if liq.get("sweep"):
        lines.append(f"• {liq['sweep']['text']}")

    if data.get("displacement"):
        lines += ["", f"⚡ {data['displacement']['text']}"]
    if data.get("atr"):
        lines.append(f"📏 ATR(14): {data['atr']:.6g}")

    lines += ["", kz.get("text", "")]

    if b.get("reasons"):
        lines += ["", "🧠 دلایل بایاس"]
        for r in b["reasons"]:
            lines.append(f"• {r}")

    if data.get("scenarios"):
        lines += ["", "📋 سناریوها"]
        for s in data["scenarios"]:
            lines.append(f"• {s}")

    lines += [
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "⚠️ صرفاً آموزشی است — توصیه مالی یا سیگنال قطعی نیست.",
        "ورود فقط با تأیید شخصی روی چارت و مدیریت ریسک.",
    ]
    return "\n".join(lines)

async def analyze_ict(symbol: str, interval: str = "1h", limit: int = 250) -> str:
    """Fetch OHLCV and return professional Persian ICT report."""
    from bot.features.market.finance_ta import _fetch_klines_for_ta
    from bot.features.market import finance as fin

    raw = (symbol or "btc").lower().strip()
    for junk in (
        "تحلیل", "ict", "آی‌سی‌تی", "اسیتی", "usdt", "تحلیل ict",
        "به روش", "روش",
    ):
        raw = raw.replace(junk, "")
    raw = raw.strip() or "btc"
    parts = raw.split()
    sym = parts[0]
    if len(parts) > 1 and parts[1] in ("15m", "15", "1h", "4h", "1d", "h1", "h4", "daily"):
        interval = parts[1]

    iv = {
        "15": "15m", "15m": "15m",
        "1h": "1h", "h1": "1h", "60m": "1h",
        "4h": "4h", "h4": "4h",
        "1d": "1d", "1day": "1d", "daily": "1d",
    }.get((interval or "1h").lower(), "1h")

    pair = f"{sym.upper()}USDT"
    if sym in ("gold", "xau", "xauusd"):
        pair = "PAXGUSDT"
        sym = "xau"

    klines: list = []
    try:
        if hasattr(fin, "_fetch_klines_interval"):
            klines = await fin._fetch_klines_interval(pair, iv, int(limit))
        if not klines:
            klines = await _fetch_klines_for_ta(pair, limit=limit)
            iv = "1h"
    except Exception as e:
        logger.warning("ICT klines failed: %s", e)

    if not klines or len(klines) < 40:
        return (
            f"❌ داده کندل کافی برای {sym.upper()} یافت نشد.\n"
            "مثال: btc | eth 4h | sol 1h | btc 15m"
        )

    opens = [_f(k[1]) for k in klines]
    highs = [_f(k[2]) for k in klines]
    lows = [_f(k[3]) for k in klines]
    closes = [_f(k[4]) for k in klines]

    data = analyze_ict_from_ohlc(
        opens, highs, lows, closes, symbol=sym, interval=iv
    )
    return format_ict_report(data)
