"""جمله انگیزشی هوشمند

ترتیب:
1) کش ZenQuotes (۵۰ جمله تصادفی از API) + ترجمه
2) اگر کش خالی بود → یک random از API
3) fallback محلی فارسی (بیش از ۱۲۰ جمله)
"""

from __future__ import annotations

import random
import re
import time
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

# ─── لیست محلی گسترده ───────────────────────────────────────────
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
        "🌱 بعد از سخت‌ترین زمستان‌ها، بهار از راه می‌رسد.",
        "🕯 یک شمع کوچک هم تاریکی اتاق را می‌شکند.",
        "🚪 وقتی یک در بسته می‌شود، در دیگری باز می‌شود؛ نگاهت را عوض کن.",
        "🧭 امید قطب‌نمای کسانی است که راه را گم کرده‌اند.",
        "🎈 سبک باش؛ گاهی امید یعنی رها کردن سنگینی‌های بی‌فایده.",
        "🪞 فردایی که می‌سازی، بازتاب امید امروز توست.",
        "🌿 حتی در خاک خشک، دانه صبور سبز می‌شود.",
        "🔔 هر لحظه می‌تواند شروع تازه‌ای باشد.",
        "🪁 امید مثل بادبادک است؛ با باد مخالف هم بالاتر می‌رود.",
        "🌟 کوچک‌ترین پیشرفت هم دلیل کافی برای ادامه است.",
        "🧭 مسیر درست گاهی دیر پیدا می‌شود، اما دیر بهتر از هرگز است.",
        "🌊 بعد از هر موج سخت، ساحل آرام‌تری در راه است.",
        "🔥 خاکستر هم می‌تواند دوباره شعله شود.",
        "🌻 رو به نور بایست؛ سایه‌ها پشت سرت می‌مانند.",
        "🎯 امید بدون اقدام، فقط رویاست؛ یک قدم بردار.",
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
        "🏋️‍♂️ عضله در برابر مقاومت ساخته می‌شود؛ تو هم همین‌طور.",
        "🧱 آجر به آجر دیوار ساخته می‌شود؛ عجله نکن، بساز.",
        "⏳ پیشرفت کند، هنوز پیشرفت است.",
        "🎯 تمرکز روی یک کار بهتر از ده کار نیمه‌کاره است.",
        "🏃‍♂️ سرعت مهم نیست؛ جهت و استمرار مهم است.",
        "📚 هر روز یک صفحه بخوان؛ در یک سال کتابخانه‌ای می‌شوی.",
        "🛠️ استعداد بدون تمرین، فقط یک استعداد است.",
        "🧗 قله از قدم‌های کوچک ساخته می‌شود، نه یک پرش.",
        "💪 خستگی نشانهٔ نزدیک شدن است، نه پایان.",
        "🧩 شکست بخشی از نقشه است، نه خط پایان.",
        "🔁 دوباره شروع کن؛ حرفه‌ای‌ها هم همین کار را می‌کنند.",
        "🧠 ذهن قوی در روزهای سخت ساخته می‌شود.",
        "📌 امروز را تمام کن؛ فردا از نتیجهٔ امروز رشد می‌کند.",
        "🛡️ نظم، استعداد را شکست می‌دهد اگر استعداد بی‌نظم باشد.",
        "🚀 یک ساعت تمرکز عمیق، از یک روز شلوغ بی‌هدف بهتر است.",
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
        "🍵 یک فنجان آرامش بهتر از یک دیگ نگرانی است.",
        "🫁 نفس عمیق بکش؛ خیلی از طوفان‌ها فقط در ذهن‌اند.",
        " Quiet mind, open heart — ذهنت را آرام کن تا دلت شنیده شود.",
        "🕊 رها کردن، گاهی شجاعانه‌ترین کار است.",
        "🪴 به خودت فرصت رشد آرام بده.",
        "🧘‍♂️ امروز لازم نیست همه چیز را حل کنی.",
        "🌊 مثل رود باش؛ مانع را دور می‌زند و پیش می‌رود.",
        "🔇 گاهی سکوت، کامل‌ترین پاسخ است.",
        "🌅 عجله مال ذهن است؛ حقیقت با آرامش می‌آید.",
        "💙 با خودت مهربان باش؛ تو هم انسان هستی.",
        "📿 یک ذکر، یک نفس، یک لحظه حضور.",
        "🌤 بعد از ابر، آسمان هنوز آنجاست.",
        "🧺 بارهای اضافه را زمین بگذار.",
        "🪷 آرامش تمرین است، نه تصادف.",
        "🌙 امشب به اندازهٔ کافی بودی.",
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
        "📖 هر اشتباه، یک درس پرداخت‌شده است.",
        "🧠 نسخهٔ بهتر تو، پشت تمرین‌های کوچک پنهان است.",
        "🔍 از خودت بپرس: امروز چه چیزی یاد گرفتم؟",
        "🪴 رشد گاهی نامحسوس است، تا روزی که همه ببینند.",
        "🧭 تغییر مسیر شکست نیست؛ اصلاح قطب‌نماست.",
        "🪞 خودت را با دیروزت مقایسه کن، نه با دیگران.",
        "🎓 کنجکاوی، سوخت رشد است.",
        "🧱 محدودهٔ راحتی‌ات را یک وجب جابه‌جا کن.",
        "🗣️ بازخورد سخت، گاهی بهترین معلم است.",
        "🌱 اجازه بده نسخه‌های قدیمی‌ات بروند.",
        "📊 پیشرفت را اندازه بگیر تا ناامید نشوی.",
        "🧩 مهارت‌ها روی هم سوار می‌شوند؛ صبور باش.",
        "🧠 ذهن مثل عضله است؛ هر روز کمی سنگین‌تر تمرینش بده.",
        "🔓 ترس از شروع، معمولاً بزرگ‌تر از خود کار است.",
        "🎯 یک عادت کوچک پایدار، از یک تصمیم بزرگ فراموش‌شده بهتر است.",
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
        "✨ حضور تو می‌تواند روز کسی را عوض کند.",
        "🎤 صدایت را پنهان نکن؛ دنیا به آن نیاز دارد.",
        "🏅 موفقیت واقعی، وقتی است که خودت را پنهان نمی‌کنی.",
        "🌞 بدرخش، حتی اگر کسی تماشا نکند.",
        "🎁 استعدادت را مثل هدیه خرج کن، نه مثل راز.",
        "🚀 رویاهای بزرگ، آدم‌های معمولی را استثنایی می‌کنند.",
        "💎 تراش‌خورده می‌درخشی؛ فشار را بخشی از فرآیند بدان.",
        "👑 خودت را کوچک نکن تا دیگران راحت باشند.",
        "🔥 شوق درونت را خاموش نکن.",
        "🌈 تو ترکیب هیچ‌کس دیگری نیستی؛ یکتا باش.",
        "📸 لحظه‌هایت را زندگی کن، فقط ثبت نکن.",
        "🕊️ آزادانه فکر کن، مسئولانه عمل کن.",
        "🎯 بدرخش و راه را برای بقیه هم روشن کن.",
        "💫 انرژی‌ات مسری است؛ مثبت پخش کن.",
        "🏆 قهرمان داستان تو، خود تویی.",
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
_RECENT_MAX = 30
last_index = -1

# کش API: لیست (متن‌انگلیسی، نویسنده)
_API_POOL: list[tuple[str, str]] = []
_API_POOL_TS = 0.0
_API_POOL_TTL = 3600  # یک ساعت

_BAD_EN = re.compile(
    r"\b(die|suicide|kill yourself|hang yourself|wish to die)\b",
    re.I,
)


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
    chunk = text[:380]

    def _ok(tr: str) -> bool:
        if not tr or tr.lower() == chunk.lower():
            return False
        u = tr.upper()
        if any(x in u for x in ("INVALID", "QUERY LENGTH", "MYMEMORY WARNING", "USED ALL AVAILABLE")):
            return False
        if len(re.findall(r"[\u0600-\u06FF]", tr)) < 6:
            return False
        return True

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ALIMJ3/1.0)",
        "Accept": "application/json,text/plain,*/*",
    }

    try:
        r = await client.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": "en", "tl": "fa", "dt": "t", "q": chunk},
            headers=headers,
            timeout=8.0,
        )
        if r.status_code == 200 and r.content:
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

    try:
        r = await client.get(
            "https://api.mymemory.translated.net/get",
            params={"q": chunk, "langpair": "en|fa"},
            headers=headers,
            timeout=8.0,
        )
        if r.status_code == 200:
            tr = _clean(((r.json().get("responseData") or {}).get("translatedText") or ""))
            if _ok(tr):
                return tr
    except Exception as e:
        logger.debug("motivation mymemory: %s", e)

    try:
        from urllib.parse import quote
        for host in ("https://lingva.ml", "https://lingva.garudalinux.org"):
            try:
                r = await client.get(
                    f"{host}/api/v1/en/fa/{quote(chunk)}",
                    headers=headers,
                    timeout=8.0,
                )
                if r.status_code == 200:
                    tr = _clean(str((r.json() or {}).get("translation") or ""))
                    if _ok(tr):
                        return tr
            except Exception as e:
                logger.debug("motivation lingva %s: %s", host, e)
    except Exception:
        pass

    return None


async def _refresh_api_pool(client: httpx.AsyncClient) -> None:
    """۵۰ جمله از ZenQuotes برای تنوع بیشتر."""
    global _API_POOL, _API_POOL_TS
    now = time.time()
    if _API_POOL and (now - _API_POOL_TS) < _API_POOL_TTL:
        return
    try:
        r = await client.get(
            "https://zenquotes.io/api/quotes",
            headers={"User-Agent": "ALIMJ3/1.0", "Accept": "application/json"},
            timeout=12.0,
        )
        if r.status_code != 200:
            return
        data = r.json()
        if not isinstance(data, list):
            return
        pool: list[tuple[str, str]] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            q = _clean(str(item.get("q") or ""))
            a = _clean(str(item.get("a") or ""))
            if len(q) < 12:
                continue
            if _BAD_EN.search(q):
                continue
            pool.append((q, a or "ناشناس"))
        if pool:
            _API_POOL = pool
            _API_POOL_TS = now
            logger.debug("motivation api pool size=%s", len(pool))
    except Exception as e:
        logger.debug("motivation pool refresh: %s", e)


async def _fetch_from_pool_or_random(client: httpx.AsyncClient, user_id: int | None) -> Optional[tuple[str, str]]:
    await _refresh_api_pool(client)
    recent = _RECENT.get(int(user_id), []) if user_id is not None else []

    candidates = list(_API_POOL) if _API_POOL else []
    if candidates:
        # اولویت: چیزی که اخیراً ندیده
        fresh = [c for c in candidates if c[0] not in recent and c[0][:40] not in "".join(recent)]
        pick_from = fresh or candidates
        return random.choice(pick_from)

    # fallback: random تکی
    for _ in range(4):
        try:
            r = await client.get(
                "https://zenquotes.io/api/random",
                headers={"User-Agent": "ALIMJ3/1.0", "Accept": "application/json"},
                timeout=10.0,
            )
            if r.status_code != 200:
                continue
            data = r.json()
            if not isinstance(data, list) or not data:
                continue
            item = data[0] if isinstance(data[0], dict) else {}
            q = _clean(str(item.get("q") or ""))
            a = _clean(str(item.get("a") or ""))
            if len(q) < 12 or _BAD_EN.search(q):
                continue
            if user_id is not None and q in recent:
                continue
            return q, a or "ناشناس"
        except Exception as e:
            logger.debug("zenquotes random: %s", e)
    return None


def _pick_local(user_id: int | None = None) -> tuple[str, str]:
    cat = _category_for_now()
    options = list(MOTIVATION_BY_CAT.get(cat) or motivation_messages)
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
    _, choice = _pick_local(user_id)
    return choice


def get_motivation_rich(user_id: int | None = None) -> str:
    cat, choice = _pick_local(user_id)
    emoji = _CAT_EMOJI.get(cat, "💖")
    return (
        f"💖 **جمله انگیزشی**\n"
        f"{emoji} حال‌وهوا: **{cat}**\n"
        f"📌 منبع: محلی ({len(motivation_messages)} جمله)\n\n"
        f"{choice}"
    )


async def get_motivation_async(user_id: int | None = None) -> str:
    eng = None
    author = None
    fa = None

    try:
        async with httpx.AsyncClient(timeout=18.0, follow_redirects=True) as client:
            got = await _fetch_from_pool_or_random(client, user_id)
            if got:
                eng, author = got
                fa = await _en_to_fa(eng, client)
    except Exception as e:
        logger.error("motivation api: %s", e)

    if eng:
        body = fa if fa else eng
        if user_id is not None:
            uid = int(user_id)
            lst = _RECENT[uid]
            lst.append(body)
            lst.append(eng)
            if len(lst) > _RECENT_MAX:
                _RECENT[uid] = lst[-_RECENT_MAX:]

        cat = _category_for_now()
        emoji = _CAT_EMOJI.get(cat, "💖")
        pool_n = len(_API_POOL) if _API_POOL else 1
        lines = [
            "💖 **جمله انگیزشی**",
            f"{emoji} حال‌وهوا: **{cat}**",
            f"🌐 منبع: ZenQuotes (مخزن {pool_n}+ جمله)",
            "",
            f"«{body}»",
        ]
        if author:
            lines.append(f"— {author}")
        if not fa:
            lines.append("")
            lines.append("_(ترجمه در دسترس نبود؛ متن اصلی)_")
        return "\n".join(lines)

    return get_motivation_rich(user_id)
