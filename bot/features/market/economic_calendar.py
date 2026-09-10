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
MAJOR_CURRENCIES = ("USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF")

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


def _stable_event_id(dt: datetime, country: str, title: str) -> str:
    """شناسه پایدار بر اساس زمان UTC دقیق تا دقیقه + ارز + عنوان نرمال‌شده.
    بین منبع FF و biquote یکسان می‌ماند تا دکمه‌ها بعد از refresh نشکنند.
    """
    utc = dt.astimezone(timezone.utc)
    base = f"{utc.strftime('%Y-%m-%dT%H:%M')}|{(country or '').upper()}|{_title_key(title)}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]


def _event_id(raw: dict[str, Any]) -> str:
    dt = _parse_dt(raw.get("date", ""))
    title = str(raw.get("title") or raw.get("event") or "").strip()
    country = str(raw.get("country") or raw.get("currency") or "").upper().strip()
    if dt:
        return _stable_event_id(dt, country, title)
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
        "actual": raw.get("actual") or "",
        "forecast": raw.get("forecast") or "",
        "previous": raw.get("previous") or "",
        "source": "Forex Factory",
    }




FF_HTML_URLS = (
    "https://www.forexfactory.com/calendar?week=this",
    "https://www.forexfactory.com/calendar?week=next",
)


def _ff_html_text(node) -> str:
    if node is None:
        return ""
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()


def _parse_ff_html(url: str) -> list[dict[str, Any]]:
    r = requests.get(url, timeout=18, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json,text/html,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.forexfactory.com/",
    })
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    out: list[dict[str, Any]] = []
    current_date = ""
    for row in soup.select("tr.calendar__row, tr.calendar_row"):
        date_node = row.select_one(".calendar__date")
        date_text = _ff_html_text(date_node)
        if date_text:
            current_date = date_text
        time_text = _ff_html_text(row.select_one(".calendar__time"))
        currency = _ff_html_text(row.select_one(".calendar__currency"))
        title = _ff_html_text(row.select_one(".calendar__event"))
        if not currency or not title or not current_date:
            continue
        actual = _ff_html_text(row.select_one(".calendar__actual"))
        forecast = _ff_html_text(row.select_one(".calendar__forecast"))
        previous = _ff_html_text(row.select_one(".calendar__previous"))
        # HTML is localized to Europe/London by Forex Factory. We only use
        # its date for matching; the JSON feed remains the authoritative time.
        out.append({
            "date_text": current_date,
            "time_text": time_text,
            "country": currency.upper(),
            "title": title,
            "actual": actual,
            "forecast": forecast,
            "previous": previous,
        })
    return out


def _ff_date_key(text: str) -> str:
    m = re.search(r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+([A-Z][a-z]{2})\s+(\d{1,2})", text or "")
    return f"{m.group(1)} {m.group(2)}" if m else ""


def _title_key(text: str) -> str:
    t = re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()
    return re.sub(r"\s+", " ", t)


def _merge_ff_html_values(events: list[dict[str, Any]], rows: list[dict[str, Any]]) -> None:
    if not events or not rows:
        return
    # Match by local London date + currency + normalized title. This deliberately
    # ignores the HTML clock because the JSON feed supplies the canonical UTC time.
    lookup: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    london = pytz.timezone("Europe/London")
    for r in rows:
        key = (_ff_date_key(r.get("date_text", "")), r["country"], _title_key(r["title"]))
        lookup.setdefault(key, []).append(r)
    for e in events:
        local = e["utc"].astimezone(london)
        date_key = local.strftime("%b %-d")
        key = (date_key, e["country"], _title_key(e["title"]))
        candidates = lookup.get(key, [])
        if not candidates:
            # Some FF rows include a country prefix or a trailing revision marker.
            ek = _title_key(e["title"])
            for (dk, cur, tk), vals in lookup.items():
                if dk == date_key and cur == e["country"] and (ek == tk or ek in tk or tk in ek):
                    candidates.extend(vals)
        if not candidates:
            continue
        r = candidates[0]
        # HTML is the published source. Fill and revise values only when nonblank;
        # never replace a known JSON value with an empty HTML cell.
        for field in ("actual", "forecast", "previous"):
            value = (r.get(field) or "").strip()
            if value:
                e[field] = value


def _refresh_ff_html_values(events: list[dict[str, Any]]) -> None:
    all_rows: list[dict[str, Any]] = []
    for url in FF_HTML_URLS:
        try:
            all_rows.extend(_parse_ff_html(url))
        except Exception as exc:
            logger.debug("Forex Factory HTML enrichment failed for %s: %s", url, exc)
    if all_rows:
        _merge_ff_html_values(events, all_rows)



BIQUOTE_URL = "https://biquote.io/api/calendar"


def _to_str_num(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        try:
            if value != value:  # NaN
                return ""
        except Exception:
            pass
        # integers that are whole
        if float(value) == int(value) and abs(value) >= 100:
            return str(int(value))
        s = f"{float(value):.6f}".rstrip("0").rstrip(".")
        return s
    return str(value).strip()


def _biquote_importance(value: str) -> str:
    v = (value or "").lower().strip()
    return {"high": "High", "medium": "Medium", "low": "Low"}.get(v, value or "")


def _fetch_biquote(day_from: str, day_to: str) -> list[dict[str, Any]]:
    r = requests.get(
        BIQUOTE_URL,
        params={"from": day_from, "to": day_to},
        timeout=18,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json",
        },
    )
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        raise ValueError("biquote calendar format invalid")
    return data



def _normalize_biquote_row(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Convert a biquote calendar row into the internal event schema."""
    t = str(raw.get("time") or "").replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(t).astimezone(timezone.utc)
    except Exception:
        return None
    cur = str(raw.get("currency") or raw.get("countryCode") or "").upper().strip()
    cur = {
        "US": "USD", "EU": "EUR", "GB": "GBP", "JP": "JPY", "AU": "AUD",
        "NZ": "NZD", "CA": "CAD", "CH": "CHF", "CN": "CNY",
    }.get(cur, cur)
    title = str(raw.get("name") or "رویداد اقتصادی").strip()
    impact = _biquote_importance(str(raw.get("importance") or ""))
    actual = _to_str_num(raw.get("actual"))
    forecast = _to_str_num(raw.get("forecast"))
    previous = _to_str_num(
        raw.get("previous") if raw.get("previous") is not None else raw.get("revisedPrevious")
    )
    eid = _stable_event_id(dt, cur, title)
    return {
        "id": eid,
        "utc": dt,
        "country": cur,
        "currency_name": CURRENCY_NAMES.get(cur, cur or "نامشخص"),
        "impact": impact if impact in IMPACT_FA else (impact.title() if impact else ""),
        "title": title,
        "title_fa": _fa_title(title),
        "actual": actual,
        "forecast": forecast,
        "previous": previous,
        "source": "biquote",
    }


def _load_biquote_events(days_back: int = 1, days_forward: int = 8) -> list[dict[str, Any]]:
    today = datetime.now(timezone.utc).date()
    day_from = (today - timedelta(days=max(0, days_back))).isoformat()
    day_to = (today + timedelta(days=max(1, days_forward))).isoformat()
    rows = _fetch_biquote(day_from, day_to)
    out = [e for e in (_normalize_biquote_row(r) for r in rows) if e]
    dedup = {e["id"]: e for e in out}
    return sorted(dedup.values(), key=lambda e: e["utc"])[:_MAX_EVENTS]

def _merge_biquote_values(events: list[dict[str, Any]], rows: list[dict[str, Any]]) -> None:
    """Fill blank actual/forecast/previous from biquote when FF JSON is empty."""
    if not events or not rows:
        return

    parsed_rows: list[tuple[datetime, str, str, dict[str, Any]]] = []
    for r in rows:
        t = str(r.get("time") or "").replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(t).astimezone(timezone.utc)
        except Exception:
            continue
        cur = str(r.get("currency") or r.get("countryCode") or "").upper().strip()
        # Map common country codes to FF currency codes
        cur = {"US": "USD", "EU": "EUR", "GB": "GBP", "JP": "JPY", "AU": "AUD",
               "NZ": "NZD", "CA": "CAD", "CH": "CHF", "CN": "CNY"}.get(cur, cur)
        if not cur:
            continue
        name = str(r.get("name") or "")
        parsed_rows.append((dt, cur, _title_key(name), r))

    for e in events:
        if str(e.get("actual") or "").strip() and str(e.get("forecast") or "").strip():
            # already complete enough
            pass
        ek = _title_key(e["title"])
        e_cur = e["country"]
        e_utc = e["utc"].astimezone(timezone.utc)
        candidates: list[tuple[int, dict[str, Any]]] = []
        for dt, cur, tk, r in parsed_rows:
            if cur != e_cur:
                continue
            # same calendar day UTC preferred; allow ±3h across midnight edges
            same_day = dt.date() == e_utc.date()
            delta = abs((dt - e_utc).total_seconds())
            if not same_day and delta > 3 * 3600:
                continue
            if not tk or not ek:
                continue
            # title similarity score
            if ek == tk:
                score = 0
            elif ek in tk or tk in ek:
                score = 1
            else:
                # token overlap
                et, tt = set(ek.split()), set(tk.split())
                if not et or not tt or len(et & tt) < max(1, min(len(et), len(tt)) // 2):
                    continue
                score = 2
            if delta > 6 * 3600:
                score += 3
            elif delta > 2 * 3600:
                score += 1
            # prefer rows that have actual
            if r.get("actual") is None:
                score += 1
            candidates.append((score, r))
        if not candidates:
            continue
        candidates.sort(key=lambda x: x[0])
        r = candidates[0][1]
        mapping = {
            "actual": _to_str_num(r.get("actual")),
            "forecast": _to_str_num(r.get("forecast")),
            "previous": _to_str_num(
                r.get("previous") if r.get("previous") is not None else r.get("revisedPrevious")
            ),
        }
        for field, value in mapping.items():
            if value and not str(e.get(field) or "").strip():
                e[field] = value


def _refresh_biquote_values(events: list[dict[str, Any]]) -> None:
    if not events:
        return
    days = sorted({e["utc"].astimezone(timezone.utc).strftime("%Y-%m-%d") for e in events})
    if not days:
        return
    day_from = days[0]
    # exclusive-ish end: last day + 1 handled by API range inclusivity; pass last+1 day string loosely
    last = datetime.strptime(days[-1], "%Y-%m-%d").date()
    day_to = (last + timedelta(days=1)).isoformat()
    rows = _fetch_biquote(day_from, day_to)
    _merge_biquote_values(events, rows)

def _fetch_json(url: str) -> list[dict[str, Any]]:
    r = requests.get(url, timeout=18, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json,text/html,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.forexfactory.com/",
    })
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

        errors: list[str] = []
        normalized: list[dict[str, Any]] = []

        # 1) PRIMARY: biquote — includes published Actual values
        try:
            normalized = await asyncio.to_thread(_load_biquote_events, 1, 8)
            if normalized:
                logger.info("economic calendar primary source=biquote events=%s", len(normalized))
        except Exception as exc:
            errors.append(f"biquote:{exc}")
            logger.warning("economic calendar biquote primary failed: %s", exc)

        # 2) SECONDARY: Forex Factory schedule (titles/impact) merged on top when biquote thin
        ff_rows: list[dict[str, Any]] = []
        for i, url in enumerate(FF_URLS):
            try:
                rows = await asyncio.to_thread(_fetch_json, url)
                ff_rows.extend(rows)
            except Exception as exc:
                errors.append(f"ff:{exc}")
                try:
                    rows = await asyncio.to_thread(_fetch_json, FF_FALLBACK_URLS[i])
                    ff_rows.extend(rows)
                except Exception as exc2:
                    errors.append(f"ff-fallback:{exc2}")

        ff_norm = [e for e in (_normalize(x) for x in ff_rows) if e]
        if ff_norm:
            if not normalized:
                normalized = ff_norm
                logger.warning("economic calendar using FF only (%s events)", len(normalized))
            else:
                # Merge: keep biquote values; add FF-only events; upgrade impact/title from FF when matched
                by_id = {e["id"]: e for e in normalized}
                for fe in ff_norm:
                    if fe["id"] in by_id:
                        be = by_id[fe["id"]]
                        # Prefer non-empty numeric fields from either side
                        for field in ("actual", "forecast", "previous"):
                            if not str(be.get(field) or "").strip() and str(fe.get(field) or "").strip():
                                be[field] = fe[field]
                        # FF impact labels are often cleaner
                        if fe.get("impact"):
                            be["impact"] = fe["impact"]
                        if fe.get("title") and len(fe["title"]) >= len(be.get("title") or ""):
                            be["title"] = fe["title"]
                            be["title_fa"] = fe.get("title_fa") or _fa_title(fe["title"])
                    else:
                        by_id[fe["id"]] = fe
                normalized = sorted(by_id.values(), key=lambda e: e["utc"])[:_MAX_EVENTS]

        # 3) Extra enrichment pass: fill remaining blank actuals from a fresh biquote pull
        if normalized:
            try:
                await asyncio.to_thread(_refresh_biquote_values, normalized)
            except Exception as exc:
                logger.debug("economic calendar biquote enrichment failed: %s", exc)
            try:
                await asyncio.to_thread(_refresh_ff_html_values, normalized)
            except Exception as exc:
                logger.debug("economic calendar HTML enrichment failed: %s", exc)

        if normalized:
            _cache = normalized
            _cache_fetched_at = time.time()
            _cache_expires = time.monotonic() + CACHE_TTL
            if errors:
                logger.warning("economic calendar partial refresh: %s", " | ".join(errors[:4]))
            return list(_cache)

        if _cache:
            logger.warning("economic calendar refresh failed; using stale cache: %s", " | ".join(errors[:4]))
            return list(_cache)

        raise RuntimeError(
            "تقویم اقتصادی فعلاً از منبع زنده دریافت نشد."
            + ((" جزئیات: " + " | ".join(errors[:2])) if errors else "")
        )



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


def format_value(value: Any, *, empty: str = "در انتظار انتشار") -> str:
    if value is None:
        return empty
    s = str(value).strip()
    if not s or s in {"None", "null", "—", "-"}:
        return empty
    return s


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=False)


def _impact_label(e: dict[str, Any]) -> str:
    return IMPACT_FA.get(e.get("impact", ""), e.get("impact") or "نامشخص")


def format_event(e: dict[str, Any], tz_name: str = "", *, show_date: bool = False) -> str:
    local = _event_local(e, tz_name)
    icon = IMPACT_ICON.get(e["impact"], "⚪")
    title_fa = _esc(e["title_fa"])
    title_en = _esc(e["title"])
    now = datetime.now(_tz(tz_name))
    past = local < now
    past_mark = " ✅" if past else ""
    actual_empty = "منتشر نشده" if past else "در انتظار انتشار"
    other_empty = "—"
    when = local.strftime("%m/%d %H:%M") if show_date else local.strftime("%H:%M")
    return (
        f"{icon} <b>{when} | {_esc(e['country'])} | {title_fa}</b>{past_mark}\n"
        f"   <i>{title_en}</i>\n"
        f"   🚦 <b>اهمیت:</b> {_esc(_impact_label(e))}"
        f"  •  📢 <b>واقعی:</b> {_esc(format_value(e.get('actual'), empty=actual_empty))}"
        f"  •  🔮 <b>پیش‌بینی:</b> {_esc(format_value(e.get('forecast'), empty=other_empty))}"
        f"  •  ◀️ <b>قبلی:</b> {_esc(format_value(e.get('previous'), empty=other_empty))}"
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
        return "\n".join(lines)

    rank = {"High": 0, "Medium": 1, "Low": 2, "Holiday": 3}
    ordered = sorted(
        events,
        key=lambda e: (
            rank.get(str(e.get("impact") or ""), 9),
            e.get("utc") or datetime.min.replace(tzinfo=timezone.utc),
        ),
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


def get_event(events, event_id: str):
    if not events or not event_id:
        return None
    for e in events:
        if e.get("id") == event_id:
            return e
    return None


def find_event(events, event_id: str = "", *, title: str = "", country: str = "", utc=None):
    """Find by stable id, then by title+country+time proximity."""
    e = get_event(events, event_id)
    if e:
        return e
    tk = _title_key(title)
    cur = (country or "").upper()
    best = None
    best_score = 10**9
    for cand in events or []:
        score = 0
        if cur and cand.get("country") != cur:
            continue
        if tk:
            ctk = _title_key(cand.get("title", ""))
            if tk != ctk and tk not in ctk and ctk not in tk:
                continue
        if utc is not None and cand.get("utc") is not None:
            try:
                delta = abs((cand["utc"] - utc).total_seconds())
            except Exception:
                delta = 0
            score = delta
        if score < best_score:
            best_score = score
            best = cand
    return best


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
    return (
        f"{IMPACT_ICON.get(e['impact'], '⚪')} <b>{_esc(e['title_fa'])}</b>\n"
        f"<i>{_esc(e['title'])}</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💱 <b>ارز:</b> {_esc(e['country'])} — {_esc(e['currency_name'])}\n"
        f"📅 <b>تاریخ:</b> <code>{local.strftime('%Y/%m/%d')}</code>\n"
        f"⏰ <b>ساعت:</b> <code>{local.strftime('%H:%M')}</code>\n"
        f"🚦 <b>اهمیت:</b> {_esc(_impact_label(e))}\n"
        f"⏳ <b>وضعیت:</b> {_esc(countdown)}\n\n"
        f"📢 <b>واقعی:</b> {_esc(format_value(e.get('actual'), empty=actual_empty))}\n"
        f"🔮 <b>پیش‌بینی:</b> {_esc(format_value(e.get('forecast'), empty='—'))}\n"
        f"◀️ <b>قبلی:</b> {_esc(format_value(e.get('previous'), empty='—'))}\n\n"
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


def get_calendar_keyboard(user_id: int, *, mode: str = "today", impact: str = "all", events=None, currency: str = "", selected_date=None, page: int = 0, **_kwargs):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    rows = [
        [
            InlineKeyboardButton("⬅️ دیروز", callback_data="ec:day:-1"),
            InlineKeyboardButton("📅 امروز", callback_data="ec:today"),
            InlineKeyboardButton("فردا ➡️", callback_data="ec:day:+1"),
        ],
        [
            InlineKeyboardButton("🔴 فقط مهم", callback_data="ec:impact:high"),
            InlineKeyboardButton("📋 همه خبرهای روز", callback_data="ec:impact:all"),
        ],
        [
            InlineKeyboardButton("🤖 تحلیل هوشمند روز", callback_data="ec:ai"),
            InlineKeyboardButton("🔔 اعلان‌ها", callback_data="ec:settings"),
        ],
        [
            InlineKeyboardButton("💵 USD", callback_data="ec:cur:USD"),
            InlineKeyboardButton("💶 EUR", callback_data="ec:cur:EUR"),
            InlineKeyboardButton("💷 GBP", callback_data="ec:cur:GBP"),
        ],
        [InlineKeyboardButton("🔄 بروزرسانی", callback_data="ec:refresh")],
    ]
    # دکمه هر خبر همان روز
    if events:
        tz_name = getattr(config, "TIMEZONE", "Asia/Tehran")
        for e in list(events)[:40]:
            local = e["utc"].astimezone(_tz(tz_name))
            label = f"{IMPACT_ICON.get(e['impact'], '⚪')} {local.strftime('%H:%M')} {e['country']} {e['title_fa'][:28]}"
            rows.append([InlineKeyboardButton(label, callback_data=f"ec:event:{e['id']}")])
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


def is_speech_event(e: dict[str, Any] | None) -> bool:
    if not e:
        return False
    t = f"{e.get('title', '')} {e.get('title_fa', '')}".lower()
    keys = ("speech", "speaks", "press conference", "سخنرانی", "کنفرانس خبری", "remarks", "testimony")
    return any(k in t for k in keys)


def get_event_keyboard(event_id: str, e: dict[str, Any] | None = None):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    rows = [[InlineKeyboardButton("🤖 تحلیل این خبر با AI", callback_data=f"ec:analyze:{event_id}")]]
    if is_speech_event(e):
        rows.append([InlineKeyboardButton("🗣 خلاصه سخنرانی", callback_data=f"ec:speech:{event_id}")])
    rows.append([InlineKeyboardButton("↩️ بازگشت به تقویم", callback_data="ec:back")])
    return InlineKeyboardMarkup(rows)


async def get_calendar_for_user(
    user_id: int,
    mode: str = "today",
    impact: str = "all",
    currency: str = "",
    date_str: str = "",
):
    from bot.database import get_economic_calendar_preferences
    p = get_economic_calendar_preferences(user_id)
    tz_name = p["timezone"] or getattr(config, "TIMEZONE", "Asia/Tehran")
    # فیلتر اهمیت فقط از پارامتر UI می‌آید (دکمه «فقط مهم»)، نه از pref پیش‌فرض
    # همیشه فقط یک روز مشخص (نه کل هفته در یک پیام)
    events = await refresh_calendar()
    tz = _tz(tz_name)
    now = datetime.now(tz)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if date_str:
        try:
            y, m, d = [int(x) for x in str(date_str).strip()[:10].split("-")]
            start = tz.localize(datetime(y, m, d)) if hasattr(tz, "localize") else datetime(y, m, d, tzinfo=tz)
        except Exception:
            pass
        end = start + timedelta(days=1)
    elif mode in {"tomorrow", "day+1"}:
        start = start + timedelta(days=1)
        end = start + timedelta(days=1)
    elif mode in {"yesterday", "day-1"}:
        start = start - timedelta(days=1)
        end = start + timedelta(days=1)
    elif mode == "week":
        # سازگاری با دکمه قدیمی: همان امروز
        end = start + timedelta(days=1)
    else:
        end = start + timedelta(days=1)
    out = []
    cur = (currency or "").upper().strip()
    # فقط ارزهای اصلی بازار؛ لیست شلوغ کشورها نمایش داده نمی‌شود.
    majors_only = True
    for e in events:
        local = e["utc"].astimezone(tz)
        if not (start <= local < end):
            continue
        country = (e.get("country") or "").upper()
        if cur and country != cur:
            continue
        if majors_only and country not in MAJOR_CURRENCIES:
            continue
        imp = (e.get("impact") or "").lower()
        if impact and impact != "all" and imp != impact.lower():
            continue
        out.append(e)
    # مرتب‌سازی: اول اهمیت، بعد زمان
    rank = {"high": 0, "medium": 1, "low": 2, "holiday": 3}
    out.sort(key=lambda e: (rank.get((e.get("impact") or "").lower(), 9), e.get("utc") or datetime.min.replace(tzinfo=timezone.utc)))
    return out, tz_name
