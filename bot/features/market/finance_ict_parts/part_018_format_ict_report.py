# Auto-split part 18: format_ict_report
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
