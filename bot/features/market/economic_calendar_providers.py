"""economic_calendar: providers responsibilities."""
from .economic_calendar_common import *  # noqa: F401,F403
from . import economic_calendar_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def _ff_html_text(node) -> str:
    if node is None:
        return ""
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()

def _ff_impact(row) -> str:
    """Extract Forex Factory impact from icon/class across HTML layouts."""
    node = (
        row.select_one(".calendar__impact")
        or row.select_one("td.calendar__cell.calendar__impact")
        or row.select_one("[class*='impact']")
    )
    if node is None:
        return ""
    classes = " ".join(node.get("class") or [])
    title = str(node.get("title") or node.get("data-impact") or "")
    raw = f"{classes} {title} {_ff_html_text(node)}".lower()
    if "high" in raw or "red" in raw:
        return "High"
    if "medium" in raw or "orange" in raw or "yellow" in raw:
        return "Medium"
    if "low" in raw:
        return "Low"
    if "holiday" in raw:
        return "Holiday"
    return ""

def _ff_cell_text(row, field: str) -> str:
    """Extract a calendar cell across old/new FF HTML layouts."""
    selectors = (
        f".calendar__{field}",
        f"td.calendar__cell.calendar__{field}.{field}",
        f"td.calendar__{field}.{field}",
    )
    for selector in selectors:
        node = row.select_one(selector)
        if node is None:
            continue
        value = _ff_html_text(node)
        if value:
            return value
    return ""

def _parse_ff_html(url: str) -> list[dict[str, Any]]:
    r = requests.get(url, timeout=(5, 15), headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.forexfactory.com/",
    })
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    out: list[dict[str, Any]] = []
    current_date = ""

    rows = soup.select("tr.calendar__row.calendar_row, tr.calendar_row")
    for row in rows:
        date_text = _ff_cell_text(row, "date")
        if date_text:
            current_date = date_text

        time_text = _ff_cell_text(row, "time")
        currency = _ff_cell_text(row, "currency")
        title = _ff_cell_text(row, "event")
        if not currency or not title or not current_date:
            continue

        out.append({
            "date_text": current_date,
            "time_text": time_text,
            "country": currency.upper(),
            "title": title,
            "actual": _ff_cell_text(row, "actual"),
            "forecast": _ff_cell_text(row, "forecast"),
            "previous": _ff_cell_text(row, "previous"),
            "impact": _ff_impact(row),
        })
    return out

def _parse_ff_html_events(url: str) -> list[dict[str, Any]]:
    """Turn a live Forex Factory HTML week page into the internal event schema."""
    rows = _parse_ff_html(url)
    if not rows:
        return []

    tz = pytz.timezone("Europe/London")
    now_local = datetime.now(tz)
    out: list[dict[str, Any]] = []
    current_year = now_local.year

    for row in rows:
        date_text = str(row.get("date_text") or "").strip()
        time_text = str(row.get("time_text") or "").strip()
        # Typical FF date: "Mon Oct 8"; time: "8:30am".
        dm = re.search(r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+([A-Za-z]{3})\s+(\d{1,2})", date_text)
        if not dm:
            dm = re.search(r"([A-Za-z]{3})\s+(\d{1,2})", date_text)
        if not dm:
            continue
        month, day = dm.group(1), int(dm.group(2))
        year = current_year
        try:
            if datetime(year, datetime.strptime(month, "%b").month, day).date() < (now_local.date() - timedelta(days=330)):
                year += 1
        except Exception:
            continue

        hour, minute = 0, 0
        tm = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", time_text, re.I)
        if tm:
            hour = int(tm.group(1))
            minute = int(tm.group(2) or 0)
            ap = (tm.group(3) or "").lower()
            if ap == "pm" and hour < 12:
                hour += 12
            elif ap == "am" and hour == 12:
                hour = 0

        try:
            naive = datetime(year, datetime.strptime(month, "%b").month, day, hour, minute)
            local_dt = tz.localize(naive, is_dst=None)
            dt = local_dt.astimezone(timezone.utc)
        except Exception:
            continue

        cur = str(row.get("country") or "").upper().strip()
        title = str(row.get("title") or "رویداد اقتصادی").strip()
        impact = str(row.get("impact") or "").strip().title()
        if impact not in IMPACT_FA:
            impact = "Low"

        out.append({
            "id": _stable_event_id(dt, cur, title),
            "utc": dt,
            "country": cur,
            "currency_name": CURRENCY_NAMES.get(cur, cur or "نامشخص"),
            "impact": impact,
            "title": title,
            "title_fa": _fa_title(title),
            "actual": row.get("actual") or "",
            "forecast": row.get("forecast") or "",
            "previous": row.get("previous") or "",
            "source": "Forex Factory HTML",
        })
    return out

def _load_ff_html_events() -> list[dict[str, Any]]:
    """Live fallback independent of the faireconomy CDN/JSON endpoints."""
    errors: list[str] = []
    for url in FF_HTML_URLS:
        try:
            events = _parse_ff_html_events(url)
            if events:
                return events
        except Exception as exc:
            errors.append(str(exc))
            logger.debug("economic calendar live HTML fallback failed for %s: %s", url, exc)
    if errors:
        logger.warning("economic calendar all live HTML fallbacks failed: %s", " | ".join(errors[:2]))
    return []


def _ff_daily_urls(day: datetime) -> list[str]:
    """Build daily FF calendar URLs for a specific date."""
    day_text = f"{day.strftime('%b').lower()}{day.day}.{day.year}"
    return [f"{host}?day={day_text}" for host in FF_DAILY_HTML_HOSTS]

def _refresh_ff_html_values(events: list[dict[str, Any]]) -> None:
    if not events:
        return

    # First try the current/next week pages (fast path).
    all_rows: list[dict[str, Any]] = []
    for url in FF_HTML_URLS:
        try:
            rows = _parse_ff_html(url)
            if rows:
                all_rows.extend(rows)
        except Exception as exc:
            logger.debug("Forex Factory HTML enrichment failed for %s: %s", url, exc)

    _merge_ff_html_values(events, all_rows)

    # Critical fallback: for already-past events whose Actual is still blank,
    # fetch their exact calendar day. The weekly JSON feed does not carry Actual,
    # while the daily HTML page does.
    missing = [e for e in events if not str(e.get("actual") or "").strip()]
    if not missing:
        return

    london = pytz.timezone("Europe/London")
    days_needed = sorted({
        e["utc"].astimezone(london).date()
        for e in missing
        if e.get("utc")
    })

    for day in days_needed:
        day_dt = datetime.combine(day, datetime.min.time())
        day_rows: list[dict[str, Any]] = []

        for url in _ff_daily_urls(day_dt):
            try:
                rows = _parse_ff_html(url)
                if rows:
                    day_rows.extend(rows)
                    # One successful source for this exact day is enough.
                    break
            except Exception as exc:
                logger.debug("Forex Factory daily HTML failed for %s: %s", url, exc)

        if day_rows:
            _merge_ff_html_values(missing, day_rows)
            missing = [e for e in missing if not str(e.get("actual") or "").strip()]
            if not missing:
                break

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
        # %-d روی بعضی پلتفرم‌ها ValueError می‌دهد
        date_key = local.strftime("%b ") + str(local.day)
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
    # actual ممکن است 0 معتبر باشد؛ فقط None/خالی را خالی بگذار
    actual_raw = raw.get("actual")
    if actual_raw is None or actual_raw == "":
        for _key in ("releasedActual", "actualValue", "releasedValue"):
            _candidate = raw.get(_key)
            if _candidate is not None and _candidate != "":
                actual_raw = _candidate
                break
    if actual_raw is None or actual_raw == "":
        actual = ""
    else:
        actual = _to_str_num(actual_raw)
    forecast = _to_str_num(raw.get("forecast"))
    prev_raw = raw.get("previous")
    if prev_raw is None:
        prev_raw = raw.get("revisedPrevious")
    previous = _to_str_num(prev_raw)
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

def _load_biquote_events(days_back: int = 2, days_forward: int = 8) -> list[dict[str, Any]]:
    """بارگذاری چندپنجره‌ای — API حدود ۲۰۰ ردیف برمی‌گرداند و اگر بازه خیلی پهن باشد
    رویدادهای آینده حذف می‌شوند. پس گذشته و آینده جداگانه گرفته می‌شوند.
    """
    today = datetime.now(timezone.utc).date()
    windows = [
        # دیروز تا امروز (برای Actualهای منتشرشده)
        (today - timedelta(days=max(0, days_back)), today),
        # امروز تا چند روز جلو
        (today, today + timedelta(days=max(1, min(3, days_forward)))),
    ]
    if days_forward > 3:
        windows.append(
            (today + timedelta(days=3), today + timedelta(days=max(4, days_forward)))
        )
    # پنجره اختصاصی فردا برای اطمینان
    windows.append((today + timedelta(days=1), today + timedelta(days=2)))

    dedup: dict[str, dict[str, Any]] = {}
    for start, end in windows:
        if end < start:
            continue
        try:
            rows = _fetch_biquote(start.isoformat(), end.isoformat())
        except Exception as exc:
            logger.debug("biquote window %s..%s failed: %s", start, end, exc)
            continue
        for r in rows:
            e = _normalize_biquote_row(r)
            if not e:
                continue
            prev = dedup.get(e["id"])
            if not prev:
                dedup[e["id"]] = e
                continue
            # اگر نسخه جدید Actual/Forecast دارد، جایگزین کن
            for field in ("actual", "forecast", "previous"):
                if str(e.get(field) or "").strip() and not str(prev.get(field) or "").strip():
                    prev[field] = e[field]
            if e.get("impact") and (not prev.get("impact") or prev.get("impact") == "Low"):
                prev["impact"] = e["impact"]
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
            normalized = await asyncio.to_thread(_load_biquote_events, 2, 8)
            if normalized:
                logger.info("economic calendar primary source=biquote events=%s", len(normalized))
        except Exception as exc:
            errors.append(f"biquote:{exc}")
            logger.warning("economic calendar biquote primary failed: %s", exc)

        # 2) SECONDARY: Forex Factory JSON — همیشه تلاش می‌کنیم (کم‌صدا)؛
        # برای forecast/previous/impact و رویدادهای غایب مفید است. فیلد actual در JSON اغلب خالی است.
        ff_rows: list[dict[str, Any]] = []
        for i, url in enumerate(FF_URLS):
            try:
                rows = await asyncio.to_thread(_fetch_json, url)
                ff_rows.extend(rows)
            except Exception as exc:
                logger.debug("economic calendar FF secondary failed: %s", exc)
                try:
                    rows = await asyncio.to_thread(_fetch_json, FF_FALLBACK_URLS[i])
                    ff_rows.extend(rows)
                except Exception as exc2:
                    logger.debug("economic calendar FF fallback failed: %s", exc2)
                    errors.append(f"ff:{exc2}")

        ff_norm = [e for e in (_normalize(x) for x in ff_rows) if e]
        # 2b) LIVE FALLBACK: direct Forex Factory HTML. This does not depend on
        # nfs/cdn-nfs.faireconomy.media and can still provide Actual/Forecast/Previous.
        if not normalized and not ff_norm:
            html_norm = await asyncio.to_thread(_load_ff_html_events)
            if html_norm:
                normalized = html_norm
                logger.info("economic calendar live fallback source=forexfactory_html events=%s", len(normalized))
        elif normalized and not ff_norm:
            html_norm = await asyncio.to_thread(_load_ff_html_events)
            if html_norm:
                by_id = {e["id"]: e for e in normalized}
                for he in html_norm:
                    existing = by_id.get(he["id"])
                    if existing:
                        for field in ("actual", "forecast", "previous"):
                            if not str(existing.get(field) or "").strip() and str(he.get(field) or "").strip():
                                existing[field] = he[field]
                        if he.get("impact"):
                            existing["impact"] = he["impact"]
                    else:
                        by_id[he["id"]] = he
                normalized = sorted(by_id.values(), key=lambda e: e["utc"])[:_MAX_EVENTS]
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
                        for field in ("actual", "forecast", "previous"):
                            if not str(be.get(field) or "").strip() and str(fe.get(field) or "").strip():
                                be[field] = fe[field]
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
            if errors and not normalized:
                logger.warning("economic calendar partial refresh: %s", " | ".join(errors[:4]))
            elif errors:
                logger.debug("economic calendar secondary noise: %s", " | ".join(errors[:2]))
            return list(_cache)

        if _cache:
            logger.warning("economic calendar refresh failed; using stale cache: %s", " | ".join(errors[:4]))
            return list(_cache)

        # Never expose provider/DNS/network internals to Telegram users.
        logger.warning("economic calendar live refresh unavailable: %s", " | ".join(errors[:4]))
        raise RuntimeError("تقویم اقتصادی فعلاً در دسترس نیست.")
