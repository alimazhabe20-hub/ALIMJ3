"""تقویم اقتصادی زنده برای بخش بازار.

منبع پیش‌فرض: خروجی هفتگی عمومی Forex Factory/faireconomy.media.
دریافت عمداً کم‌دفعات انجام می‌شود تا به محدودیت منبع احترام گذاشته شود.
"""
from __future__ import annotations

import asyncio
import hashlib
import html
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import pytz
import requests

from bot.config import config
from bot.logger import logger

FF_URLS = (
    "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
    "https://nfs.faireconomy.media/ff_calendar_nextweek.json",
)
FF_FALLBACK_URLS = (
    "https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.json",
    "https://cdn-nfs.faireconomy.media/ff_calendar_nextweek.json",
)
CACHE_TTL = 30 * 60
_MAX_EVENTS = 600

_cache: list[dict[str, Any]] = []
_cache_expires = 0.0
_cache_fetched_at = 0.0
_cache_lock: asyncio.Lock | None = None

CURRENCY_NAMES = {
    "USD": "دلار آمریکا", "EUR": "یورو", "GBP": "پوند انگلیس", "JPY": "ین ژاپن",
    "CHF": "فرانک سوئیس", "CAD": "دلار کانادا", "AUD": "دلار استرالیا",
    "NZD": "دلار نیوزیلند", "CNY": "یوان چین", "NOK": "کرون نروژ",
    "SEK": "کرون سوئد", "HKD": "دلار هنگ‌کنگ", "SGD": "دلار سنگاپور",
    "MXN": "پزوی مکزیک", "INR": "روپیه هند", "TRY": "لیر ترکیه", "ZAR": "رند آفریقای جنوبی",
}
IMPACT_FA = {"High": "زیاد", "Medium": "متوسط", "Low": "کم", "Holiday": "تعطیلی", "": "نامشخص"}
IMPACT_ICON = {"High": "🔴", "Medium": "🟠", "Low": "🟡", "Holiday": "⚪"}

# ترجمه عنوان‌های رایج؛ عنوان‌های ناشناخته با واژه‌نامه‌ی عمومی تمیز می‌شوند.
TITLE_MAP = {
    "Non-Farm Employment Change": "تغییر اشتغال غیرکشاورزی",
    "Non-Farm Payrolls": "اشتغال غیرکشاورزی",
    "Unemployment Rate": "نرخ بیکاری",
    "Unemployment Claims": "درخواست‌های بیمه بیکاری",
    "Initial Jobless Claims": "درخواست‌های اولیه بیمه بیکاری",
    "Continuing Jobless Claims": "درخواست‌های مستمر بیمه بیکاری",
    "CPI m/m": "شاخص قیمت مصرف‌کننده ماهانه",
    "Core CPI m/m": "شاخص قیمت مصرف‌کننده هسته ماهانه",
    "CPI y/y": "شاخص قیمت مصرف‌کننده سالانه",
    "Core CPI y/y": "شاخص قیمت مصرف‌کننده هسته سالانه",
    "PPI m/m": "شاخص قیمت تولیدکننده ماهانه",
    "Core PPI m/m": "شاخص قیمت تولیدکننده هسته ماهانه",
    "PPI y/y": "شاخص قیمت تولیدکننده سالانه",
    "GDP q/q": "رشد تولید ناخالص داخلی فصلی",
    "GDP y/y": "رشد تولید ناخالص داخلی سالانه",
    "Retail Sales m/m": "فروش خرده‌فروشی ماهانه",
    "Core Retail Sales m/m": "فروش خرده‌فروشی هسته ماهانه",
    "Industrial Production m/m": "تولید صنعتی ماهانه",
    "Manufacturing PMI": "شاخص مدیران خرید تولیدی",
    "Services PMI": "شاخص مدیران خرید خدمات",
    "PMI": "شاخص مدیران خرید",
    "Consumer Confidence": "اعتماد مصرف‌کننده",
    "Consumer Sentiment": "احساسات مصرف‌کننده",
    "Consumer Price Index": "شاخص قیمت مصرف‌کننده",
    "Producer Price Index": "شاخص قیمت تولیدکننده",
    "Interest Rate Decision": "تصمیم نرخ بهره",
    "Main Refinancing Rate": "نرخ اصلی بازتأمین مالی",
    "Monetary Policy Statement": "بیانیه سیاست پولی",
    "ECB Press Conference": "کنفرانس خبری بانک مرکزی اروپا",
    "FOMC Statement": "بیانیه کمیته بازار آزاد فدرال رزرو",
    "FOMC Meeting Minutes": "صورت‌جلسه کمیته بازار آزاد فدرال رزرو",
    "Fed Interest Rate Decision": "تصمیم نرخ بهره فدرال رزرو",
    "BOE Interest Rate Decision": "تصمیم نرخ بهره بانک مرکزی انگلیس",
    "BOJ Interest Rate Decision": "تصمیم نرخ بهره بانک مرکزی ژاپن",
    "RBA Interest Rate Decision": "تصمیم نرخ بهره بانک مرکزی استرالیا",
    "RBNZ Interest Rate Decision": "تصمیم نرخ بهره بانک مرکزی نیوزیلند",
    "Speaks": "سخنرانی مقام اقتصادی",
    "President Trump Speaks": "سخنرانی رئیس‌جمهور ترامپ",
    "Central Bank": "بانک مرکزی",
    "Trade Balance": "تراز تجاری",
    "Current Account": "حساب جاری",
    "Building Permits": "مجوزهای ساخت‌وساز",
    "Housing Starts": "شروع ساخت مسکن",
    "Durable Goods Orders": "سفارش کالاهای بادوام",
    "Factory Orders": "سفارش‌های کارخانه‌ای",
    "Existing Home Sales": "فروش خانه‌های موجود",
    "New Home Sales": "فروش خانه‌های جدید",
    "ISM Manufacturing PMI": "شاخص تولیدی ISM",
    "ISM Services PMI": "شاخص خدمات ISM",
    "ADP Non-Farm Employment Change": "تغییر اشتغال غیرکشاورزی ADP",
    "JOLTS Job Openings": "فرصت‌های شغلی JOLTS",
    "Average Hourly Earnings m/m": "میانگین دستمزد ساعتی ماهانه",
    "Personal Spending m/m": "مخارج شخصی ماهانه",
    "Personal Income m/m": "درآمد شخصی ماهانه",
}

TERM_MAP = {
    " m/m": " ماهانه", " y/y": " سالانه", " q/q": " فصلی",
    "Core": "هسته", "Final": "نهایی", "Prelim": "اولیه", "Preliminary": "اولیه",
    "Flash": "اولیه سریع", "Index": "شاخص", "Rate": "نرخ", "Statement": "بیانیه",
    "Press Conference": "کنفرانس خبری", "Sales": "فروش", "Orders": "سفارش‌ها",
    "Change": "تغییر", "Balance": "تراز", "Expectations": "انتظارات", "Forecast": "پیش‌بینی",
    "Previous": "قبلی", "Actual": "واقعی", "Estimate": "برآورد", "Minutes": "صورت‌جلسه",
}


def _event_id(raw: dict[str, Any]) -> str:
    base = "|".join(str(raw.get(k, "")) for k in ("date", "country", "title", "impact"))
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]


def _parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    s = str(value).strip()
    try:
        normalized = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", s)
        dt = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _fa_title(title: str) -> str:
    t = (title or "رویداد اقتصادی").strip()
    if t in TITLE_MAP:
        return TITLE_MAP[t]
    # چند عنوان رایج که با پسوندها/نام کشورها تغییر می‌کنند.
    for k, v in sorted(TITLE_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        if t.lower() == k.lower():
            return v
    out = t
    for k, v in sorted(TERM_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        out = out.replace(k, v)
    out = re.sub(r"\bHigh\b", "زیاد", out, flags=re.I)
    out = re.sub(r"\bMedium\b", "متوسط", out, flags=re.I)
    out = re.sub(r"\bLow\b", "کم", out, flags=re.I)
    # اگر هنوز کاملاً انگلیسی است، آن را برای AI قابل‌تشخیص نگه می‌داریم اما متن UI فارسی می‌ماند.
    return out


def _raw_value(raw: dict[str, Any], *keys: str) -> Any:
    """اولین مقدار واقعاً موجود را برمی‌گرداند؛ صفر مقدار معتبر است."""
    for key in keys:
        if key in raw and raw.get(key) not in (None, ""):
            return raw.get(key)
    return ""


def _normalize(raw: dict[str, Any]) -> dict[str, Any] | None:
    dt = _parse_dt(raw.get("date", ""))
    if not dt:
        return None
    country = str(raw.get("country") or raw.get("currency") or "").upper().strip()
    impact = str(raw.get("impact") or "").strip().title()
    title = str(raw.get("title") or raw.get("event") or "رویداد اقتصادی").strip()
    return {
        "id": _event_id(raw),
        "utc": dt,
        "country": country,
        "currency_name": CURRENCY_NAMES.get(country, country or "نامشخص"),
        "impact": impact,
        "title": title,
        "title_fa": _fa_title(title),
        "actual": _raw_value(raw, "actual", "Actual", "actualValue"),
        "forecast": _raw_value(raw, "forecast", "Forecast", "forecastValue", "estimate"),
        "previous": _raw_value(raw, "previous", "Previous", "previousValue"),
        "source": "Forex Factory",
    }


def _fetch_json(url: str) -> list[dict[str, Any]]:
    r = requests.get(url, timeout=18, headers={"User-Agent": "Mozilla/5.0 ALIMJ Economic Calendar"})
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        raise ValueError("فرمت داده تقویم نامعتبر است")
    return data


async def refresh_calendar(force: bool = False) -> list[dict[str, Any]]:
    global _cache, _cache_expires, _cache_fetched_at, _cache_lock
    now = time.monotonic()
    if _cache and now < _cache_expires and not force:
        return list(_cache)
    if _cache_lock is None:
        _cache_lock = asyncio.Lock()
    async with _cache_lock:
        now = time.monotonic()
        if _cache and now < _cache_expires and not force:
            return list(_cache)
        all_rows: list[dict[str, Any]] = []
        errors = []
        for i, url in enumerate(FF_URLS):
            try:
                rows = await asyncio.to_thread(_fetch_json, url)
                all_rows.extend(rows)
            except Exception as exc:
                errors.append(f"{url}: {exc}")
                # fallback فقط در صورت خطا، نه به‌صورت درخواست موازی.
                try:
                    rows = await asyncio.to_thread(_fetch_json, FF_FALLBACK_URLS[i])
                    all_rows.extend(rows)
                except Exception as exc2:
                    errors.append(f"fallback: {exc2}")
        normalized = [e for e in (_normalize(x) for x in all_rows) if e]
        dedup = {e["id"]: e for e in normalized}
        normalized = sorted(dedup.values(), key=lambda e: e["utc"])[:_MAX_EVENTS]
        if normalized:
            # قبل از جایگزینی cache، داده‌ها را دائمی نگه می‌داریم تا Actual و
            # رویدادهای روزهای گذشته حتی بعد از خروج از feed زنده باقی بمانند.
            try:
                from bot.database import upsert_economic_calendar_events
                upsert_economic_calendar_events(normalized)
            except Exception as exc:
                logger.warning("economic calendar history persist failed: %s", exc)
            _cache = normalized
            _cache_fetched_at = time.time()
            _cache_expires = time.monotonic() + CACHE_TTL
            if errors:
                logger.warning("economic calendar partial refresh: %s", " | ".join(errors[:3]))
        elif _cache:
            logger.warning("economic calendar refresh failed; using stale cache: %s", " | ".join(errors[:3]))
        else:
            raise RuntimeError("تقویم اقتصادی فعلاً از منبع زنده دریافت نشد.")
        return list(_cache)


def _tz(name: str = ""):
    name = (name or "").strip() or getattr(config, "TIMEZONE", "Asia/Tehran")
    try:
        return pytz.timezone(name)
    except Exception:
        return pytz.timezone("Asia/Tehran")


def _event_local(e: dict[str, Any], tz_name: str) -> datetime:
    return e["utc"].astimezone(_tz(tz_name))


def filter_events(events, *, days: int = 1, currency: str = "", impact: str = "", tz_name: str = "", include_past: bool = False):
    tz = _tz(tz_name)
    now = datetime.now(tz)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=max(1, min(14, int(days or 1))))
    currency = (currency or "").upper().strip()
    impact = (impact or "").lower().strip()
    out = []
    for e in events:
        local = e["utc"].astimezone(tz)
        if include_past:
            if not (start <= local < end):
                continue
        elif not (now <= local < end):
            continue
        if currency and e["country"] != currency:
            continue
        if impact and impact != "all" and e["impact"].lower() != impact:
            continue
        out.append(e)
    return out


def format_value(value: Any) -> str:
    return str(value).strip() if value not in (None, "") else "—"


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=False)


def _impact_label(e: dict[str, Any]) -> str:
    return IMPACT_FA.get(e.get("impact", ""), e.get("impact") or "نامشخص")


def format_event(e: dict[str, Any], tz_name: str = "") -> str:
    local = _event_local(e, tz_name)
    icon = IMPACT_ICON.get(e["impact"], "⚪")
    title_fa = _esc(e["title_fa"])
    title_en = _esc(e["title"])
    actual = format_value(e["actual"])
    status = "🟢 اعلام شد" if actual != "—" else "⏳ هنوز اعلام نشده"
    return (
        f"{icon} <b>{local.strftime('%H:%M')} | {_esc(e['country'])} | {title_fa}</b>\n"
        f"   <i>{title_en}</i>\n"
        f"   🚦 <b>اهمیت:</b> {_esc(_impact_label(e))}\n"
        f"   {status}  •  📢 <b>واقعی:</b> {_esc(actual)}"
        f"  •  🔮 <b>پیش‌بینی:</b> {_esc(format_value(e['forecast']))}"
        f"  •  ◀️ <b>قبلی:</b> {_esc(format_value(e['previous']))}"
    )


def calendar_text(events, *, title: str, tz_name: str = "", limit: int = 25) -> str:
    tz = _tz(tz_name)
    lines = [
        f"🗓 <b>{_esc(title)}</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"🕐 <b>منطقه زمانی:</b> <code>{_esc(tz.zone)}</code>",
        "",
    ]
    if not events:
        lines.append("📭 <i>رویداد اقتصادی‌ای با این فیلتر پیدا نشد.</i>")
        return "\n".join(lines)
    base = "\n".join(lines)
    added = 0
    for e in events[:limit]:
        block = format_event(e, tz_name)
        candidate = base + "\n" + block + "\n"
        # هرگز HTML را وسط یک تگ قطع نکنیم.
        if len(candidate) > 3850:
            break
        lines.extend([block, ""])
        base = candidate
        added += 1
    remaining = len(events) - added
    if remaining > 0:
        lines += [f"… <i>{remaining} رویداد دیگر هم وجود دارد.</i>", ""]
    lines += [
        "<b>راهنمای اهمیت:</b> 🔴 زیاد  🟠 متوسط  🟡 کم",
        "ℹ️ <i>مقادیر واقعی ممکن است تا زمان انتشار خالی باشند.</i>",
    ]
    return "\n".join(lines)


def get_event(events, event_id: str):
    return next((e for e in events if e.get("id") == event_id), None)


def event_detail(e: dict[str, Any], tz_name: str = "") -> str:
    local = _event_local(e, tz_name)
    now = datetime.now(_tz(tz_name))
    delta = local - now
    if delta.total_seconds() > 0:
        mins = int(delta.total_seconds() // 60)
        countdown = f"حدود {mins // 60} ساعت و {mins % 60} دقیقه دیگر"
    else:
        countdown = "زمان رویداد گذشته است"
    return (
        f"{IMPACT_ICON.get(e['impact'], '⚪')} <b>{_esc(e['title_fa'])}</b>\n"
        f"<i>{_esc(e['title'])}</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💱 <b>ارز:</b> {_esc(e['country'])} — {_esc(e['currency_name'])}\n"
        f"📅 <b>تاریخ:</b> <code>{local.strftime('%Y/%m/%d')}</code>\n"
        f"⏰ <b>ساعت:</b> <code>{local.strftime('%H:%M')}</code>\n"
        f"🚦 <b>اهمیت:</b> {_esc(_impact_label(e))}\n"
        f"⏳ <b>وضعیت:</b> {_esc(countdown)}\n\n"
        f"📢 <b>واقعی:</b> {_esc(format_value(e['actual']))}\n"
        f"🔮 <b>پیش‌بینی:</b> {_esc(format_value(e['forecast']))}\n"
        f"◀️ <b>قبلی:</b> {_esc(format_value(e['previous']))}\n\n"
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


def get_calendar_keyboard(user_id: int, *, mode: str = "today", impact: str = "all", events=None, selected_date: str = ""):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    if not selected_date:
        try:
            from bot.database import get_economic_calendar_preferences
            pref = get_economic_calendar_preferences(user_id)
            user_tz = pref.get("timezone") or getattr(config, "TIMEZONE", "Asia/Tehran")
        except Exception:
            user_tz = getattr(config, "TIMEZONE", "Asia/Tehran")
        selected_date = datetime.now(_tz(user_tz)).strftime("%Y-%m-%d")
    selected = selected_date
    try:
        d = datetime.strptime(selected, "%Y-%m-%d").date()
    except Exception:
        d = datetime.now(_tz()).date()
    prev_d = (d - timedelta(days=1)).isoformat()
    next_d = (d + timedelta(days=1)).isoformat()
    rows = [
        [InlineKeyboardButton("⬅️ روز قبل", callback_data=f"ec:date:{prev_d}"),
         InlineKeyboardButton("📅 امروز", callback_data="ec:today"),
         InlineKeyboardButton("روز بعد ➡️", callback_data=f"ec:date:{next_d}")],
        [InlineKeyboardButton("📆 فردا", callback_data="ec:tomorrow"), InlineKeyboardButton("🗓 هفته", callback_data="ec:week")],
        [InlineKeyboardButton("🔴 فقط مهم", callback_data="ec:impact:high"), InlineKeyboardButton("📋 همه خبرها", callback_data="ec:impact:all")],
        [InlineKeyboardButton("🤖 تحلیل هوشمند", callback_data="ec:ai"), InlineKeyboardButton("🔄 بروزرسانی", callback_data="ec:refresh")],
        [InlineKeyboardButton("💵 USD", callback_data="ec:cur:USD"), InlineKeyboardButton("💶 EUR", callback_data="ec:cur:EUR"), InlineKeyboardButton("💷 GBP", callback_data="ec:cur:GBP")],
    ]
    if events:
        for e in list(events)[:6]:
            rows.append([InlineKeyboardButton(
                f"{IMPACT_ICON.get(e['impact'], '⚪')} {e['country']} {e['title_fa'][:38]}",
                callback_data=f"ec:event:{e['id']}",
            )])
    rows.append([InlineKeyboardButton("🕐 تنظیم ساعت و فیلتر", callback_data="ec:settings")])
    return InlineKeyboardMarkup(rows)


def get_settings_keyboard(user_id: int):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from bot.database import get_economic_calendar_preferences
    p = get_economic_calendar_preferences(user_id)
    alert = "🔔 اعلان مهم: روشن" if p["alerts"] else "🔕 اعلان مهم: خاموش"
    lead = p["lead_minutes"]
    tz_name = p["timezone"] or getattr(config, "TIMEZONE", "Asia/Tehran")
    tz_label = {"Asia/Tehran": "ایران", "Asia/Baku": "آذربایجان", "UTC": "UTC"}.get(tz_name, tz_name)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(alert, callback_data="ec:toggle_alert")],
        [InlineKeyboardButton(f"⏱ هشدار {lead} دقیقه قبل", callback_data="ec:lead_menu")],
        [InlineKeyboardButton(f"🕐 ساعت: {tz_label}", callback_data="ec:tz_menu")],
        [InlineKeyboardButton("🔴 مهم | 🟠 متوسط | 🟡 کم", callback_data="ec:impact_menu")],
        [InlineKeyboardButton("↩️ برگشت به تقویم", callback_data="ec:back")],
    ])


def get_lead_keyboard():
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("۵ دقیقه", callback_data="ec:lead:5"), InlineKeyboardButton("۱۵ دقیقه", callback_data="ec:lead:15")],
        [InlineKeyboardButton("۳۰ دقیقه", callback_data="ec:lead:30"), InlineKeyboardButton("۶۰ دقیقه", callback_data="ec:lead:60")],
        [InlineKeyboardButton("↩️ برگشت", callback_data="ec:settings")],
    ])


def get_tz_keyboard():
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇮🇷 ایران", callback_data="ec:tz:Asia/Tehran"), InlineKeyboardButton("🇦🇿 آذربایجان", callback_data="ec:tz:Asia/Baku")],
        [InlineKeyboardButton("🌍 UTC", callback_data="ec:tz:UTC")],
        [InlineKeyboardButton("↩️ برگشت", callback_data="ec:settings")],
    ])


def get_event_keyboard(event_id: str):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 تحلیل این خبر با AI", callback_data=f"ec:analyze:{event_id}")],
        [InlineKeyboardButton("↩️ بازگشت به تقویم", callback_data="ec:back")],
    ])


async def get_calendar_for_user(user_id: int, mode: str = "today", impact: str = "all", currency: str = "", date_str: str = ""):
    """تقویم کاربر با پشتیبانی از تاریخچه و روز قبل/بعد.

    today شامل تمام رویدادهای همان روز است، حتی رویدادهایی که زمانشان گذشته؛
    بنابراین Actual بعد از انتشار از صفحه حذف نمی‌شود.
    """
    from bot.database import get_economic_calendar_preferences, get_economic_calendar_events
    p = get_economic_calendar_preferences(user_id)
    tz_name = p["timezone"] or getattr(config, "TIMEZONE", "Asia/Tehran")
    tz = _tz(tz_name)
    now = datetime.now(tz)

    # یک refresh سبک برای دریافت Actualهای تازه؛ تاریخچه از DB جداگانه خوانده می‌شود.
    await refresh_calendar()

    if date_str:
        try:
            selected = datetime.strptime(str(date_str), "%Y-%m-%d").date()
        except Exception:
            selected = now.date()
    elif mode == "tomorrow":
        selected = (now + timedelta(days=1)).date()
    elif mode == "yesterday":
        selected = (now - timedelta(days=1)).date()
    else:
        selected = now.date()

    if mode == "week":
        start_date = now.date()
        end_date = start_date + timedelta(days=7)
    else:
        start_date = selected
        end_date = selected + timedelta(days=1)

    start_local = tz.localize(datetime.combine(start_date, datetime.min.time()))
    end_local = tz.localize(datetime.combine(end_date, datetime.min.time()))
    start_utc = start_local.astimezone(timezone.utc)
    end_utc = end_local.astimezone(timezone.utc)

    # cache زنده + تاریخچه DB؛ DB مرجع رویدادهای گذشته است.
    merged: dict[str, dict[str, Any]] = {}
    for e in _cache:
        merged[e["id"]] = e
    try:
        rows = get_economic_calendar_events(start_utc, end_utc)
        for row in rows:
            e = {
                "id": row[0], "utc": _parse_dt(row[1]), "country": row[2] or "",
                "currency_name": row[3] or row[2] or "نامشخص", "impact": row[4] or "",
                "title": row[5] or "رویداد اقتصادی", "title_fa": row[6] or _fa_title(row[5] or "رویداد اقتصادی"),
                "actual": row[7] if row[7] is not None else "",
                "forecast": row[8] if row[8] is not None else "",
                "previous": row[9] if row[9] is not None else "",
                "source": row[10] or "Forex Factory",
            }
            if e["utc"] is not None:
                # DB may contain an older snapshot with blank Actual/Forecast/Previous.
                # Never let that stale blank overwrite fresher live values from _cache.
                # Conversely, keep any nonblank historical values stored in DB.
                existing = merged.get(e["id"])
                if existing:
                    for field in ("actual", "forecast", "previous"):
                        if not e.get(field) and existing.get(field):
                            e[field] = existing[field]
                    # Prefer the fresher/nonblank live metadata when available.
                    for field in ("country", "currency_name", "impact", "title", "title_fa", "source"):
                        if not e.get(field) and existing.get(field):
                            e[field] = existing[field]
                merged[e["id"]] = e
    except Exception as exc:
        logger.warning("economic calendar history read failed: %s", exc)

    out = []
    for e in merged.values():
        if not e.get("utc"):
            continue
        local = e["utc"].astimezone(tz)
        if not (start_local <= local < end_local):
            continue
        if currency and e["country"] != currency.upper():
            continue
        if impact and impact != "all" and e["impact"].lower() != impact.lower():
            continue
        out.append(e)
    out.sort(key=lambda e: e["utc"])
    return out, tz_name

