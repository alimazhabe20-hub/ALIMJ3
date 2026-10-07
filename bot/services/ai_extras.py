"""
قابلیت‌های اضافه دستیار: نمودار، جستجوی وب، کش جواب برای دکمه ویس،
یادآوری زبان‌طبیعی، OCR فیش، و کمک‌کننده‌های استریم.
"""
from __future__ import annotations

import io
import re
import time
import hashlib
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta

import pytz

from bot.logger import logger

TEHRAN = pytz.timezone("Asia/Tehran")

# answer_id -> (user_id, text, expires, prompt)
_ANSWER_CACHE: Dict[str, Tuple[int, str, float, str]] = {}
_CACHE_TTL = 3600 * 6

_LAST_ANSWER: Dict[int, str] = {}
# user_id -> last original user prompt (for continue)
_LAST_PROMPT: Dict[int, str] = {}
# user_id -> last answer_id
_LAST_ANSWER_ID: Dict[int, str] = {}

# ===== merged from bot/services/ai_extras_parts/part_001_parse_natural_weather.py =====
from typing import Optional
from typing import Tuple

# Auto-split part 1: parse_natural_weather
def parse_natural_weather(text: str) -> Optional[Tuple[str, bool]]:
    """تشخیص درخواست طبیعی هوا و تعیین شهر/پیش‌بینی بدون وابستگی به AI."""
    raw = (text or "").strip()
    if not raw:
        return None
    normalized = raw.replace("ي", "ی").replace("ك", "ک").replace("‌", " ")

    # دکمه‌های منوی رسمی باید مسیر معمول خودشان را حفظ کنند.
    if normalized in {"هوا و مکان", "🌤 هوا و مکان", "پیش‌بینی هوا", "🌤 پیش‌بینی هوا", "کیفیت هوا", "🌫 کیفیت هوا"}:
        return None

    if not re.search(r"(?:آب\s*و\s*هوا|هوا|دما|باران|بارون|رگبار|آفتابی|ابری|رطوبت|پیش\s*بینی)", normalized, re.I):
        return None

    # «فردا/پس‌فردا/این هفته...» یعنی پیش‌بینی؛ برای سؤال ساده هوا، وضعیت فعلی را می‌گیریم.
    forecast = bool(re.search(
        r"فردا|پس\s*فردا|امروز\s*و\s*فردا|هفته|روزهای\s*آینده|چند\s*روز|پیش\s*بینی",
        normalized, re.I,
    ))

    from bot.features.weather.features_weather_weather_extra import CITY_COORDS
    city = ""
    # شهرهای شناخته‌شده را از طولانی‌ترین نام به کوتاه‌ترین بررسی کن.
    for candidate in sorted(CITY_COORDS, key=len, reverse=True):
        if candidate in normalized:
            city = candidate
            break

    # برای «هوا چطوره؟» شهر خالی می‌ماند تا ابزار شهر کاربر را انتخاب کند.
    if not city and not forecast and not re.search(r"چط(?:وره|وری)|چگونه|چجوری|وضعیت|دما", normalized, re.I):
        return None
    return city, forecast

# ===== end merged part =====

# ===== merged from bot/services/ai_extras_parts/part_002_parse_natural_crypto_price.py =====
from typing import Optional

# Auto-split part 2: parse_natural_crypto_price
def parse_natural_crypto_price(text: str) -> Optional[str]:
    """تشخیص درخواست قیمت زنده یک رمزارز مشخص برای جلوگیری از پاسخ حدسی AI."""
    normalized = (text or "").strip().replace("ي", "ی").replace("ك", "ک").replace("‌", " ")
    if not re.search(r"قیمت|نرخ|چنده|چقدر|price", normalized, re.I):
        return None
    aliases = [
        (r"بیت\s*کوین|بیتکویین|bitcoin|btc", "btc"),
        (r"اتریوم|ethereum|eth", "eth"),
        (r"تتر|tether|usdt", "usdt"),
        (r"سولانا|solana|sol", "sol"),
        (r"ریپل|xrp", "xrp"),
        (r"دوج\s*کوین|dogecoin|doge", "doge"),
        (r"bnb|بایننس", "bnb"),
        (r"کاردانو|cardano|ada", "ada"),
    ]
    for pattern, symbol in aliases:
        if re.search(pattern, normalized, re.I):
            return symbol
    return None

# ===== end merged part =====

# ===== merged from bot/services/ai_extras_parts/part_003_store_answer.py =====
# Auto-split part 3: store_answer
def store_answer(user_id: int, text: str, prompt: str = "") -> str:
    """ذخیره جواب برای دکمه ویس، ادامه پاسخ و درخواست «ویس بفرست»."""
    aid = hashlib.md5(f"{user_id}:{time.time()}:{text[:80]}".encode()).hexdigest()[:12]
    _ANSWER_CACHE[aid] = (user_id, text or "", time.time() + _CACHE_TTL, prompt or "")
    if text:
        _LAST_ANSWER[user_id] = text
        _LAST_ANSWER_ID[user_id] = aid
    if prompt:
        _LAST_PROMPT[user_id] = prompt
    if len(_ANSWER_CACHE) > 2000:
        now = time.time()
        dead = [k for k, v in _ANSWER_CACHE.items() if v[2] < now]
        for k in dead[:500]:
            _ANSWER_CACHE.pop(k, None)
    return aid

# ===== end merged part =====

# ===== merged from bot/services/ai_extras_parts/part_004_get_stored_answer.py =====
from typing import Optional

# Auto-split part 4: get_stored_answer
def get_stored_answer(answer_id: str, user_id: int) -> Optional[str]:
    item = _ANSWER_CACHE.get(answer_id)
    if not item:
        return None
    uid, text, exp, _prompt = item if len(item) == 4 else (*item, "")
    if exp < time.time() or uid != user_id:
        return None
    return text

# ===== end merged part =====

# ===== merged from bot/services/ai_extras_parts/part_005_get_stored_prompt.py =====
from typing import Optional

# Auto-split part 5: get_stored_prompt
def get_stored_prompt(answer_id: str, user_id: int) -> Optional[str]:
    item = _ANSWER_CACHE.get(answer_id)
    if not item:
        return None
    if len(item) == 4:
        uid, _text, exp, prompt = item
    else:
        uid, _text, exp = item
        prompt = ""
    if exp < time.time() or uid != user_id:
        return None
    return prompt or _LAST_PROMPT.get(user_id)

# ===== end merged part =====

# ===== merged from bot/services/ai_extras_parts/part_006_get_last_answer.py =====
from typing import Optional

# Auto-split part 6: get_last_answer
def get_last_answer(user_id: int) -> Optional[str]:
    """آخرین جواب AI همین کاربر."""
    return _LAST_ANSWER.get(user_id) or None

# ===== end merged part =====

# ===== merged from bot/services/ai_extras_parts/part_007_get_last_prompt.py =====
from typing import Optional

# Auto-split part 7: get_last_prompt
def get_last_prompt(user_id: int) -> Optional[str]:
    return _LAST_PROMPT.get(user_id)

# ===== end merged part =====

# ===== merged from bot/services/ai_extras_parts/part_008_get_last_answer_id.py =====
from typing import Optional

# Auto-split part 8: get_last_answer_id
def get_last_answer_id(user_id: int) -> Optional[str]:
    return _LAST_ANSWER_ID.get(user_id)

# ===== end merged part =====

# ── نمودار ──────────────────────────────────────────────────────────────────

# ===== merged from bot/services/ai_extras_parts/part_009_make_chart_image.py =====
from typing import List

# Auto-split part 9: make_chart_image
def make_chart_image(
    title: str,
    labels: List[str],
    values: List[float],
    chart_type: str = "bar",
) -> bytes:
    """ساخت تصویر نمودار PNG با matplotlib."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise RuntimeError("matplotlib نصب نیست. به requirements اضافه کن: matplotlib") from e

    if not labels or not values or len(labels) != len(values):
        raise RuntimeError("برای نمودار به برچسب و عدد هم‌تعداد نیاز است.")

    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=140)
    chart_type = (chart_type or "bar").lower()
    if chart_type == "line":
        ax.plot(labels, values, marker="o", linewidth=2)
    elif chart_type == "pie":
        ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
        ax.axis("equal")
    else:
        ax.bar(labels, values, color="#3b82f6")
        ax.tick_params(axis="x", rotation=30)

    if chart_type != "pie":
        ax.set_title(title or "نمودار")
        ax.grid(True, axis="y", alpha=0.3)
    else:
        ax.set_title(title or "نمودار")

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()

# ===== end merged part =====

# ===== merged from bot/services/ai_extras_parts/part_010_parse_chart_request.py =====
from typing import List
from typing import Optional
from typing import Tuple

# Auto-split part 10: parse_chart_request
def parse_chart_request(text: str) -> Optional[Tuple[str, List[str], List[float], str]]:
    """
    تلاش برای فهم درخواست نمودار از متن.
    مثال: نمودار میله‌ای قیمت: دلار 60000، یورو 65000
    """
    t = (text or "").strip()
    if not re.search(r"نمودار|chart|گراف", t, re.I):
        return None
    ctype = "bar"
    if re.search(r"خطی|line", t, re.I):
        ctype = "line"
    elif re.search(r"دایره|pie", t, re.I):
        ctype = "pie"

    # pairs: name number
    pairs = re.findall(
        r"([A-Za-zآ-یء‌]+)\s*[:=：]?\s*([0-9۰-۹]+(?:[.,][0-9۰-۹]+)?)",
        t,
    )
    if len(pairs) < 2:
        return None

    def _num(s: str) -> float:
        s = s.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")).replace(",", "")
        return float(s)

    labels = [p[0] for p in pairs]
    values = [_num(p[1]) for p in pairs]
    title = "نمودار"
    m = re.search(r"نمودار\s*([^:\n]+)", t)
    if m:
        title = m.group(1).strip()[:60] or title
    return title, labels, values, ctype

# ===== end merged part =====

# ── جستجوی وب ───────────────────────────────────────────────────────────────

# ===== merged from bot/services/ai_extras_parts/part_011_web_search.py =====
# Auto-split part 11: web_search  (v79 — real search APIs + keyless fallback)
#
# Provider order (first one with a key wins, then automatic fallback to the next):
#   1. TAVILY_API_KEY   -> https://tavily.com           (best for LLMs: returns page text)
#   2. BRAVE_API_KEY    -> https://brave.com/search/api  (also BRAVE_SEARCH_API_KEY)
#   3. SERPER_API_KEY   -> https://serper.dev            (Google results)
#   4. SEARXNG_URL      -> your own SearXNG instance     (free, self-hosted)
#   5. DuckDuckGo HTML  -> no key, last resort (snippets only)
#
# The query is sent AS IS. (Older versions appended "(current as of DATE)" to the
# query which polluted results; freshness is now requested via provider params.)

_WS_NEWS_RE = None


def _ws_env(*names: str) -> str:
    import os
    for n in names:
        v = (os.getenv(n) or "").strip()
        if v:
            return v
    return ""


def _ws_is_newsy(query: str) -> bool:
    global _WS_NEWS_RE
    import re
    if _WS_NEWS_RE is None:
        _WS_NEWS_RE = re.compile(
            r"خبر|اخبار|امروز|دیشب|امشب|الان|اخیر|جدیدترین|آخرین|news|latest|today|breaking|"
            r"نتیجه|برنده|انتخابات|رونمایی|عرضه|release|launch",
            re.I,
        )
    return bool(_WS_NEWS_RE.search(query or ""))


def _ws_fmt(title: str, url: str, snippet: str = "", date: str = "") -> str:
    block = f"• {title}\n  {url}"
    if date:
        block += f"\n  تاریخ انتشار: {date}"
    if snippet:
        block += f"\n  خلاصه: {snippet}"
    return block


async def _ws_tavily(client, query: str, n: int, newsy: bool) -> list[str]:
    key = _ws_env("TAVILY_API_KEY")
    if not key:
        return []
    body = {
        "api_key": key,
        "query": query,
        "max_results": n,
        "search_depth": "advanced" if n >= 6 else "basic",
        "include_answer": False,
        "topic": "news" if newsy else "general",
    }
    if newsy:
        body["days"] = 14
    r = await client.post("https://api.tavily.com/search", json=body)
    r.raise_for_status()
    out = []
    for it in (r.json().get("results") or [])[:n]:
        text = (it.get("content") or "").strip().replace("\n", " ")
        out.append(_ws_fmt(
            it.get("title") or it.get("url") or "",
            it.get("url") or "",
            text[:600],
            str(it.get("published_date") or ""),
        ))
    return out


async def _ws_brave(client, query: str, n: int, newsy: bool) -> list[str]:
    key = _ws_env("BRAVE_API_KEY", "BRAVE_SEARCH_API_KEY")
    if not key:
        return []
    params = {"q": query, "count": n}
    if newsy:
        params["freshness"] = "pm"  # past month
    r = await client.get(
        "https://api.search.brave.com/res/v1/web/search",
        params=params,
        headers={"X-Subscription-Token": key, "Accept": "application/json"},
    )
    r.raise_for_status()
    out = []
    for it in ((r.json().get("web") or {}).get("results") or [])[:n]:
        desc = (it.get("description") or "").replace("<strong>", "").replace("</strong>", "")
        out.append(_ws_fmt(it.get("title") or "", it.get("url") or "", desc[:600], str(it.get("age") or "")))
    return out


async def _ws_serper(client, query: str, n: int, newsy: bool) -> list[str]:
    key = _ws_env("SERPER_API_KEY")
    if not key:
        return []
    body = {"q": query, "num": n, "hl": "fa"}
    if newsy:
        body["tbs"] = "qdr:m"
    r = await client.post(
        "https://google.serper.dev/search", json=body,
        headers={"X-API-KEY": key, "Content-Type": "application/json"},
    )
    r.raise_for_status()
    out = []
    for it in (r.json().get("organic") or [])[:n]:
        out.append(_ws_fmt(it.get("title") or "", it.get("link") or "", (it.get("snippet") or "")[:600], str(it.get("date") or "")))
    return out


async def _ws_searxng(client, query: str, n: int, newsy: bool) -> list[str]:
    base = _ws_env("SEARXNG_URL").rstrip("/")
    if not base:
        return []
    params = {"q": query, "format": "json", "language": "fa"}
    if newsy:
        params["time_range"] = "month"
    r = await client.get(f"{base}/search", params=params)
    r.raise_for_status()
    out = []
    for it in (r.json().get("results") or [])[:n]:
        out.append(_ws_fmt(it.get("title") or "", it.get("url") or "", (it.get("content") or "")[:600], str(it.get("publishedDate") or "")))
    return out


async def _ws_duckduckgo(client, query: str, n: int, newsy: bool) -> list[str]:
    from bs4 import BeautifulSoup

    data = {"q": query}
    if newsy:
        data["df"] = "m"  # last month
    r = await client.post(
        "https://html.duckduckgo.com/html/",
        data=data,
        headers={"User-Agent": "Mozilla/5.0 (compatible; RoozeZibaBot/1.0)"},
    )
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    out = []
    for node in soup.select(".result")[:n]:
        a = node.select_one("a.result__a")
        if not a:
            continue
        sn = node.select_one(".result__snippet")
        out.append(_ws_fmt(
            a.get_text(" ", strip=True),
            a.get("href") or "",
            sn.get_text(" ", strip=True) if sn else "",
        ))
    return out


async def web_search(query: str, max_results: int = 5) -> str:
    """Live web search with freshness metadata and bounded snippets.

    Never invents a result: if every provider fails the response starts with
    LIVE_DATA_UNAVAILABLE so the AI layer refuses to present stale model
    knowledge as current data.
    """
    from datetime import datetime, timezone

    query = (query or "").strip()
    if not query:
        return "LIVE_DATA_UNAVAILABLE: عبارت جستجو خالی است."
    max_results = max(1, min(int(max_results or 5), 10))
    date_tag = datetime.now(timezone.utc).date().isoformat()
    newsy = _ws_is_newsy(query)

    providers = (
        ("tavily", _ws_tavily),
        ("brave", _ws_brave),
        ("serper", _ws_serper),
        ("searxng", _ws_searxng),
        ("duckduckgo", _ws_duckduckgo),
    )
    try:
        import httpx
    except Exception as e:  # pragma: no cover
        logger.warning("web_search: httpx unavailable: %s", e)
        return "LIVE_DATA_UNAVAILABLE: جستجوی وب فعلاً در دسترس نیست؛ اطلاعات قدیمی را جایگزین نکن."

    last_error = None
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        for name, fn in providers:
            try:
                results = await fn(client, query, max_results, newsy)
            except Exception as e:
                last_error = e
                logger.warning("web_search provider %s failed: %s", name, e)
                continue
            if results:
                return (
                    f"LIVE_WEB_RESULTS (provider={name}, searched {date_tag} UTC) برای «{query}»:\n\n"
                    + "\n\n".join(results)
                    + "\n\nقانون پاسخ: فقط از همین نتایج استفاده کن، تاریخ/منبع را ذکر کن، "
                      "و اگر نتایج کافی یا مرتبط نیستند صریحاً بگو."
                )
    if last_error is not None:
        logger.warning("web_search: all providers failed, last error: %s", last_error)
        return "LIVE_DATA_UNAVAILABLE: جستجوی وب فعلاً در دسترس نیست؛ اطلاعات قدیمی را جایگزین نکن."
    return f"LIVE_DATA_UNAVAILABLE: برای «{query}» نتیجه قابل اتکایی پیدا نشد."

# ===== end merged part =====

# ── یادآوری زبان طبیعی ─────────────────────────────────────────────────────

# ===== merged from bot/services/ai_extras_parts/part_012_parse_natural_reminder.py =====
import re
from datetime import datetime, timedelta
from typing import Optional
from typing import Tuple

# Auto-split part 12: parse_natural_reminder
def parse_natural_reminder(text: str) -> Optional[Tuple[str, datetime, str, int]]:
    """Parse common Persian natural-language reminders.

    Returns: (body, when, repeat_type, repeat_every).
    Supports Persian/Arabic digits and one-time/daily/weekly/monthly/minute/hour repeats.
    """
    t = (text or "").strip()
    if not t:
        return None

    digit_map = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    t = t.translate(digit_map)
    normalized = t.replace("‌", " ")

    # عبارت‌های طبیعی مثل «بیدارم کن» هم درخواست یادآوری هستند.
    # اما صرفِ وجود «فردا/ساعت...» نباید پیام عادی را Reminder کند.
    reminder_hint = re.search(
        r"یادآوری|یادم\s*(?:بیار|باشه|بنداز)|ریمایندر|آلارم|خبرم\s*کن|پیام\s*بده|یاد\s*بده|بیدارم\s*کن|منو\s*بیدار\s*کن|یادم\s*بنداز",
        normalized, re.I,
    )
    # مهم: صرفِ وجود زمان («فردا»، «ساعت ۹»، ...) به معنی درخواست یادآوری نیست.
    # این شرط جلوی تبدیل درخواست‌هایی مثل «فردا هوا قم چطوره؟» به Reminder را می‌گیرد.
    # فقط وقتی وارد parser می‌شویم که کاربر صریحاً قصد یادآوری/اطلاع‌رسانی زمان‌بندی‌شده را
    # بیان کرده باشد.
    if not reminder_hint:
        return None

    now = datetime.now(TEHRAN)
    when: Optional[datetime] = None
    repeat_type = "once"
    repeat_every = 0

    if re.search(r"هر\s*روز|روزانه|daily", normalized, re.I):
        repeat_type, repeat_every = "daily", 1
    elif re.search(r"هر\s*هفته|هفتگی|weekly", normalized, re.I):
        repeat_type, repeat_every = "weekly", 1
    elif re.search(r"هر\s*ماه|ماهانه|monthly", normalized, re.I):
        repeat_type, repeat_every = "monthly", 1
    else:
        m = re.search(r"هر\s*(\d+)\s*دقیقه", normalized, re.I)
        if m:
            repeat_type, repeat_every = "every_minutes", max(1, int(m.group(1)))
        else:
            m = re.search(r"هر\s*(\d+)\s*ساعت", normalized, re.I)
            if m:
                repeat_type, repeat_every = "every_hours", max(1, int(m.group(1)))

    number_words = {
        "صفر": 0, "یک": 1, "یه": 1, "دو": 2, "سه": 3, "چهار": 4,
        "پنج": 5, "شش": 6, "شیش": 6, "هفت": 7, "هشت": 8, "نه": 9,
        "ده": 10, "یازده": 11, "دوازده": 12, "سیزده": 13, "چهارده": 14,
        "پانزده": 15, "شانزده": 16, "هفده": 17, "هجده": 18, "نوزده": 19,
        "بیست": 20, "بیست و یک": 21, "بیست و دو": 22, "بیست و سه": 23,
    }

    def _hm() -> Optional[tuple[int, int]]:
        # «ساعت 9»، «ساعت 9:30»، «ساعت نه»، «ساعت نه و نیم»
        m = re.search(
            r"ساعت\s*(\d{1,2})(?:\s*[:：]\s*(\d{1,2}))?",
            normalized, re.I,
        )
        if m:
            hour = int(m.group(1))
            minute = int(m.group(2) or 0)
        else:
            word_pattern = "|".join(re.escape(k) for k in sorted(number_words, key=len, reverse=True))
            m = re.search(r"ساعت\s*(" + word_pattern + r")(?:\s*و\s*نیم)?", normalized, re.I)
            if not m:
                return None
            hour = number_words[m.group(1)]
            minute = 30 if "و نیم" in m.group(0) else 0

        # «صبح/بامداد» را صبح نگه می‌داریم و «ظهر/شب/عصر» را به ساعت 24 ساعته تبدیل می‌کنیم.
        context = normalized[m.end():m.end() + 12]
        if re.search(r"(?:صبح|بامداد)", context, re.I):
            if hour == 12:
                hour = 0
        elif re.search(r"(?:ظهر|عصر)", context, re.I):
            if hour < 12:
                hour += 12
        elif re.search(r"شب", context, re.I):
            if hour == 12:
                hour = 0
            elif hour < 12:
                hour += 12
        return min(23, hour), min(59, minute)

    m = re.search(r"(\d+)\s*دقیقه\s*(?:دیگه|دیگر)", normalized, re.I)
    if m:
        when = now + timedelta(minutes=max(1, int(m.group(1))))

    if when is None:
        m = re.search(r"(\d+)\s*ساعت\s*(?:دیگه|دیگر)", normalized, re.I)
        if m:
            when = now + timedelta(hours=max(1, int(m.group(1))))

    if when is None and re.search(r"پس\s*فردا", normalized, re.I):
        hm = _hm() or (9, 0)
        when = (now + timedelta(days=2)).replace(hour=hm[0], minute=hm[1], second=0, microsecond=0)

    if when is None and re.search(r"فردا", normalized, re.I):
        hm = _hm() or (9, 0)
        when = (now + timedelta(days=1)).replace(hour=hm[0], minute=hm[1], second=0, microsecond=0)

    if when is None:
        hm = _hm()
        if hm:
            when = now.replace(hour=hm[0], minute=hm[1], second=0, microsecond=0)
            if when <= now:
                when += timedelta(days=1)

    if when is None and repeat_type == "every_minutes":
        when = now + timedelta(minutes=repeat_every)
    elif when is None and repeat_type == "every_hours":
        when = now + timedelta(hours=repeat_every)
    elif when is None and repeat_type != "once":
        when = now + timedelta(minutes=1)

    if when is None:
        return None

    body = normalized
    body = re.sub(r"یادآوری(?:\s*کن)?|یادم\s*(?:بیار|باشه|بنداز)|ریمایندر|آلارم|خبرم\s*کن|یاد\s*بده|بیدارم\s*کن|منو\s*بیدار\s*کن", "", body, flags=re.I)
    body = re.sub(
        r"(?:\d+\s*دقیقه\s*(?:دیگه|دیگر)|\d+\s*ساعت\s*(?:دیگه|دیگر)|فردا|پس\s*فردا|امروز|ساعت\s*(?:\d{1,2}(?:\s*[:：]\s*\d{1,2})?|یک|یه|دو|سه|چهار|پنج|شش|شیش|هفت|هشت|نه|ده|یازده|دوازده|سیزده|چهارده|پانزده|شانزده|هفده|هجده|نوزده|بیست)(?:\s*و\s*نیم)?|(?:صبح|بامداد|ظهر|عصر|شب)|هر\s*روز|روزانه|هر\s*هفته|هفتگی|هر\s*ماه|ماهانه|هر\s*\d+\s*دقیقه|هر\s*\d+\s*ساعت|daily|weekly|monthly)",
        "", body, flags=re.I,
    )
    body = re.sub(r"\s+", " ", body).strip(" :،,-") or "یادآوری"
    return body[:200], when, repeat_type, repeat_every

# ===== end merged part =====

# ── OCR فیش (پرامپت تقویت‌شده) ─────────────────────────────────────────────

RECEIPT_OCR_PROMPT = (
    "این تصویر احتمالاً فیش، رسید، فاکتور یا کارت است. "
    "همه متن را با دقت OCR کن و ساخت‌یافته به فارسی برگردان:\n"
    "• فروشنده / فروشگاه\n"
    "• تاریخ و ساعت\n"
    "• اقلام (نام + تعداد + قیمت)\n"
    "• جمع کل / مالیات / تخفیف\n"
    "• شماره پیگیری / مرجع\n"
    "• هر مبلغ یا شماره مهم دیگر\n"
    "اگر خوانا نبود بگو کدام بخش مبهم است. اعداد را دقیق بنویس."
)

# ===== merged from bot/services/ai_extras_parts/part_013_enhance_ocr_prompt.py =====
# Auto-split part 13: enhance_ocr_prompt
def enhance_ocr_prompt(user_prompt: str, has_image: bool) -> str:
    if not has_image:
        return user_prompt
    base = (user_prompt or "").strip()
    if re.search(r"فیش|رسید|فاکتور|OCR|او\s*سی\s*آر|کارت\s*ملی|کارت\s*بانک", base, re.I):
        return RECEIPT_OCR_PROMPT + ("\n\nدرخواست کاربر: " + base if base else "")
    if not base:
        return (
            "تصویر را کامل تحلیل کن. اگر فیش/رسید/متن دارد، متن را دقیق بخوان و "
            "مبالغ و تاریخ را جداگانه لیست کن."
        )
    return base

# ===== end merged part =====

# ── کیبورد اینلاین زیر جواب AI ───────────────────────────────────────────────

# ===== merged from bot/services/ai_extras_parts/part_014_get_ai_result_keyboard.py =====
# Auto-split part 14: get_ai_result_keyboard
def get_ai_result_keyboard(user_id: int, answer_id: str = "", *, offer_continue: bool = False):
    """
    کیبورد زیر جواب AI.
    اگر offer_continue=True یا پاسخ بلند باشد، دکمه «ادامه پاسخ» اضافه می‌شود.
    """
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    rows = []
    aid = answer_id or get_last_answer_id(user_id) or ""
    last = get_last_answer(user_id) or ""
    should_continue = offer_continue or (len(last) >= 1800)
    if should_continue and aid:
        rows.append([
            InlineKeyboardButton("▶️ ادامه پاسخ", callback_data=f"ai_continue:{aid}")
        ])
    # مدل و حافظه از get_ai_keyboard جدا هستند؛ اینجا فقط ادامه
    if not rows:
        return None
    return InlineKeyboardMarkup(rows)

# ===== end merged part =====

# ===== merged from bot/services/ai_extras_parts/part_015_build_continue_prompt.py =====
from typing import Optional

# Auto-split part 15: build_continue_prompt
def build_continue_prompt(user_id: int, answer_id: str = "") -> Optional[str]:
    """ساخت پرامپت ادامه برای AI بدون تکرار بخش قبلی."""
    prev = None
    prompt = None
    if answer_id:
        prev = get_stored_answer(answer_id, user_id)
        prompt = get_stored_prompt(answer_id, user_id)
    if not prev:
        prev = get_last_answer(user_id)
    if not prompt:
        prompt = get_last_prompt(user_id)
    if not prev:
        return None
    tail = prev[-900:] if len(prev) > 900 else prev
    base = (
        "ادامه بده دقیقاً از جایی که پاسخ قبلی قطع شد. "
        "هیچ بخشی از متن قبلی را تکرار نکن. مستقیم ادامه بده.\n\n"
        f"--- انتهای پاسخ قبلی ---\n{tail}\n--- ادامه از اینجا ---"
    )
    if prompt:
        return f"موضوع اصلی کاربر: {prompt}\n\n{base}"
    return base

# ===== end merged part =====
