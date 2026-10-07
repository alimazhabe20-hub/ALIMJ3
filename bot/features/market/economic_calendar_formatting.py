"""economic_calendar: formatting responsibilities."""
from .economic_calendar_common import *  # noqa: F401,F403
from . import economic_calendar_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def format_value(value: Any, *, empty: str = "در انتظار انتشار", unit: str = "") -> str:
    if value is None:
        return empty
    s = str(value).strip()
    if not s or s in {"None", "null", "—", "-"}:
        return empty
    # already has unit
    if any(ch in s for ch in ("%","K","M","B")) and re.search(r"\d", s):
        return s
    num = _parse_num(s)
    if num is None:
        return s
    # pretty number
    if abs(num) >= 100 and float(num) == int(num):
        body = str(int(num))
    else:
        body = f"{num:.4f}".rstrip("0").rstrip(".")
    u = (unit or "").strip()
    if u == "%":
        return f"{body}%"
    if u in {"K", "M", "B"}:
        return f"{body}{u}"
    return body

def surprise_text(e: dict[str, Any]) -> str:
    """مقایسه Actual با Forecast برای نمایش سورپرایز."""
    a = _parse_num(e.get("actual"))
    f = _parse_num(e.get("forecast"))
    if a is None or f is None:
        return ""
    title = f"{e.get('title', '')}".lower()
    # برای claims بالاتر = بدتر برای بازار ریسک‌پذیر
    inverse = any(x in title for x in ("claims", "jobless", "unemployment"))
    if abs(a - f) < 1e-12:
        return "➖ مطابق انتظار"
    higher = a > f
    if inverse:
        if higher:
            return "⚠️ بالاتر از پیش‌بینی (منفی برای ریسک)"
        return "✅ پایین‌تر از پیش‌بینی (مثبت برای ریسک)"
    if higher:
        return "⬆️ بالاتر از پیش‌بینی"
    return "⬇️ پایین‌تر از پیش‌بینی"

def _impact_label(e: dict[str, Any]) -> str:
    return IMPACT_FA.get(e.get("impact", ""), e.get("impact") or "نامشخص")

def format_event(e: dict[str, Any], tz_name: str = "", *, show_date: bool = False) -> str:
    local = _event_local(e, tz_name)
    icon = IMPACT_ICON.get(e["impact"], "⚪")
    title_fa = _esc(e["title_fa"])
    title_en = _esc(_en_short(e.get("title") or "", max_len=40))
    now = datetime.now(_tz(tz_name))
    past = local < now
    past_mark = " ✅" if past else ""
    actual_empty = "منتشر نشده" if past else "در انتظار انتشار"
    other_empty = "—"
    when = local.strftime("%m/%d %H:%M") if show_date else local.strftime("%H:%M")
    unit = _unit_for_event(e)
    actual_s = format_value(e.get("actual"), empty=actual_empty, unit=unit)
    forecast_s = format_value(e.get("forecast"), empty=other_empty, unit=unit)
    previous_s = format_value(e.get("previous"), empty=other_empty, unit=unit)
    surprise = surprise_text(e)
    sur_line = f"\n   📊 <b>نتیجه:</b> {_esc(surprise)}" if surprise else ""
    return (
        f"{icon} <b>{when} | {_esc(e['country'])} | {title_fa}</b>{past_mark}\n"
        f"   <i>{title_en}</i>\n"
        f"   🚦 <b>اهمیت:</b> {_esc(_impact_label(e))}"
        f"  •  📢 <b>واقعی:</b> {_esc(actual_s)}"
        f"  •  🔮 <b>پیش‌بینی:</b> {_esc(forecast_s)}"
        f"  •  ◀️ <b>قبلی:</b> {_esc(previous_s)}"
        f"{sur_line}"
    )

def calendar_text(events, *, title: str, tz_name: str = "", limit: int = 25, show_date: bool = False) -> str:
    tz = _tz(tz_name)
    lines = [
        f"🗓 <b>{_esc(title)}</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"🕐 <b>منطقه زمانی:</b> <code>{_esc(tz.zone)}</code>",
        "",
    ]
    if not events:
        lines.append("📭 <i>رویداد اقتصادی‌ای با این فیلتر پیدا نشد.</i>")
        lines.append("")
        lines.append("💡 <i>اگر روز آینده را می‌بینید، ممکن است منبع هنوز برنامه آن روز را منتشر نکرده باشد. «بروزرسانی» را بزنید یا روز دیگری را انتخاب کنید.</i>")
        return "\n".join(lines)

    # نمایش روزانه: ترتیب زمانی (نه فقط مهم‌ها اول)
    ordered = sorted(
        events,
        key=lambda e: e.get("utc") or datetime.min.replace(tzinfo=timezone.utc),
    )

    base = "\n".join(lines)
    added = 0
    for e in ordered[: max(limit, 1)]:
        block = format_event(e, tz_name, show_date=show_date)
        candidate = base + "\n" + block + "\n"
        if len(candidate) > 3850:
            break
        lines.extend([block, ""])
        base = candidate
        added += 1
    remaining = len(events) - added
    if remaining > 0:
        high_left = sum(1 for e in ordered[added:] if str(e.get("impact")) == "High")
        extra = f" (از جمله {high_left} خبر مهم)" if high_left else ""
        lines += [f"… <i>{remaining} رویداد دیگر هم وجود دارد{extra}. دکمه «فقط مهم» را بزنید.</i>", ""]
    lines += [
        "<b>راهنمای اهمیت:</b> 🔴 زیاد  🟠 متوسط  🟡 کم",
        "ℹ️ <i>مقادیر واقعی از منبع داده‌محور خوانده می‌شوند. اگر «در انتظار انتشار» دیدید یعنی هنوز عدد رسمی ثبت نشده.</i>",
    ]
    return "\n".join(lines)

def event_detail(e: dict[str, Any], tz_name: str = "") -> str:
    local = _event_local(e, tz_name)
    now = datetime.now(_tz(tz_name))
    delta = local - now
    if delta.total_seconds() > 0:
        mins = int(delta.total_seconds() // 60)
        countdown = f"حدود {mins // 60} ساعت و {mins % 60} دقیقه دیگر"
        actual_empty = "در انتظار انتشار"
    else:
        countdown = "زمان رویداد گذشته است"
        actual_empty = "منتشر نشده"
    unit = _unit_for_event(e)
    surprise = surprise_text(e)
    sur = f"\n📊 <b>نتیجه:</b> {_esc(surprise)}" if surprise else ""
    return (
        f"{IMPACT_ICON.get(e['impact'], '⚪')} <b>{_esc(e['title_fa'])}</b>\n"
        f"<i>{_esc(_en_short(e.get('title') or '', max_len=48))}</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💱 <b>ارز:</b> {_esc(e['country'])} — {_esc(e['currency_name'])}\n"
        f"📅 <b>تاریخ:</b> <code>{local.strftime('%Y/%m/%d')}</code>\n"
        f"⏰ <b>ساعت:</b> <code>{local.strftime('%H:%M')}</code>\n"
        f"🚦 <b>اهمیت:</b> {_esc(_impact_label(e))}\n"
        f"⏳ <b>وضعیت:</b> {_esc(countdown)}\n\n"
        f"📢 <b>واقعی:</b> {_esc(format_value(e.get('actual'), empty=actual_empty, unit=unit))}\n"
        f"🔮 <b>پیش‌بینی:</b> {_esc(format_value(e.get('forecast'), empty='—', unit=unit))}\n"
        f"◀️ <b>قبلی:</b> {_esc(format_value(e.get('previous'), empty='—', unit=unit))}"
        f"{sur}\n\n"
        "⚠️ <i>این داده برای تصمیم‌گیری مالی قطعی نیست.</i>"
    )

def get_status() -> str:
    if not _cache_fetched_at:
        return "داده هنوز دریافت نشده است."
    age = max(0, int(time.time() - _cache_fetched_at))
    return f"آخرین بروزرسانی منبع: {age // 60} دقیقه قبل"

def ai_context(events, tz_name: str = "", limit: int = 40) -> str:
    rows = []
    for e in events[:limit]:
        local = _event_local(e, tz_name)
        rows.append(
            f"{local.isoformat()} | {e['country']} | {e['impact']} | {e['title']} | "
            f"actual={format_value(e['actual'])} | forecast={format_value(e['forecast'])} | previous={format_value(e['previous'])}"
        )
    return "\n".join(rows)
