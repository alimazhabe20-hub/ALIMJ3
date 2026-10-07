"""economic_calendar: navigation responsibilities."""
from .economic_calendar_common import *  # noqa: F401,F403
from . import economic_calendar_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


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

def get_calendar_keyboard(user_id: int, *, mode: str = "today", impact: str = "all", events=None, currency: str = "", selected_date=None, page: int = 0, **_kwargs):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    # روز نسبی نسبت به selected_date (نه همیشه نسبت به «امروز سیستم»)
    base = (selected_date or "").strip()[:10]
    if not base:
        try:
            base = datetime.now(_tz(getattr(config, "TIMEZONE", "Asia/Tehran"))).strftime("%Y-%m-%d")
        except Exception:
            base = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows = [
        [
            InlineKeyboardButton("⬅️ دیروز", callback_data=f"ec:nav:{base}:-1"),
            InlineKeyboardButton("📅 امروز", callback_data="ec:today"),
            InlineKeyboardButton("فردا ➡️", callback_data=f"ec:nav:{base}:+1"),
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
            # دکمه با انگلیسی مخفف تا جمع‌وجور و خوانا باشد
            short_en = _en_short(e.get("title") or e.get("title_fa") or "", max_len=22)
            label = f"{IMPACT_ICON.get(e['impact'], '⚪')} {local.strftime('%H:%M')} {e['country']} {short_en}"
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

def fetch_speech_context(title: str, country: str = "") -> str:
    """تلاش برای دریافت خلاصه/متن مرتبط سخنرانی از منابع عمومی."""
    title = (title or "").strip()
    if not title:
        return ""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/json",
    }
    snippets: list[str] = []
    # ECB press conference landing
    urls = []
    low = title.lower()
    if "ecb" in low or "lagarde" in low or country.upper() == "EUR":
        urls.append("https://www.ecb.europa.eu/press/pressconf/html/index.en.html")
    if "fed" in low or "powell" in low or country.upper() == "USD":
        urls.append("https://www.federalreserve.gov/json/ne-press.json")
    for url in urls[:2]:
        try:
            r = requests.get(url, timeout=12, headers=headers)
            if r.status_code != 200:
                continue
            text = r.text
            if url.endswith(".json"):
                try:
                    data = r.json()
                    # Fed news JSON structure varies; take titles
                    items = data if isinstance(data, list) else data.get("item") or data.get("items") or []
                    for it in (items or [])[:5]:
                        if isinstance(it, dict):
                            snippets.append(str(it.get("title") or it.get("description") or "")[:300])
                except Exception:
                    snippets.append(text[:500])
            else:
                # strip tags lightly
                clean = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I)
                clean = re.sub(r"<style[\s\S]*?</style>", " ", clean, flags=re.I)
                clean = re.sub(r"<[^>]+>", " ", clean)
                clean = re.sub(r"\s+", " ", clean).strip()
                snippets.append(clean[:1200])
        except Exception:
            continue
    return "\n".join(s for s in snippets if s)[:2000]

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

def dedupe_day_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """حذف رویدادهای خیلی شبیه در یک روز (عنوان+ارز+نزدیکی زمانی)."""
    if not events:
        return []
    ranked = sorted(
        events,
        key=lambda e: (
            {"High": 0, "Medium": 1, "Low": 2}.get(str(e.get("impact") or ""), 9),
            0 if str(e.get("actual") or "").strip() else 1,
            e.get("utc") or datetime.min.replace(tzinfo=timezone.utc),
        ),
    )
    kept: list[dict[str, Any]] = []
    for e in ranked:
        tk = _title_key(e.get("title", ""))
        cur = (e.get("country") or "").upper()
        utc = e.get("utc")
        dup = False
        for k in kept:
            if (k.get("country") or "").upper() != cur:
                continue
            if _title_key(k.get("title", "")) != tk:
                # شباهت نرم: یکی زیرمجموعه دیگری
                kt = _title_key(k.get("title", ""))
                if not (tk and kt and (tk in kt or kt in tk)):
                    continue
            try:
                if utc and k.get("utc") and abs((utc - k["utc"]).total_seconds()) > 3 * 3600:
                    continue
            except Exception:
                pass
            dup = True
            break
        if not dup:
            kept.append(e)
    kept.sort(key=lambda e: e.get("utc") or datetime.min.replace(tzinfo=timezone.utc))
    return kept

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
    # شروع روز محلی به‌صورت امن (DST-aware)
    try:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    except Exception:
        start = datetime(now.year, now.month, now.day, tzinfo=tz)
    if date_str:
        try:
            y, m, d = [int(x) for x in str(date_str).strip()[:10].split("-")]
            naive = datetime(y, m, d)
            if hasattr(tz, "localize"):
                try:
                    start = tz.localize(naive, is_dst=None)
                except Exception:
                    start = tz.localize(naive, is_dst=False)
            else:
                start = naive.replace(tzinfo=tz)
        except Exception:
            logger.debug("invalid date_str=%s for calendar filter", date_str)
        end = start + timedelta(days=1)
    elif mode in {"tomorrow", "day+1"}:
        start = start + timedelta(days=1)
        end = start + timedelta(days=1)
    elif mode in {"yesterday", "day-1"}:
        start = start - timedelta(days=1)
        end = start + timedelta(days=1)
    elif mode == "week":
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
    # ترتیب زمانی همان روز + حذف تکراری‌های خیلی شبیه
    out = dedupe_day_events(out)
    out.sort(key=lambda e: e.get("utc") or datetime.min.replace(tzinfo=timezone.utc))
    return out, tz_name
