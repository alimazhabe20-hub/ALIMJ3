"""جمله انگیزشی — فقط نثر (بدون کتاب شعر)

منبع: کتاب‌های نثر، فلسفه، خودیاری، متون کوتاه غیرشعری + API
خروجی خلوت.
"""

from __future__ import annotations

import random
import re
import time
from collections import defaultdict
from collections.abc import Sequence
from typing import Optional

import httpx

try:
    from bot.logger import logger
except Exception:  # pragma: no cover
    class _L:
        def debug(self, *a, **k): pass
        def error(self, *a, **k): pass
    logger = _L()

# فقط نثر — بدون دیوان / مثنوی / شاهنامه / رباعیات / گلستانِ منظوم‌گونه
QUOTES: list[tuple[str, str, str]] = [
    # —— رواقی ——
    ("مانع راهت نیست؛ خودِ راه است.", "مارکوس اورلیوس", "تفکرات"),
    ("کار را چنان انجام بده که انگار آخرین کارت است.", "مارکوس اورلیوس", "تفکرات"),
    ("صبح را با این اندیشه آغاز کن که امروز سختی می‌بینی و آرام بمان.", "مارکوس اورلیوس", "تفکرات"),
    ("اگر چیزی بیرون از اختیار توست، نگذار آرامش تو را بگیرد.", "مارکوس اورلیوس", "تفکرات"),
    ("کم بخواه، تا کمتر رنج بکشی.", "مارکوس اورلیوس", "تفکرات"),
    ("بهترین انتقام این است که مثل آن‌ها نباشی.", "مارکوس اورلیوس", "تفکرات"),
    ("هر لحظه را چنان زندگی کن که انگار آخرین لحظه است.", "مارکوس اورلیوس", "تفکرات"),
    ("درونت را ساده و آرام نگه دار.", "مارکوس اورلیوس", "تفکرات"),
    ("ما بیشتر از رنج واقعی، از رنج خیالی رنج می‌بریم.", "سنکا", "نامه‌هایی به لوسیلیوس"),
    ("وقت گران‌بهاترین سرمایه است.", "سنکا", "دربارهٔ کوتاهی عمر"),
    ("تا وقتی زنده‌ای یاد بگیر چگونه زندگی کنی.", "سنکا", "نامه‌هایی به لوسیلیوس"),
    ("ثروت در داشتن چیزها نیست؛ در بی‌نیازی از آن‌هاست.", "سنکا", "نامه‌هایی به لوسیلیوس"),
    ("خشم یک سم کوتاه است که اول خودت را می‌سوزاند.", "سنکا", "دربارهٔ خشم"),
    ("اگر می‌خواهی انسان آرامی باشی، کمتر بخواه.", "سنکا", "نامه‌هایی به لوسیلیوس"),
    ("این رویدادها نیستند که می‌آزارند؛ داوری ما دربارهٔ آن‌هاست.", "اپیکتتوس", "رساله"),
    ("تمرکز روی آنچه می‌توانی کنترل کنی.", "اپیکتتوس", "رساله"),
    ("آزادی در این است که بخواهی آنچه رخ می‌دهد رخ دهد.", "اپیکتتوس", "گفتارها"),
    ("هیچ‌کس نمی‌تواند بدون رضایت تو آرامش تو را بگیرد.", "اپیکتتوس", "رساله"),
    ("اول بگو کیستی؛ بعد مطابق همان زندگی کن.", "اپیکتتوس", "گفتارها"),
    ("مشکل را دور نینداز؛ از آن برای قوی‌تر شدن استفاده کن.", "اپیکتتوس", "گفتارها"),
    # —— عرفانی (نثر / آموزه — نه دیوان شعر) ——
    ("دل را از غیر خدا خالی کن تا از نور پر شود.", "مولانا", "فیه ما فیه"),
    ("تو همانی که می‌جویی؛ بیرون از خودت به دنبال خودت نرو.", "مولانا", "فیه ما فیه"),
    ("تا از خودت نمیری، به حقیقت زنده نمی‌شوی.", "مولانا", "فیه ما فیه"),
    ("عشق، پرده‌ها را کنار می‌زند.", "مولانا", "فیه ما فیه"),
    ("هرچه در درون می‌کاری، در بیرون می‌درَوی.", "مولانا", "فیه ما فیه"),
    ("آرامش وقتی می‌آید که تسلیم باشی، نه وقتی همه چیز را کنترل کنی.", "آموزه‌های عرفانی", "حکمت عملی"),
    ("سکوت، زبان خداست؛ بقیه ترجمه‌اند.", "آموزه‌های عرفانی", "حکمت عملی"),
    ("دل شکسته، نزدیک‌ترین جا به رحمت است.", "آموزه‌های عرفانی", "حکمت عملی"),
    ("تا تهی نشوی، پر نمی‌شوی.", "آموزه‌های عرفانی", "حکمت عملی"),
    ("آنچه می‌جویی در خود توست.", "آموزه‌های عرفانی", "حکمت عملی"),
    ("نور وقتی می‌آید که تاریکی را انکار نکنی.", "آموزه‌های عرفانی", "حکمت عملی"),
    ("با نفس خودت مهربان باش؛ راه از همین‌جا شروع می‌شود.", "آموزه‌های عرفانی", "حکمت عملی"),
    ("یاد خدا آرامش دل است.", "قرآن کریم", "سوره رعد"),
    ("با هر سختی آسانی است.", "قرآن کریم", "سوره انشراح"),
    ("خدا با صابران است.", "قرآن کریم", "سوره بقره"),
    ("ارزش هر کس به همت اوست.", "امام علی (ع)", "نهج‌البلاغه"),
    ("دانش گمشدهٔ مؤمن است.", "امام علی (ع)", "نهج‌البلاغه"),
    ("نفس خود را میزان میان خود و دیگران قرار ده.", "امام علی (ع)", "نهج‌البلاغه"),
    ("قلب‌ها با مدارا آرام می‌گیرند، نه با خشونت.", "امام علی (ع)", "نهج‌البلاغه"),
    ("بهترین ذکر، ذکر خدا در خلوت دل است.", "آموزه‌های اخلاقی", "حکمت عملی"),
    # —— نثر خودیاری و معنا ——
    ("بین محرک و پاسخ فضایی هست؛ در آن فضا آزادی ماست.", "ویکتور فرانکل", "انسان در جستجوی معنا"),
    ("کسی که چرایی دارد، با هر چگونگی می‌سازد.", "ویکتور فرانکل", "انسان در جستجوی معنا"),
    ("رنج وقتی معنا داشته باشد، دیگر رنج محض نیست.", "ویکتور فرانکل", "انسان در جستجوی معنا"),
    ("عادت‌های کوچک، نتایج بزرگ می‌سازند.", "جیمز کلیر", "عادات اتمی"),
    ("محیطت را طوری بساز که کار درست آسان شود.", "جیمز کلیر", "عادات اتمی"),
    ("هر روز یک درصد بهتر شو.", "جیمز کلیر", "عادات اتمی"),
    ("کمتر داشته باش تا بیشتر زندگی کنی.", "هنری دیوید ثورو", "والدن"),
    ("ساده زندگی کن تا ذهن آزاد بماند.", "هنری دیوید ثورو", "والدن"),
    ("باش تغییری که می‌خواهی در جهان ببینی.", "مهاتما گاندی", "آثار و نامه‌ها"),
    ("در میان تاریکی، نور باش.", "مهاتما گاندی", "نامه‌ها"),
    ("آموزش قوی‌ترین سلاح برای تغییر جهان است.", "نلسون ماندلا", "راه طولانی آزادی"),
    ("بزرگ‌ترین افتخار این نیست که هرگز نیفتی؛ این است که هر بار برخیزی.", "کنفوسیوس", "مکالمات"),
    ("زندگی مثل دوچرخه‌سواری است؛ برای تعادل باید حرکت کنی.", "آلبرت اینشتین", "نامه‌ها"),
    ("سعی نکن فقط موفق باشی؛ سعی کن انسان ارزشمندی باشی.", "آلبرت اینشتین", "یادداشت‌ها"),
    ("زمان محدود است؛ زندگیِ کس دیگری را زندگی نکن.", "استیو جابز", "سخنرانی استنفورد"),
    ("تنها راه انجام کار بزرگ، دوست داشتن آن کار است.", "استیو جابز", "سخنرانی استنفورد"),
    ("موفقیت نهایی نیست؛ شکست مرگبار نیست؛ شجاعتِ ادامه دادن مهم است.", "وینستون چرچیل", "سخنرانی‌ها"),
    ("اگر در جهنمی، به راه رفتن ادامه بده.", "وینستون چرچیل", "نقل‌قول‌ها"),
    ("چه فکر کنی می‌توانی و چه فکر کنی نمی‌توانی، حق با توست.", "هنری فورد", "زندگی من و کارم"),
    ("شکست فرصتی است برای شروعی هوشمندتر.", "هنری فورد", "زندگی من و کارم"),
    ("یک سفر هزار فرسنگی با یک قدم آغاز می‌شود.", "لائوتسه", "تائو ته چینگ"),
    ("طبیعت عجله ندارد؛ با این حال همه چیز تمام می‌شود.", "لائوتسه", "تائو ته چینگ"),
    ("نفرت با نفرت خاموش نمی‌شود؛ با محبت خاموش می‌شود.", "بودا", "داماپادا"),
    ("سلامتی بزرگ‌ترین هدیه است؛ قناعت بزرگ‌ترین ثروت.", "بودا", "داماپادا"),
    ("ذهن همه چیز است؛ آنچه فکر می‌کنی می‌شوی.", "بودا", "آموزه‌ها"),
    ("با خودت صادق باش.", "ویلیام شکسپیر", "هملت"),
    ("خودت را بشناس.", "سقراط", "آثار افلاطون"),
    ("ما آنچه را تکرار می‌کنیم می‌شویم.", "ارسطو", "اخلاق نیکوماخوس"),
    ("آینده متعلق به کسانی است که به زیبایی رویاهایشان ایمان دارند.", "النور روزولت", "نوشته‌ها"),
    ("آرامش از کنترل همه چیز نمی‌آید؛ از پذیرش می‌آید.", "حکمت رواقی", "متون رواقی"),
    ("نفس عمیق بکش؛ خیلی از طوفان‌ها فقط در ذهن‌اند.", "حکمت آرامش", "جملات الهام‌بخش"),
    ("با خودت مهربان باش.", "حکمت آرامش", "جملات الهام‌بخش"),
    ("امروز لازم نیست همه چیز را حل کنی.", "حکمت آرامش", "جملات الهام‌بخش"),
    ("پیشرفتِ کند هنوز پیشرفت است.", "حکمت انگیزشی", "جملات الهام‌بخش"),
    ("یک قدم کوچک امروز، راه فردا را باز می‌کند.", "حکمت انگیزشی", "جملات الهام‌بخش"),
    ("تو از آنچه فکر می‌کنی تواناتری.", "حکمت انگیزشی", "جملات الهام‌بخش"),
    ("ادامه بده؛ نتیجه مال کسانی است که می‌مانند.", "حکمت انگیزشی", "جملات الهام‌بخش"),
    ("کمتر مقایسه کن، بیشتر شکر کن.", "حکمت آرامش", "جملات الهام‌بخش"),
    ("از گذشته بیاموز، در حال زندگی کن، برای آینده امید داشته باش.", "حکمت کلاسیک", "اندرزنامه‌ها"),
]

motivation_messages = [q[0] for q in QUOTES]
last_index = -1
_RECENT: dict[int, list[str]] = defaultdict(list)
_RECENT_MAX = 25
_API_POOL: list[tuple[str, str, str]] = []
_API_POOL_TS = 0.0
_API_TTL = 1800

# رد کردن کتاب‌های شعر در API
_POETRY_BOOK = re.compile(
    r"poem|poetry|diwan|divan|sonnet|verse|مثنوی|دیوان|رباعی|غزل|شاهنامه|اشعار|شعر",
    re.I,
)
_BAD = re.compile(r"\b(die|suicide|kill yourself|wish to die)\b", re.I)


def _clean(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = re.sub(r"\s+", " ", s).strip().strip("“”\"'«»")
    return s


def _ok(q: str, book: str = "") -> bool:
    q = _clean(q)
    if len(q) < 12 or len(q) > 220:
        return False
    if _BAD.search(q):
        return False
    if book and _POETRY_BOOK.search(book):
        return False
    return q.count(" ") >= 2


def _remember(uid: int | None, *items: str) -> None:
    if uid is None:
        return
    lst = _RECENT[int(uid)]
    for x in items:
        if x:
            lst.append(x)
    if len(lst) > _RECENT_MAX:
        _RECENT[int(uid)] = lst[-_RECENT_MAX:]


def _pick_local(user_id: int | None) -> tuple[str, str, str]:
    recent = set(_RECENT.get(int(user_id), [])) if user_id is not None else set()
    opts = [x for x in QUOTES if x[0] not in recent]
    if not opts:
        opts = list(QUOTES)
    t, a, b = random.choice(opts)
    _remember(user_id, t)
    return t, a, b


def _format(text: str, author: str, book: str) -> str:
    lines = ["💖 **جمله انگیزشی**", "", f"«{text}»", f"— {author}"]
    if book:
        lines.append(f"📖 {book}")
    return "\n".join(lines)


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
        i = random.randint(0, len(pool) - 1)
        if len(pool) > 1:
            while i == last_index:
                i = random.randint(0, len(pool) - 1)
        last_index = i
        return pool[i]
    return _format(*_pick_local(user_id))


def get_motivation_rich(user_id: int | None = None) -> str:
    return _format(*_pick_local(user_id))


async def _en_to_fa(text: str, client: httpx.AsyncClient) -> Optional[str]:
    chunk = _clean(text)[:350]
    if len(chunk) < 8:
        return None

    def good(tr: str) -> bool:
        if not tr or tr.lower() == chunk.lower():
            return False
        if "MYMEMORY WARNING" in tr.upper():
            return False
        return len(re.findall(r"[\u0600-\u06FF]", tr)) >= 6

    try:
        r = await client.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": "en", "tl": "fa", "dt": "t", "q": chunk},
            timeout=7.0,
        )
        if r.status_code == 200 and r.content:
            data = r.json()
            parts = []
            if isinstance(data, list) and data and isinstance(data[0], list):
                for row in data[0]:
                    if row and row[0]:
                        parts.append(str(row[0]))
            tr = _clean("".join(parts))
            if good(tr):
                return tr
    except Exception as e:
        logger.debug("gtx: %s", e)
    return None


async def _refresh_api(client: httpx.AsyncClient) -> None:
    global _API_POOL, _API_POOL_TS
    if _API_POOL and (time.time() - _API_POOL_TS) < _API_TTL:
        return
    pool: list[tuple[str, str, str]] = []
    for _ in range(6):
        try:
            r = await client.get("https://api.hamatim.com/quote", timeout=8.0)
            if r.status_code != 200:
                continue
            d = r.json() if r.content else {}
            q = _clean(str((d or {}).get("text") or ""))
            a = _clean(str((d or {}).get("author") or ""))
            b = _clean(str((d or {}).get("book") or ""))
            if _ok(q, b):
                pool.append((q, a or "ناشناس", b))
        except Exception:
            break
    try:
        r = await client.get("https://zenquotes.io/api/quotes", timeout=10.0)
        if r.status_code == 200:
            for item in r.json() if isinstance(r.json(), list) else []:
                if not isinstance(item, dict):
                    continue
                q = _clean(str(item.get("q") or ""))
                a = _clean(str(item.get("a") or ""))
                if _ok(q):
                    pool.append((q, a or "ناشناس", ""))
    except Exception as e:
        logger.debug("zen: %s", e)
    if pool:
        _API_POOL = pool
        _API_POOL_TS = time.time()


async def get_motivation_async(user_id: int | None = None) -> str:
    if random.random() < 0.6:
        return get_motivation_rich(user_id)
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            await _refresh_api(client)
            recent = set(_RECENT.get(int(user_id), [])) if user_id is not None else set()
            opts = [x for x in _API_POOL if x[0] not in recent] or list(_API_POOL)
            if not opts:
                return get_motivation_rich(user_id)
            eng, author, book = random.choice(opts)
            body = eng
            if not re.search(r"[\u0600-\u06FF]", eng):
                fa = await _en_to_fa(eng, client)
                if fa:
                    body = fa
            _remember(user_id, body, eng)
            return _format(body, author, book)
    except Exception as e:
        logger.error("motivation: %s", e)
        return get_motivation_rich(user_id)
