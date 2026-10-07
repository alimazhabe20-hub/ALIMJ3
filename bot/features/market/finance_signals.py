"""finance: signals responsibilities."""
from .finance_common import *  # noqa: F401,F403
from . import finance_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def _signal_track_stub() -> str:
    """کارنامه ساده — تا وقتی دیتابیس سیگنال نداریم"""
    return "کارنامه سیگنال: به‌زودی با ثبت خودکار ستاپ‌ها فعال می‌شود"

def _support_resistance(closes, highs, lows, current):
    if not closes:
        return None, None
    window = closes[-48:] if len(closes) >= 48 else closes
    hi_w = highs[-48:] if len(highs) >= 48 else highs
    lo_w = lows[-48:] if len(lows) >= 48 else lows
    resistance = max(hi_w) if hi_w else max(window)
    support = min(lo_w) if lo_w else min(window)
    # نزدیک‌تر کردن به قیمت فعلی با pivot ساده
    if current:
        # حمایت: بالاترین low زیر قیمت
        below = [x for x in lo_w if x < current * 0.999]
        above = [x for x in hi_w if x > current * 1.001]
        if below:
            support = max(below)
        if above:
            resistance = min(above)
    return support, resistance

def _derive_signal(ta: dict, chg_24, binance: dict, current=None, support=None, resistance=None):
    """سیگنال، امتیاز، R:R، ریسک، وضعیت اجرا — با تشخیص فرصت گذشته"""
    rsi = ta.get("rsi")
    adx = ta.get("adx") or 0
    trend = ta.get("trend") or "خنثی"
    score = 5
    signal = "خنثی / احتیاط"
    signal_emoji = "🟡"

    if trend == "صعودی":
        score += 2
        signal, signal_emoji = "لانگ", "🟢"
    elif trend == "نزولی":
        score += 2
        signal, signal_emoji = "شورت", "🔴"

    if rsi is not None:
        if signal == "لانگ" and 35 <= rsi <= 65:
            score += 1
        elif signal == "شورت" and 35 <= rsi <= 65:
            score += 1
        elif signal == "لانگ" and rsi >= 72:
            score -= 2
        elif signal == "شورت" and rsi <= 28:
            score -= 2
        elif signal == "لانگ" and rsi <= 35:
            score += 1
        elif signal == "شورت" and rsi >= 65:
            score += 1

    if adx >= 25:
        score += 1
    elif adx < 18:
        score -= 1
        if signal in ("لانگ", "شورت"):
            signal, signal_emoji = "خنثی / احتیاط", "🟡"

    if chg_24 is not None:
        if signal == "لانگ" and chg_24 < -5:
            score -= 1
        if signal == "شورت" and chg_24 > 5:
            score -= 1

    fr = (binance or {}).get("funding_rate")
    if fr is not None:
        if signal == "لانگ" and fr < 0:
            score += 1
        elif signal == "شورت" and fr > 0:
            score += 1
        elif signal == "لانگ" and fr > 0.05:
            score -= 1
        elif signal == "شورت" and fr < -0.05:
            score -= 1

    score = max(1, min(10, score))

    if score >= 8:
        rr = "خوب 🟢"
        risk = "کم 🟢"
    elif score >= 6:
        rr = "متوسط 🟡"
        risk = "متوسط 🟡"
    elif score >= 4:
        rr = "متوسط 🟡"
        risk = "متوسط 🟡"
    else:
        rr = "ضعیف 🔴"
        risk = "بالا 🔴"

    exec_status = "صبر کنید ❌"
    try:
        cur = float(current) if current is not None else None
        sup = float(support) if support is not None else None
        res = float(resistance) if resistance is not None else None
    except Exception:
        cur = sup = res = None

    if signal == "لانگ" and cur is not None and sup is not None and res is not None:
        span = max(res - sup, cur * 0.001)
        pos = (cur - sup) / span
        if pos >= 0.72:
            exec_status = "فرصت گذشته — منتظرِ موقعیتِ بعدی ⛔️"
            risk = "متوسط 🟡"
        elif pos <= 0.35 and score >= 6:
            exec_status = "قابل معامله ✅"
        elif score >= 7:
            exec_status = "با احتیاط ⚠️"
        else:
            exec_status = "صبر کنید ❌"
    elif signal == "شورت" and cur is not None and sup is not None and res is not None:
        span = max(res - sup, cur * 0.001)
        near_res = abs(res - cur) / span <= 0.35
        near_sup = abs(cur - sup) / span <= 0.28
        if near_sup:
            exec_status = "فرصت گذشته — منتظرِ موقعیتِ بعدی ⛔️"
            risk = "متوسط 🟡"
        elif near_res and score >= 6:
            exec_status = "قابل معامله ✅"
        elif score >= 7:
            exec_status = "با احتیاط ⚠️"
        else:
            exec_status = "صبر کنید ❌"
    else:
        if score >= 8:
            exec_status = "قابل معامله ✅"
        elif score >= 5:
            exec_status = "با احتیاط ⚠️"
        else:
            exec_status = "صبر کنید ❌"

    return signal, signal_emoji, score, rr, risk, exec_status
