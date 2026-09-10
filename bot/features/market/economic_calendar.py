"""تقویم اقتصادی زنده برای بخش بازار.

منبع پیش‌فرض: خروجی هفتگی عمومی Forex Factory/faireconomy.media.
دریافت عمداً کم‌دفعات انجام می‌شود تا به محدودیت منبع احترام گذاشته شود.
"""
from __future__ import annotations

import asyncio
import difflib
import hashlib
import html
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import pytz
import requests
from bs4 import BeautifulSoup

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
CACHE_TTL = 5 * 60
HISTORICAL_HTML_URLS = (
    "https://calendar.forexfactory.com/calendar?week={slug}",
    "https://www.forexfactory.com/calendar?week={slug}",
    "https://calendar.forexfactory.com/calendar/",
    "https://www.forexfactory.com/calendar/",
)
HISTORICAL_TZ = pytz.timezone("Europe/London")
BIQUOTE_CALENDAR_URL = "https://biquote.io/api/calendar"
BIQUOTE_COUNTRY_TO_CURRENCY = {
    "US": "USD", "EU": "EUR", "GB": "GBP", "AU": "AUD", "CA": "CAD",
    "JP": "JPY", "CH": "CHF", "NZ": "NZD", "CN": "CNY", "NO": "NOK",
    "SE": "SEK", "HK": "HKD", "SG": "SGD", "MX": "MXN", "IN": "INR",
    "TR": "TRY", "ZA": "ZAR", "BR": "BRL", "KR": "KRW", "ID": "IDR",
    "RU": "RUB", "SA": "SAR", "AR": "ARS", "PL": "PLN", "CZ": "CZK",
    "HU": "HUF", "DK": "DKK", "IL": "ILS", "AE": "AED", "TW": "TWD",
}
TRADINGVIEW_CALENDAR_URL = "https://economic-calendar.tradingview.com/events"
TRADINGVIEW_COUNTRIES = ("AR", "AU", "BR", "CA", "CN", "FR", "DE", "IN", "ID", "IT", "JP", "KR", "MX", "RU", "SA", "ZA", "TR", "GB", "US", "EU")
TRADINGVIEW_COUNTRY_TO_CURRENCY = {"US": "USD", "EU": "EUR", "GB": "GBP", "AU": "AUD", "CA": "CAD", "JP": "JPY", "CH": "CHF", "NZ": "NZD", "CN": "CNY", "NO": "NOK", "SE": "SEK", "HK": "HKD", "SG": "SGD", "MX": "MXN", "IN": "INR", "TR": "TRY", "ZA": "ZAR"}
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



def _week_slug(dt: datetime) -> str:
    """Forex Factory week slug, e.g. sep9.2026."""
    return dt.strftime("%b%-d.%Y").lower()


def _parse_ff_date(text: str, year_hint: int) -> datetime | None:
    text = " ".join((text or "").split())
    m = re.search(r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)?\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})\b", text, re.I)
    if not m:
        return None
    try:
        return datetime.strptime(f"{m.group(1)} {m.group(2)} {year_hint}", "%b %d %Y")
    except Exception:
        return None


def _parse_ff_time(text: str) -> tuple[int, int] | None:
    m = re.search(r"\b(\d{1,2}):(\d{2})\s*([ap]m)\b", (text or "").lower())
    if not m:
        return None
    hour, minute = int(m.group(1)), int(m.group(2))
    if m.group(3) == "pm" and hour != 12:
        hour += 12
    if m.group(3) == "am" and hour == 12:
        hour = 0
    return hour, minute


def _parse_ff_historical_html(text: str, year_hint: int) -> list[dict[str, Any]]:
    """Extract published Actual/Forecast/Previous values from Forex Factory HTML.

    FF puts the date on the first/merged date cell of calendar rows rather than
    reliably using a dedicated day-break <tr>, so the parser must carry the
    latest non-empty .calendar__date value forward across rows.
    """
    soup = BeautifulSoup(text, "html.parser")
    out: list[dict[str, Any]] = []
    current_date: datetime | None = None

    rows = soup.select("tr.calendar__row.calendar_row, tr.calendar_row")
    for tr in rows:
        # The date cell is often populated only on the first event of a day;
        # subsequent rows inherit it through current_date.
        date_cell = tr.select_one(".calendar__date")
        if date_cell:
            parsed_day = _parse_ff_date(date_cell.get_text(" ", strip=True), year_hint)
            if parsed_day:
                current_date = parsed_day

        # Some FF variants expose a standalone day-break row. Keep support for it.
        classes = " ".join(tr.get("class") or [])
        if "day-break" in classes or "calendar__day" in classes:
            parsed_day = _parse_ff_date(tr.get_text(" ", strip=True), year_hint)
            if parsed_day:
                current_date = parsed_day
            continue

        cur = tr.select_one(".calendar__currency")
        event = tr.select_one(".calendar__event")
        if not cur or not event or not current_date:
            continue

        currency = cur.get_text(" ", strip=True).upper()
        title = event.get_text(" ", strip=True)
        time_cell = tr.select_one(".calendar__time")
        parsed_time = _parse_ff_time(time_cell.get_text(" ", strip=True) if time_cell else "")
        if parsed_time:
            dt_local = HISTORICAL_TZ.localize(
                current_date.replace(hour=parsed_time[0], minute=parsed_time[1])
            )
        else:
            dt_local = HISTORICAL_TZ.localize(current_date)

        def cell_value(*selectors: str) -> str:
            for selector in selectors:
                node = tr.select_one(selector)
                if node:
                    value = node.get_text(" ", strip=True)
                    if value:
                        return value
            return ""

        out.append({
            "utc": dt_local.astimezone(timezone.utc),
            "country": currency,
            "title": title,
            "actual": cell_value(".calendar__actual", ".calendar-actual"),
            "forecast": cell_value(".calendar__forecast", ".calendar-forecast"),
            "previous": cell_value(".calendar__previous", ".calendar-previous"),
        })
    return out


def _fetch_historical_html(url: str) -> str:
    r = requests.get(
        url,
        timeout=18,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "Chrome/131.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.8",
        },
    )
    r.raise_for_status()
    return r.text


def _html_rows_to_events(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert FF HTML rows into the same normalized shape used by the JSON feed."""
    out: list[dict[str, Any]] = []
    for row in rows:
        utc = row.get("utc")
        if not isinstance(utc, datetime):
            continue
        raw = {
            "date": utc.isoformat(),
            "country": row.get("country", ""),
            "title": row.get("title", ""),
            "impact": row.get("impact", ""),
            "actual": row.get("actual", ""),
            "forecast": row.get("forecast", ""),
            "previous": row.get("previous", ""),
        }
        event = _normalize(raw)
        if event:
            out.append(event)
    return out


def _fetch_biquote_calendar(start_utc: datetime, end_utc: datetime) -> list[dict[str, Any]]:
    """Fetch published macro values from Biquote's public calendar API.

    Biquote exposes actual/forecast/previous directly and requires no API key.
    The function is intentionally best-effort: Forex Factory remains the
    preferred event/impact source when available.
    """
    params = {
        "from": start_utc.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "to": end_utc.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "limit": 500,
    }
    r = requests.get(
        BIQUOTE_CALENDAR_URL,
        params=params,
        timeout=15,
        headers={
            "Accept": "application/json",
            "User-Agent": "ALIMJ-EconomicCalendar/1.0",
        },
    )
    r.raise_for_status()
    payload = r.json()
    if not isinstance(payload, list):
        return []
    out: list[dict[str, Any]] = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        dt = _parse_dt(str(row.get("time") or row.get("date") or ""))
        if not dt:
            continue
        code = str(row.get("currency") or row.get("countryCode") or "").upper().strip()
        currency = BIQUOTE_COUNTRY_TO_CURRENCY.get(code, code)
        title = str(row.get("name") or row.get("title") or "").strip()
        if not currency or not title:
            continue
        out.append({
            "utc": dt,
            "country": currency,
            "title": title,
            "actual": _raw_value(row, "actual"),
            "forecast": _raw_value(row, "forecast"),
            "previous": _raw_value(row, "previous"),
            "importance": str(row.get("importance") or "").strip().title(),
            "id": str(row.get("eventId") or row.get("id") or "").strip(),
        })
    return out


def _normalize_biquote_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build calendar events from Biquote when Forex Factory is unavailable."""
    out: list[dict[str, Any]] = []
    for row in rows:
        raw = {
            "date": row.get("utc", ""),
            "country": row.get("country", ""),
            "title": row.get("title", ""),
            "impact": row.get("importance", ""),
            "actual": row.get("actual", ""),
            "forecast": row.get("forecast", ""),
            "previous": row.get("previous", ""),
        }
        if isinstance(raw["date"], datetime):
            raw["date"] = raw["date"].isoformat()
        event = _normalize(raw)
        if event:
            event["source"] = "Biqoute"
            # Keep the provider identifier as an additional hint, while the
            # database/event id remains stable for the bot's callbacks.
            if row.get("id"):
                event["provider_id"] = row["id"]
            out.append(event)
    return out


def _merge_biquote_values(events: list[dict[str, Any]], rows: list[dict[str, Any]]) -> int:
    """Conservatively enrich FF events with Biquote's published values.

    A value is accepted only when currency/date/time and title agree strongly.
    Forecast/previous are used as corroborating signals when available, which
    prevents generic titles such as PPI or housing indicators from cross-matching.
    """
    merged = 0
    for row in rows:
        r_title = _normalize_title(row.get("title"))
        r_currency = str(row.get("country") or "").upper().strip()
        r_utc = row.get("utc")
        if not r_title or not r_currency or not isinstance(r_utc, datetime):
            continue
        candidates = []
        for event in events:
            if str(event.get("country") or "").upper().strip() != r_currency:
                continue
            e_utc = event.get("utc")
            if not isinstance(e_utc, datetime) or e_utc.date() != r_utc.date():
                continue
            diff = abs((e_utc - r_utc).total_seconds())
            if diff > 30 * 60:
                continue
            e_title = _normalize_title(event.get("title"))
            if not e_title:
                continue
            ratio = difflib.SequenceMatcher(None, e_title, r_title).ratio()
            rt, et = set(r_title.split()), set(e_title.split())
            overlap = len(rt & et) / max(1, len(rt | et))
            title_ok = ratio >= 0.90 or (ratio >= 0.82 and overlap >= 0.70)
            if not title_ok:
                continue
            corroboration = 0
            for field in ("forecast", "previous"):
                rv = str(row.get(field) or "").strip().lower()
                ev = str(event.get(field) or "").strip().lower()
                if rv and ev and rv == ev:
                    corroboration += 1
            # Exact title can stand on its own; looser title matches need at
            # least one existing FF value to agree.
            if ratio < 0.90 and corroboration == 0:
                continue
            score = ratio * 0.72 + overlap * 0.18 + min(corroboration, 2) * 0.05 - min(diff / 1800, 1) * 0.03
            candidates.append((score, event))
        if not candidates:
            continue
        _, event = max(candidates, key=lambda x: x[0])
        for field in ("actual", "forecast", "previous"):
            value = str(row.get(field) or "").strip()
            if value and not str(event.get(field) or "").strip():
                event[field] = row.get(field)
                if field == "actual":
                    merged += 1
    return merged


def _merge_historical_values(events: list[dict[str, Any]], rows: list[dict[str, Any]]) -> int:
    """Merge published values from the same Forex Factory calendar HTML.

    Matching is deliberately conservative: same currency, same local event
    date, close event time, and strong title similarity.  A false Actual is
    materially worse than leaving Actual blank.
    """
    merged = 0
    for row in rows:
        r_title = _normalize_title(row.get("title"))
        r_currency = str(row.get("country") or "").strip().upper()
        r_utc = row.get("utc")
        if not r_title or not r_currency or not isinstance(r_utc, datetime):
            continue
        candidates = []
        for event in events:
            if str(event.get("country") or "").strip().upper() != r_currency:
                continue
            e_utc = event.get("utc")
            if not isinstance(e_utc, datetime) or e_utc.date() != r_utc.date():
                continue
            diff = abs((e_utc - r_utc).total_seconds())
            if diff > 45 * 60:
                continue
            e_title = _normalize_title(event.get("title"))
            if not e_title:
                continue
            ratio = difflib.SequenceMatcher(None, e_title, r_title).ratio()
            rt, et = set(r_title.split()), set(e_title.split())
            overlap = len(rt & et) / max(1, len(rt | et))
            # Exact/near-exact title wins. For paraphrased titles, require
            # substantial token overlap as well as a high sequence score.
            if not (ratio >= 0.88 or (ratio >= 0.78 and overlap >= 0.65)):
                continue
            score = ratio * 0.85 + overlap * 0.15 - min(diff / 3600, 0.75) * 0.03
            candidates.append((score, event))
        if not candidates:
            continue
        _, event = max(candidates, key=lambda x: x[0])
        for field in ("actual", "forecast", "previous"):
            value = str(row.get(field) or "").strip()
            if value and not str(event.get(field) or "").strip():
                event[field] = value
                if field == "actual":
                    merged += 1
    return merged


def _fetch_tradingview_actuals(start_utc: datetime, end_utc: datetime) -> list[dict[str, Any]]:
    params = {
        "from": start_utc.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "to": end_utc.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "countries": ",".join(TRADINGVIEW_COUNTRIES),
    }
    headers = {
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.8",
        "Cache-Control": "no-cache",
        "Origin": "https://www.tradingview.com",
        "Referer": "https://www.tradingview.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36",
    }
    r = requests.get(TRADINGVIEW_CALENDAR_URL, params=params, headers=headers, timeout=18)
    r.raise_for_status()
    payload = r.json()
    rows = payload.get("result", []) if isinstance(payload, dict) else []
    out = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict) or row.get("actual") in (None, ""):
            continue
        dt = _parse_dt(str(row.get("date") or ""))
        country = TRADINGVIEW_COUNTRY_TO_CURRENCY.get(str(row.get("country") or "").upper().strip(), str(row.get("country") or "").upper().strip())
        title = str(row.get("title") or row.get("indicator") or "").strip()
        if dt and country and title:
            out.append({"utc": dt, "country": country, "title": title, "actual": row.get("actual")})
    return out


def _merge_tradingview_actuals(events: list[dict[str, Any]], rows: list[dict[str, Any]]) -> int:
    merged = 0
    for row in rows:
        rkey = _tv_title_key(row.get("title"))
        candidates = []
        for event in events:
            if event.get("country") != row.get("country") or event["utc"].date() != row["utc"].date():
                continue
            diff = abs((event["utc"] - row["utc"]).total_seconds())
            if diff > 4 * 3600:
                continue
            ekey = _tv_title_key(event.get("title"))
            ratio = difflib.SequenceMatcher(None, ekey, rkey).ratio()
            rt, et = set(rkey.split()), set(ekey.split())
            overlap = len(rt & et) / max(1, len(rt | et))
            if ratio >= 0.62 or (overlap >= 0.5 and ratio >= 0.5):
                score = ratio * 0.75 + overlap * 0.25 - min(diff / 3600, 4) * 0.02
                candidates.append((score, event))
        if candidates:
            _, event = max(candidates, key=lambda x: x[0])
            value = str(row.get("actual") or "").strip()
            if value and not str(event.get("actual") or "").strip():
                event["actual"] = value
                merged += 1
    return merged


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

        # Biquote is the actual-value fallback. It is independent of Forex
        # Factory's weekly JSON (which omits Actual) and does not require an API
        # key. Keep its matching deliberately strict to avoid false Actuals.
        biquote_rows: list[dict[str, Any]] = []
        try:
            now_utc = datetime.now(timezone.utc)
            biquote_rows = await asyncio.to_thread(
                _fetch_biquote_calendar, now_utc - timedelta(days=2), now_utc + timedelta(days=2)
            )
            if biquote_rows and normalized:
                merged_bq = _merge_biquote_values(normalized, biquote_rows)
                if merged_bq:
                    logger.info("economic calendar: merged %d Actual value(s) from Biquote", merged_bq)
            elif biquote_rows and not normalized:
                normalized = _normalize_biquote_rows(biquote_rows)
                if normalized:
                    logger.info("economic calendar: using Biquote as primary source (%d events)", len(normalized))
        except Exception as exc:
            logger.debug("economic calendar Biquote source failed: %s", exc)

        # Do not merge TradingView values into Forex Factory events here.
        # TradingView titles are not a stable one-to-one identifier (especially
        # for generic PPI, housing, inventory and rate indicators), so fuzzy
        # matching can silently attach an unrelated Actual value to an event.
        # Actual enrichment is intentionally sourced from the Forex Factory
        # calendar HTML below, where event/title/time context is consistent.

        # The JSON export is convenient but can be unavailable/blocked. The public
        # Forex Factory calendar page is a reliable fallback and also contains the
        # already-published Actual values. When JSON is empty, build the calendar
        # entirely from HTML instead of returning "source unavailable".
        html_rows: list[dict[str, Any]] = []
        try:
            now_utc = datetime.now(timezone.utc)
            # Current week first; yesterday/previous week is only needed for
            # history enrichment and is intentionally best-effort.
            current_slug = _week_slug(now_utc)
            current_errors = []
            for template in HISTORICAL_HTML_URLS:
                try:
                    url = template.format(slug=current_slug)
                    current_html = await asyncio.to_thread(_fetch_historical_html, url)
                    parsed = _parse_ff_historical_html(current_html, now_utc.year)
                    if parsed:
                        html_rows.extend(parsed)
                        break
                except Exception as exc:
                    current_errors.append(str(exc))
            if not html_rows and current_errors:
                logger.debug("economic calendar current HTML fallbacks failed: %s", " | ".join(current_errors[:4]))

            if normalized:
                previous_dt = now_utc - timedelta(days=7)
                previous_errors = []
                for template in HISTORICAL_HTML_URLS:
                    try:
                        url = template.format(slug=_week_slug(previous_dt))
                        previous_html = await asyncio.to_thread(_fetch_historical_html, url)
                        parsed = _parse_ff_historical_html(previous_html, previous_dt.year)
                        if parsed:
                            html_rows.extend(parsed)
                            break
                    except Exception as exc:
                        previous_errors.append(str(exc))
                if previous_errors and not any(r.get("utc").date() == previous_dt.date() for r in html_rows if r.get("utc")):
                    logger.debug("economic calendar previous-week HTML fallbacks failed: %s", " | ".join(previous_errors[:4]))

            if html_rows:
                if normalized:
                    _merge_historical_values(normalized, html_rows)
                else:
                    normalized = _html_rows_to_events(html_rows)
        except Exception as exc:
            logger.debug("economic calendar HTML source failed: %s", exc)

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

