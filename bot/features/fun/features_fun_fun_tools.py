"""سرگرمی — فال حافظ، جوک، دانستنی، چالش"""
import random
import re
import httpx
from bot.logger import logger

# ===== merged from bot/features/fun/fun_tools_parts/features_fun_fun_tools_parts_part_001_pn.py =====
# Auto-split part 1: pn
def pn(n):
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))

# ===== end merged part =====

# ——— فال حافظ (شبیه hafez.taktemp.com) ———
HAFEZ_OPENING = (
    "ای حافظ شیرازی! تو محرم هر رازی!\n"
    "تو را به خدا و به شاخ نباتت قسم می‌دهم "
    "که هر چه صلاح و مصلحت می‌بینی برایم آشکار و آرزوی مرا برآورده سازی."
)

HAFEZ_LOCAL = [
    (
        "غزل شمارهٔ ۱",
        "الا یا ایها الساقی ادر کأساً و ناولها\nکه عشق آسان نمود اول ولی افتاد مشکل‌ها\n"
        "به بوی نافه‌ای کآخر صبا زان طره بگشاید\nز تاب جعد مشکینش چه خون افتاد در دل‌ها",
        "صبر و توکل؛ عشق در آغاز آسان می‌نماید اما راهش پر از آزمون است. با ایمان پیش برو.",
    ),
    (
        "غزل شمارهٔ ۳",
        "اگر آن ترک شیرازی به دست آرد دل ما را\nبه خال هندویش بخشم سمرقند و بخارا را\n"
        "بده ساقی می باقی که در جنت نخواهی یافت\nکنار آب رکن‌آباد و گلگشت مصلا را",
        "عشق و دلدادگی در راه است. سخاوت و بخشش نیتت را به خیر می‌رساند.",
    ),
    (
        "غزل شمارهٔ ۲۲",
        "دوش وقت سحر از غصه نجاتم دادند\nواندر آن ظلمت شب آب حیاتم دادند\n"
        "بی‌خود از شعشعه پرتو ذاتم کردند\nباده از جام تجلی صفاتم دادند",
        "گشایش نزدیک است. از تاریکی عبور می‌کنی و نور به تو می‌رسد؛ ناامید نشو.",
    ),
    (
        "غزل شمارهٔ ۲۵۷",
        "یوسف گم‌گشته باز آید به کنعان غم مخور\nکلبهٔ احزان شود روزی گلستان غم مخور\n"
        "ای دل غمدیده حالت به شود دلبد مکن\nوین سر شوریده باز آید به سامان غم مخور",
        "صبر کن؛ آنچه از دست رفته بازمی‌گردد و غم جای خود را به شادی می‌دهد.",
    ),
]

# ===== merged from bot/features/fun/fun_tools_parts/part_002__format_verses.py =====
# Auto-split part 2: _format_verses
def _format_verses(verses: list) -> str:
    """چیدمان ابیات مثل سایت‌های فال حافظ (مصراع‌ها جفت‌جفت)"""
    lines = []
    couplet = []
    for v in verses:
        if not isinstance(v, dict):
            continue
        text = (v.get("text") or "").strip()
        if not text:
            continue
        couplet.append(text)
        # versePosition 0 = مصراع اول، 1 = مصراع دوم
        pos = v.get("versePosition")
        if pos == 1 or len(couplet) >= 2:
            lines.append("\n".join(couplet))
            couplet = []
    if couplet:
        lines.append("\n".join(couplet))
    return "\n\n".join(lines)

# ===== end merged part =====

# ===== merged from bot/features/fun/fun_tools_parts/part_003_hafez_fal.py =====
# Auto-split part 3: hafez_fal
async def hafez_fal(user_id: int = 0) -> str:
    """
    فال حافظ — شبیه hafez.taktemp.com
    نیت → دعا → غزل کامل → تفسیر
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.get("https://api.ganjoor.net/api/ganjoor/hafez/faal")
            if r.status_code == 200:
                data = r.json() or {}
                title = data.get("title") or "غزل حافظ"
                full_title = data.get("fullTitle") or title
                verses = data.get("verses") or []
                body = _format_verses(verses) if verses else (data.get("plainText") or "").replace("\r\n", "\n\n")
                # تفسیر: خلاصه هوش‌مصنوعی گنجور
                meaning = (data.get("poemSummary") or "").strip()
                if not meaning:
                    # از coupletSummary اولین بیت
                    for v in verses:
                        if isinstance(v, dict) and v.get("coupletSummary"):
                            meaning = v["coupletSummary"]
                            break
                if meaning.startswith("هوش مصنوعی:"):
                    meaning = meaning.replace("هوش مصنوعی:", "", 1).strip()

                if body:
                    parts = [
                        "🔮 **فال حافظ**",
                        "",
                        "نیت کنید…",
                        "",
                        f"📿 {HAFEZ_OPENING}",
                        "",
                        "━━━━━━━━━━━━━━━━━━━━",
                        f"📖 **{title}**",
                        f"_{full_title}_" if full_title != title else "",
                        "",
                        body.strip(),
                        "",
                    ]
                    if meaning:
                        parts.extend([
                            "━━━━━━━━━━━━━━━━━━━━",
                            "💡 **تفسیر فال**",
                            "",
                            meaning[:900],
                            "",
                        ])
                    parts.append("🕯️ برای شادی روح حافظ، صلوات یا فاتحه‌ای نثار کنید.")
                    return "\n".join(p for p in parts if p is not None)
    except Exception as e:
        logger.error(f"hafez api: {e}")

    title, body, advice = random.choice(HAFEZ_LOCAL)
    return (
        f"🔮 **فال حافظ**\n\n"
        f"نیت کنید…\n\n"
        f"📿 {HAFEZ_OPENING}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📖 **{title}**\n\n"
        f"{body}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 **تفسیر فال**\n\n"
        f"{advice}\n\n"
        f"🕯️ برای شادی روح حافظ، صلوات یا فاتحه‌ای نثار کنید."
    )

# ===== end merged part =====

# ——— جوک‌ها از farsijokes.com (۵۵۱۶ جوک دسته‌بندی‌شده) ———
import json
from pathlib import Path

_JOKES_CACHE = None

# ===== merged from bot/features/fun/fun_tools_parts/part_004__load_jokes.py =====
# Auto-split part 4: _load_jokes
def _load_jokes():
    global _JOKES_CACHE
    if _JOKES_CACHE is not None:
        return _JOKES_CACHE
    path = Path(__file__).parent / "jokes_data.json"
    try:
        with open(path, encoding="utf-8") as f:
            _JOKES_CACHE = json.load(f)
    except Exception:
        _JOKES_CACHE = {
            "labels": {"general": "😄 عمومی"},
            "jokes": {"general": ["جوکی موجود نیست."]},
        }
    return _JOKES_CACHE

# ===== end merged part =====

# ===== merged from bot/features/fun/fun_tools_parts/part_005_get_joke_categories.py =====
# Auto-split part 5: get_joke_categories
def get_joke_categories() -> dict:
    """برگرداندن {key: label} دسته‌ها"""
    data = _load_jokes()
    return data.get("labels", {})

# ===== end merged part =====

# ===== merged from bot/features/fun/fun_tools_parts/part_006_random_joke.py =====
# Auto-split part 6: random_joke
def random_joke(category: str = None, user_id: int = None) -> str:
    """جوک تصادفی — برای هر کاربر تکراری نمی‌فرستد"""
    import hashlib
    data = _load_jokes()
    jokes_map = data.get("jokes", {})
    labels = data.get("labels", {})

    if category and category in jokes_map and jokes_map[category]:
        pool = list(jokes_map[category])
        label = labels.get(category, category)
    else:
        pool = []
        for lst in jokes_map.values():
            pool.extend(lst)
        label = "تصادفی"

    if not pool:
        return "جوکی موجود نیست."

    # حذف جوک‌هایی که این کاربر قبلاً دیده
    if user_id:
        try:
            from bot.database import get_sent_joke_hashes, mark_joke_sent, reset_sent_jokes
            seen = get_sent_joke_hashes(user_id)
            fresh = [j for j in pool if hashlib.md5(j.encode("utf-8")).hexdigest() not in seen]
            if not fresh:
                # همه را دیده — از نو شروع کن
                reset_sent_jokes(user_id)
                fresh = pool
            text = random.choice(fresh)
            mark_joke_sent(user_id, hashlib.md5(text.encode("utf-8")).hexdigest())
        except Exception:
            text = random.choice(pool)
    else:
        text = random.choice(pool)

    return f"😂 **جوک ({label})**\n\n{text}"

# ===== end merged part =====

# سازگاری با کد قبلی
JOKES = []  # دیگر استفاده نمی‌شود؛ از random_joke استفاده کنید

FACTS = [
    "عسل تنها غذایی است که هرگز فاسد نمی‌شود.",
    "قلب کوسه در سرش نیست؛ نزدیک آبشش است.",
    "اثر انگشت گوریل و انسان متفاوت است اما هر دو یکتاست.",
    "طول رگ‌های بدن انسان حدود ۱۰۰ هزار کیلومتر است.",
    "اختاپوس سه قلب دارد.",
    "بیشتر گرد و غبار خانه از پوست مرده انسان است.",
    "نهنگ آبی بزرگ‌ترین حیوان تاریخ زمین است.",
    "مغز انسان حدود ۲۰ وات انرژی مصرف می‌کند.",
    "در فضا اشک جاری نمی‌شود؛ به شکل حباب می‌ماند.",
    "زبان قوی‌ترین عضله نسبت به اندازه‌اش در بدن است.",
    "زرافه فقط حدود ۳۰ دقیقه در شبانه‌روز می‌خوابد.",
    "نور خورشید حدود ۸ دقیقه طول می‌کشد تا به زمین برسد.",
    "کوه اورست هر سال چند میلی‌متر رشد می‌کند.",
    "انسان تنها حیوانی است که می‌تواند آگاهانه نفس را حبس کند.",
    "خواب دیدن معمولاً در مرحله REM رخ می‌دهد.",
    "اسکلت انسان در بدو تولد حدود ۲۷۰ استخوان دارد و بعد کمتر می‌شود.",
    "بادام‌زمینی جزو آجیل‌ها نیست؛ جزو حبوبات است.",
    "چشم‌های شترمرغ از مغزش بزرگ‌ترند.",
    "در هر ثانیه خورشید میلیون‌ها تن ماده را به انرژی تبدیل می‌کند.",
    "اثر انگشت حتی در دوقلوهای همسان متفاوت است.",
    "دلفین‌ها با نام مخصوص یکدیگر را صدا می‌زنند.",
    "قلب انسان در طول عمر حدود ۲٫۵ میلیارد بار می‌تپد.",
    "یک روز در زهره طولانی‌تر از یک سال آن است.",
    "گربه‌ها نمی‌توانند طعم شیرینی را حس کنند.",
    "بیش از ۷۰ درصد سطح زمین را آب پوشانده است.",
    "سرعت عطسه می‌تواند به بیش از ۱۵۰ کیلومتر بر ساعت برسد.",
    "در قطب جنوب عملاً باران نمی‌بارد؛ بیشتر برف است.",
    "مرغ‌ها بیشتر رنگ‌ها را می‌بینند — حتی فرابنفش.",
    "استخوان ران انسان از بتن هم‌اندازه قوی‌تر است.",
    "هر انسان حدود ۰٫۲ میلی‌گرم طلا در بدن دارد.",
    "قورباغه اگر چشمانش بسته باشد نمی‌تواند بپرد.",
    "کهکشان راه شیری حدود ۱۰۰ تا ۴۰۰ میلیارد ستاره دارد.",
    "پنگوئن‌ها برای پیدا کردن جفت خود صدا را تشخیص می‌دهند.",
    "خون بدن انسان حدود ۷ تا ۸ درصد وزن اوست.",
    "مارها پلک ندارند و با پوست شفاف چشم را می‌پوشانند.",
    "در ماه تقریباً یک‌ششم گرانش زمین وجود دارد.",
    "زنبور عسل برای یک قاشق عسل از حدود ۲ میلیون گل بازدید می‌کند.",
    "مغز در خواب هم تقریباً به‌اندازه بیداری فعال است.",
    "تنها حرفی که در جدول تناوبی عناصر نیست J است.",
    "صدا در آب حدود ۴ برابر سریع‌تر از هوا حرکت می‌کند.",
]

CHALLENGES = [
    "امروز به یک نفر بدون مناسبت پیام محبت‌آمیز بده.",
    "۳۰ دقیقه بدون گوشی بمان و فقط نفس عمیق بکش.",
    "یک کار عقب‌افتاده را همین امروز تمام کن.",
    "به کسی که فراموش کردی پیام بده و احوالش را بپرس.",
    "۱۰ چیز که بابت آن‌ها شکرگزاری می‌کنی را بنویس.",
    "امروز یک عادت بد را آگاهانه متوقف کن.",
    "۱۵ دقیقه پیاده‌روی بدون هدف مشخص.",
    "به جای شکایت، یک راه‌حل پیشنهاد بده.",
    "یک صفحه کتاب بخوان — هر کتابی.",
    "قبل از خواب گوشی را یک ساعت کنار بگذار.",
    "به خودت بگو: من کافی هستم — و باور کن.",
    "یک کار خیر کوچک بدون اینکه کسی بفهمد انجام بده.",
]

# ===== merged from bot/features/fun/fun_tools_parts/part_007_joke_of_day.py =====
# Auto-split part 7: joke_of_day
async def joke_of_day(category: str = None, user_id: int = None) -> str:
    return random_joke(category, user_id=user_id)

# ===== end merged part =====


async def _translate_en_to_fa(text: str, client: httpx.AsyncClient) -> str | None:
    """ترجمه کوتاه انگلیسی → فارسی (چند سرویس رایگان)."""
    text = (text or "").strip()
    if len(text) < 3:
        return None
    chunk = text[:450]

    def _ok(tr: str) -> bool:
        if not tr or tr.lower() == chunk.lower():
            return False
        u = tr.upper()
        if any(x in u for x in ("INVALID", "QUERY LENGTH", "MYMEMORY WARNING", "USED ALL AVAILABLE")):
            return False
        # باید حداقل کمی فارسی داشته باشد
        if not re.search(r"[آ-ی]", tr):
            return False
        return True

    # ۱) Google Translate endpoint عمومی (بدون کلید)
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
            tr = "".join(parts).strip()
            if _ok(tr):
                return tr
    except Exception as e:
        logger.debug("fact gtx: %s", e)

    # ۲) MyMemory
    try:
        r = await client.get(
            "https://api.mymemory.translated.net/get",
            params={"q": chunk, "langpair": "en|fa"},
            timeout=6.0,
        )
        if r.status_code == 200:
            tr = ((r.json().get("responseData") or {}).get("translatedText") or "").strip()
            if _ok(tr):
                return tr
    except Exception as e:
        logger.debug("fact mymemory: %s", e)

    return None


async def _fetch_useless_fact(client: httpx.AsyncClient) -> str | None:
    """دانستنی تصادفی از Useless Facts API."""
    try:
        r = await client.get(
            "https://uselessfacts.jsph.pl/api/v2/facts/random",
            params={"language": "en"},
            headers={"Accept": "application/json"},
            timeout=8.0,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        text = (data.get("text") or data.get("fact") or "").strip()
        return text or None
    except Exception as e:
        logger.debug("uselessfacts: %s", e)
        return None


async def fact_of_day() -> str:
    """دانستنی روز: API خارجی + ترجمه فارسی، در صورت خطا لیست محلی."""
    fact_fa = None
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            eng = await _fetch_useless_fact(client)
            if eng:
                fact_fa = await _translate_en_to_fa(eng, client)
    except Exception as e:
        logger.error("fact_of_day api: %s", e)

    if not fact_fa:
        fact_fa = random.choice(FACTS)

    return f"🧠 **دانستنی**\n\n{fact_fa}"


# ===== end merged part =====

# ===== merged from bot/features/fun/fun_tools_parts/part_009_daily_challenge.py =====
# Auto-split part 9: daily_challenge
async def daily_challenge() -> str:
    return (
        f"💪 **چالش امروز**\n\n"
        f"{random.choice(CHALLENGES)}\n\n"
        f"✅ وقتی انجام دادی به خودت امتیاز بده!"
    )

# ===== end merged part =====
