"""جمله انگیزشی هوشمند

- دسته + ساعت روز + ضدتکرار کاربر
- API: ZenQuotes (انگلیسی) → ترجمه فارسی
- fallback: لیست محلی فارسی
"""

from __future__ import annotations

import random
import re
from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime
from typing import Optional

import httpx

try:
    from bot.logger import logger
except Exception:  # pragma: no cover
    class _L:
        def debug(self, *a, **k): pass
        def error(self, *a, **k): pass
    logger = _L()

# ─── جملات محلی (دسته‌بندی) ─────────────────────────────────────────
MOTIVATION_BY_CAT: dict[str, list[str]] = {
    "امید": [
        "🌈 رنگین‌کمان پس از باران می‌آید. صبر کن، زیبایی در راه است.",
        "🌅 هر طلوع، فرصتی تازه برای شروع دوباره است. امروز را غنیمت شمار.",
        "🌸 بهار منتظر کسی نمی‌ماند. خودت بهار زندگی‌ات باش.",
        "🌄 افق همیشه روشن است، حتی اگر هنوز آن را نبینی. به روشنایی ایمان داشته باش.",
        "🌌 شب با تمام تاریکی‌اش، ستاره‌ها را به دنیا می‌آورد. از دل تاریکی نور بساز.",
        "🍀 شانس مثل برگ چهاربرگ است؛ باید دقیق نگاه کنی تا پیدایش کنی.",
        "🌸 شکوفه‌ها نماد امیدند. امید را در دلت زنده نگه دار.",
        "🌅 هر روز فرصت تازه‌ای است. از آن غافل مشو.",
        "🌄 طلوع خورشید، هر روز معجزه‌ای کوچک است. معجزه‌های کوچک را ببین.",
        "🌌 شب پر از ستاره است اگر چشم‌هایت را باز کنی. چشم‌هایت را باز کن.",
    ],
    "تلاش": [
        "🌊 موج‌ها هرگز از تلاش برای رسیدن به ساحل دست نمی‌کشند. تو هم دست نکش.",
        "🌊 موج‌ها به ساحل می‌رسند چون ادامه می‌دهند. ادامه بده.",
        "🌿 ریشه‌های عمیق، درخت را در برابر طوفان استوار نگه می‌دارند. ریشه‌هایت را محکم کن.",
        "🌄 کوه‌ها ساکت‌اند، اما استواری‌شان زبانزد است. محکم باش، بی‌صدا.",
        "🌿 درختان کهن، طوفان‌های بسیاری دیده‌اند و هنوز ایستاده‌اند. تو هم می‌ایستی.",
        "🌿 درختان خم می‌شوند اما نمی‌شکنند. خم شو، اما نشکن.",
        "🌺 گلی که در میان خارها می‌روید، مقاوم‌ترین است. مقاوم باش.",
        "🌟 ستاره‌ها میلیون‌ها سال است که می‌درخشند. پایدار باش.",
        "🍃 باد می‌وزد تا چیزهای سبک را ببرد. سنگین و ریشه‌دار باش.",
        "🌅 خورشید غروب می‌کند اما هرگز تمام نمی‌شود. تمام نشو.",
    ],
    "آرامش": [
        "🌙 حتی در تاریک‌ترین شب‌ها، ماه راه را نشان می‌دهد. تو هم راهت را خواهی یافت.",
        "🍃 باد پیام‌های ناگفته‌ی جهان را با خود می‌برد. به صدای دلت گوش بسپار.",
        "🌙 شب با سکوتش آرامش می‌بخشد. به خودت آرامش بده.",
        "🌙 مهتاب آرام است اما جهان را تغییر می‌دهد. آرام اما تأثیرگذار باش.",
        "🌙 مهتاب در دل شب مهربانی می‌بارد. مهربان باش.",
        "🌌 کهکشان‌ها در سکوت می‌چرخند، اما عظمتشان را همه می‌بینند. سکوتت را قدرتمند کن.",
        "❄️ برف، زمستان را زیبا می‌کند. تو هم سختی‌ها را به زیبایی تبدیل کن.",
        "🌊 دریا عمیق است، اما هر قطره‌اش ارزشمند. تو هم عمیقی و ارزشمند.",
        "🌙 ماه هر شب شکلش را عوض می‌کند، اما همیشه زیباست. تو هم در تغییر زیبا باش.",
        "🌌 شب پر از رمز و راز است. رمزهای درونت را کشف کن.",
    ],
    "رشد": [
        "🌸 گل‌ها پیش از شکفتن، باران‌های بسیاری را تحمل کرده‌اند. صبور باش، نوبت تو هم می‌رسد.",
        "🌺 زیباترین گل‌ها در سخت‌ترین خاک‌ها می‌رویند. تو هم می‌توانی.",
        "🌟 هر ستاره نوری منحصربه‌فرد دارد. نور خودت را پیدا کن و بدرخش.",
        "🍃 برگ‌ها حتی هنگام افتادن می‌رقصند. در مسیر زندگیت هم زیبایی بیافرین.",
        "🌿 هر درخت از یک دانه آغاز می‌شود. از همین حالا شروع کن.",
        "🌟 هر ستاره جایگاه خودش را دارد. جایگاه خودت را پیدا کن.",
        "🌟 هر ستاره مسیری دارد. مسیر خودت را پیدا کن و برو.",
        "🍃 هر برگ داستانی از زندگی دارد. از هر مرحله درس بگیر.",
        "🌸 شکوفه‌ها بعد از خواب زمستانی بیدار می‌شوند. بیدار شو.",
        "🌟 ستاره‌ها راهنما هستند. خودت راهنمای مسیرت باش.",
    ],
    "درخشش": [
        "☀️ خورشید هر روز بی‌چشم‌داشت می‌درخشد. تو هم بدرخش، بی‌توقع.",
        "🌄 خورشید بی‌ادعا می‌درخشد. تو هم بی‌ادعا بدرخش.",
        "🌟 ستاره‌ها در تاریکی می‌درخشند، نه در روشنایی روز. درختی باش که در سختی نور می‌دهد.",
        "🌟 ستاره‌ها تاریکی را شکست می‌دهند. تو هم تاریکی‌ها را بشکن.",
        "🌺 گل‌ها در باد نمی‌شکنند، می‌رقصند. با بادها برقص.",
        "🌿 درختان میوه می‌دهند تا دیگران بهره ببرند. مفید باش.",
        "🌊 دریا بی‌نهایت است و هر قطره‌اش یک دنیا. تو هم یک دنیایی.",
        "🌌 ستاره‌ها ما را به بی‌نهایت دعوت می‌کنند. رویاهایت را بزرگ کن.",
        "🌅 سحرگاه، پرندگان با شادی آواز می‌خوانند. شادی را در دلت بکار.",
        "🌸 بهار زندگی را جشن می‌گیرد. تو هم زندگی را جشن بگیر.",
    ],
}

motivation_messages: list[str] = [q for qs in MOTIVATION_BY_CAT.values() for q in qs]

_CAT_EMOJI = {
    "امید": "🌈",
    "تلاش": "💪",
    "آرامش": "🌿",
    "رشد": "🌱",
    "درخشش": "✨",
}

_RECENT: dict[int, list[str]] = defaultdict(list)
_RECENT_MAX = 10
last_index = -1


def _category_for_now() -> str:
    try:
        hour = datetime.now().hour
    except Exception:
        return random.choice(list(MOTIVATION_BY_CAT.keys()))
    if 5 <= hour < 11:
        pool = ["رشد", "تلاش", "امید", "درخشش"]
    elif 11 <= hour < 17:
        pool = ["تلاش", "درخشش", "رشد", "امید"]
    elif 17 <= hour < 21:
        pool = ["امید", "درخشش", "آرامش", "رشد"]
    else:
        pool = ["آرامش", "امید", "آرامش", "رشد"]
    return random.choice(pool)


def _clean(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = re.sub(r"\s+", " ", s).strip()
    return s


async def _en_to_fa(text: str, client: httpx.AsyncClient) -> Optional[str]:
    text = _clean(text)
    if len(text) < 3:
        return None
    chunk = text[:400]

    def _ok(tr: str) -> bool:
        if not tr or tr.lower() == chunk.lower():
            return False
        u = tr.upper()
        if any(x in u for x in ("INVALID", "QUERY LENGTH", "MYMEMORY WARNING", "USED ALL AVAILABLE")):
            return False
        if not re.search(r"[\u0600-\u06FF]{8,}", tr):
            return False
        return True

    # Google gtx
    try:
        r = await client.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": "en", "tl": "fa", "dt": "t", "q": chunk},
            timeout=6.0,
        )
        if r.status_code == 200:
            data = r.json()
            parts = []
            if isinstance(data, list) and data and isinstance(data[0], list):
                for row in data[0]:
                    if row and row[0]:
                        parts.append(str(row[0]))
            tr = _clean("".join(parts))
            if _ok(tr):
                return tr
    except Exception as e:
        logger.debug("motivation gtx: %s", e)

    # MyMemory
    try:
        r = await client.get(
            "https://api.mymemory.translated.net/get",
            params={"q": chunk, "langpair": "en|fa"},
            timeout=6.0,
        )
        if r.status_code == 200:
            tr = _clean(((r.json().get("responseData") or {}).get("translatedText") or ""))
            if _ok(tr):
                return tr
    except Exception as e:
        logger.debug("motivation mymemory: %s", e)

    return None


async def _fetch_zenquote(client: httpx.AsyncClient) -> Optional[tuple[str, str]]:
    """(متن انگلیسی، نویسنده) از ZenQuotes."""
    try:
        r = await client.get("https://zenquotes.io/api/random", timeout=8.0)
        if r.status_code != 200:
            return None
        data = r.json()
        if not isinstance(data, list) or not data:
            return None
        item = data[0] if isinstance(data[0], dict) else {}
        q = _clean(str(item.get("q") or ""))
        a = _clean(str(item.get("a") or ""))
        if len(q) < 10:
            return None
        return q, a or "ناشناس"
    except Exception as e:
        logger.debug("zenquotes: %s", e)
        return None


def _pick_local(user_id: int | None = None) -> tuple[str, str]:
    """(دسته، متن) از لیست محلی."""
    cat = _category_for_now()
    options = list(MOTIVATION_BY_CAT.get(cat) or motivation_messages)
    recent: list[str] = []
    if user_id is not None:
        recent = _RECENT.get(int(user_id), [])
        filtered = [q for q in options if q not in recent]
        if filtered:
            options = filtered
        else:
            all_opts = [q for q in motivation_messages if q not in recent]
            if all_opts:
                options = all_opts
                cat = next((k for k, vs in MOTIVATION_BY_CAT.items() if options[0] in vs), cat)
    choice = random.choice(options or motivation_messages)
    if user_id is not None:
        uid = int(user_id)
        lst = _RECENT[uid]
        lst.append(choice)
        if len(lst) > _RECENT_MAX:
            _RECENT[uid] = lst[-_RECENT_MAX:]
    return cat, choice


def get_motivation(
    messages: Sequence[str] | None = None,
    user_id: int | None = None,
    *,
    smart: bool = True,
) -> str:
    """سازگاری همزمان — فقط محلی (بدون await)."""
    global last_index
    if messages is not None:
        pool = list(messages)
        if not pool:
            return ""
        if len(pool) == 1:
            return pool[0]
        index = random.randint(0, len(pool) - 1)
        while index == last_index and len(pool) > 1:
            index = random.randint(0, len(pool) - 1)
        last_index = index
        return pool[index]

    if not smart:
        pool = motivation_messages
        index = random.randint(0, len(pool) - 1)
        while index == last_index and len(pool) > 1:
            index = random.randint(0, len(pool) - 1)
        last_index = index
        return pool[index]

    _, choice = _pick_local(user_id)
    return choice


async def get_motivation_async(user_id: int | None = None) -> str:
    """جمله انگیزشی: API + ترجمه، در غیر این صورت محلی."""
    quote_fa = None
    author = None
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            got = await _fetch_zenquote(client)
            if got:
                eng, author = got
                quote_fa = await _en_to_fa(eng, client)
    except Exception as e:
        logger.error("motivation api: %s", e)

    if quote_fa:
        # ثبت در recent تا با محلی قاطی نشود
        if user_id is not None:
            uid = int(user_id)
            lst = _RECENT[uid]
            lst.append(quote_fa)
            if len(lst) > _RECENT_MAX:
                _RECENT[uid] = lst[-_RECENT_MAX:]
        cat = _category_for_now()
        emoji = _CAT_EMOJI.get(cat, "💖")
        lines = [
            "💖 **جمله انگیزشی**",
            f"{emoji} حال‌وهوا: **{cat}**",
            "",
            quote_fa,
        ]
        if author:
            lines.append(f"— {author}")
        return "\n".join(lines)

    # fallback محلی
    return get_motivation_rich(user_id)


def get_motivation_rich(user_id: int | None = None) -> str:
    """خروجی کامل محلی با عنوان دسته."""
    cat, choice = _pick_local(user_id)
    emoji = _CAT_EMOJI.get(cat, "💖")
    return (
        f"💖 **جمله انگیزشی**\n"
        f"{emoji} حال‌وهوا: **{cat}**\n\n"
        f"{choice}"
    )
