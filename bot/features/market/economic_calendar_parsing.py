"""economic_calendar: parsing responsibilities."""
from .economic_calendar_common import *  # noqa: F401,F403
from . import economic_calendar_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


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
    if not t:
        return "رویداد اقتصادی"
    if t in TITLE_MAP:
        return TITLE_MAP[t]
    low = t.lower()
    for k, v in sorted(TITLE_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        if low == k.lower():
            return v
    # تطبیق عنوان‌های شناخته‌شده داخل عنوان بلندتر
    for k, v in sorted(TITLE_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        if len(k) >= 8 and k.lower() in low and len(k) >= max(8, int(len(t) * 0.55)):
            return v
    out = t
    for k, v in sorted(TERM_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        out = re.sub(re.escape(k), v, out, flags=re.I)
    out = re.sub(r"\bHigh\b", "زیاد", out, flags=re.I)
    out = re.sub(r"\bMedium\b", "متوسط", out, flags=re.I)
    out = re.sub(r"\bLow\b", "کم", out, flags=re.I)
    # پاکسازی باقیمانده‌های انگلیسی کوتاه مثل of / the
    out = re.sub(r"\b(of|the|and|for|in|on|to)\b", " ", out, flags=re.I)
    out = re.sub(r"\s{2,}", " ", out).strip(" -|/\\")
    return out or t

def _en_short(title: str, *, max_len: int = 36) -> str:
    """نسخه انگلیسی مخفف برای متن اصلی و دکمه‌ها."""
    t = (title or "").strip()
    if not t:
        return ""
    out = t
    for full, abbr in sorted(_EN_ABBR, key=lambda x: len(x[0]), reverse=True):
        if full.lower() in out.lower():
            out = re.sub(re.escape(full), abbr, out, flags=re.I)
            break
    # پسوندهای زمانی — فقط در انتهای عنوان / با فاصله، نه وسط کلمه
    out = re.sub(r"(?i)\bmonthly\b", "m/m", out)
    out = re.sub(r"(?i)\byearly\b|\bannual(?:ly)?\b", "y/y", out)
    out = re.sub(r"(?i)\bquarterly\b", "q/q", out)
    # اگر هنوز m/m y/y جدا هستند نگه دار
    out = re.sub(r"(?i)\bmonth\b(?!\s*/)", "m/m", out)
    out = re.sub(r"(?i)\byear\b(?!\s*/)", "y/y", out)
    out = re.sub(r"(?i)\bquarter\b(?!\s*/)", "q/q", out)
    out = re.sub(r"\bManufacturing\b", "Mfg", out, flags=re.I)
    out = re.sub(r"\bProduction\b", "Prod", out, flags=re.I)
    out = re.sub(r"\bConstruction\b", "Const", out, flags=re.I)
    out = re.sub(r"\bServices?\b", "Svc", out, flags=re.I)
    # اگر q/q اول آمده جابجا کن: "q/q Unemp Rate" → "Unemp Rate q/q"
    out = re.sub(r"^(m/m|y/y|q/q)\s+(.+)$", r"\2 \1", out.strip())
    out = re.sub(r"\bIndex\b", "Idx", out, flags=re.I)
    out = re.sub(r"\bBalance\b", "Bal", out, flags=re.I)
    out = re.sub(r"\bOutput\b", "Out", out, flags=re.I)
    out = re.sub(r"\bPreliminary\b|\bPrelim\b", "Prel", out, flags=re.I)
    out = re.sub(r"\bPrevious\b", "Prev", out, flags=re.I)
    out = re.sub(r"\s{2,}", " ", out).strip()
    if len(out) > max_len:
        out = out[: max_len - 1].rstrip() + "…"
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

def _esc(value: Any) -> str:
    return html.escape(str(value), quote=False)

def _parse_num(value: Any) -> float | None:
    if value is None:
        return None
    s = str(value).strip().replace(",", "").replace("%", "").replace("K", "").replace("M", "").replace("B", "")
    if not s or s in {"—", "-", "None", "null", "منتشر نشده", "در انتظار انتشار"}:
        return None
    # e.g. 5.22|2.4
    if "|" in s:
        s = s.split("|", 1)[0].strip()
    try:
        return float(s)
    except Exception:
        m = re.search(r"[-+]?\d*\.?\d+", s)
        if not m:
            return None
        try:
            return float(m.group(0))
        except Exception:
            return None

def _unit_for_event(e: dict[str, Any] | None) -> str:
    if not e:
        return ""
    title = f"{e.get('title', '')} {e.get('title_fa', '')}".lower()
    unit = str(e.get("unit") or "").lower()
    mult = str(e.get("multiplier") or "").lower()
    if any(x in title for x in ("m/m", "y/y", "q/q", "cpi", "ppi", "inflation", "rate", "unemployment", "%", "percent")):
        return "%"
    if "percent" in unit or unit in {"%", "pct"}:
        return "%"
    if any(x in title for x in ("claims", "jobless")) or mult in {"thousands", "thousand"}:
        return "K"
    if any(x in title for x in ("inventory", "inventories", "sales", "home sales")) or mult in {"millions", "million"}:
        if "home sales" in title or "existing home" in title:
            return "M"
        return "M"
    if mult in {"billions", "billion"} or any(x in title for x in ("storage", "crude")):
        return "B"
    return str(e.get("display_unit") or "")
