"""آیه و حدیث — آیه تصادفی قرآن + حدیث شیعی معتبر (Thaqalayn)

حدیث: فقط منابع اهل‌بیت از Thaqalayn + ترجمه فارسی تمیز
- حذف سند طولانی
- محدودسازی طول
- نام کتاب/مؤلف فارسی
"""

from __future__ import annotations

import random
import re
from typing import Optional, Tuple

import httpx

from bot.logger import logger

HADITHS = [
    ("پیامبر اکرم (ص)", "بهترین شما کسی است که اخلاقش نیکوتر باشد."),
    ("پیامبر اکرم (ص)", "تبسم به روی برادر مؤمن صدقه است."),
    ("پیامبر اکرم (ص)", "کسی که به مردم رحم نکند، خدا به او رحم نمی‌کند."),
    ("پیامبر اکرم (ص)", "دست خدا با جماعت است."),
    ("پیامبر اکرم (ص)", "طلب علم بر هر مسلمانی واجب است."),
    ("پیامبر اکرم (ص)", "نگاه به والدین عبادت است."),
    ("پیامبر اکرم (ص)", "مؤمن با ایمان برادر مؤمن است."),
    ("پیامبر اکرم (ص)", "از غضب بپرهیزید که غضب ایمان را می‌سوزاند."),
    ("پیامبر اکرم (ص)", "صداقت آرامش می‌آورد و دروغ شک."),
    ("پیامبر اکرم (ص)", "هر که فریب دهد از ما نیست."),
    ("امام علی (ع)", "ارزش هر کس به اندازه همت اوست."),
    ("امام علی (ع)", "سکوت دری از درهای حکمت است."),
    ("امام علی (ع)", "کسی که خود را شناخت پروردگارش را شناخت."),
    ("امام علی (ع)", "فرصت‌ها مثل ابر می‌گذرند."),
    ("امام علی (ع)", "با مردم به نیکی رفتار کنید تا دل‌ها به شما مایل شود."),
    ("امام علی (ع)", "علم بهتر از مال است؛ علم نگهبان توست و مال را تو نگهبانی."),
    ("امام علی (ع)", "بزرگ‌ترین فقر حماقت است."),
    ("امام علی (ع)", "دوست تو همان کسی است که تو را به حق راه نماید."),
    ("امام علی (ع)", "هیچ ثروتی چون عقل و هیچ فقری چون جهل نیست."),
    ("امام علی (ع)", "صبر کلید فرج است."),
    ("امام حسن (ع)", "نیکی آن است که در نهان و آشکار یکسان باشی."),
    ("امام حسن (ع)", "نسبت به آنچه از دست دادی بی‌اعتنا باش."),
    ("امام حسین (ع)", "اگر دین ندارید، آزادمرد باشید."),
    ("امام حسین (ع)", "مرگ با عزت بهتر از زندگی با خواری است."),
    ("امام سجاد (ع)", "دوست بد، مثل آتش است که اگر نسوزاند دودش آزار می‌دهد."),
    ("امام باقر (ع)", "مؤمن برادر مؤمن است؛ به او خیانت نمی‌کند و او را خوار نمی‌سازد."),
    ("امام صادق (ع)", "مؤمن آینه مؤمن است."),
    ("امام صادق (ع)", "خوش‌اخلاقی روزی را زیاد می‌کند."),
    ("امام صادق (ع)", "نیمی از خرد مدارا کردن است."),
    ("امام صادق (ع)", "هر که برای خدا خشم خود را فرو برد، خدا دلش را از امنیت پر می‌کند."),
    ("امام کاظم (ع)", "کمک به ناتوان از بهترین صدقات است."),
    ("امام رضا (ع)", "دوست ندارم مردی را ببینم مگر آنکه در کاری از کارهای دنیا یا آخرت باشد."),
    ("امام جواد (ع)", "اعتماد به خدا بهای هر کالای گران و نردبان رسیدن به هر بلندی است."),
    ("امام هادی (ع)", "دنیا بازاری است که گروهی در آن سود و گروهی زیان می‌برند."),
    ("امام عسکری (ع)", "فروتنی نعمتی است که بر آن حسد نمی‌برند."),
    ("امام مهدی (عج)", "ما در رسیدگی و سرپرستی شما کوتاهی نمی‌کنیم و یادتان را از خاطر نمی‌بریم."),
    ("پیامبر اکرم (ص)", "دنیا مزرعه آخرت است."),
    ("پیامبر اکرم (ص)", "هر که صبح کند و به فکر امور مسلمانان نباشد مسلمان نیست."),
    ("امام علی (ع)", "مردم دشمن آن‌اند که نمی‌دانند."),
    ("امام علی (ع)", "زبان عاقل در پشت قلب اوست و قلب نادان در پشت زبانش."),
    ("امام صادق (ع)", "بر شما باد به دعا کردن؛ زیرا دعا درمان هر دردی است."),
    ("امام باقر (ع)", "چهار چیز از گنج‌های نیکی است: کتمان حاجت، کتمان صدقه، کتمان بیماری و کتمان مصیبت."),
    ("پیامبر اکرم (ص)", "پاکیزگی نیمی از ایمان است."),
    ("امام علی (ع)", "اندازه هر کس به اندازه همت او و صدق او به اندازه مروتش است."),
    ("امام صادق (ع)", "با سه کس رفاقت مکن: فاسق، بخیل و دروغگو."),
    ("پیامبر اکرم (ص)", "از نشانه‌های فهم مرد آن است که در معیشت اقتصاد کند."),
    ("امام علی (ع)", "هر که حساب خود را بکشد سود برد و هر که از آن غافل شود زیان کند."),
    ("امام رضا (ع)", "عقل هدیه‌ای الهی است."),
    ("امام حسین (ع)", "بخشنده‌ترین مردم کسی است که در هنگام تنگدستی ببخشد."),
    ("امام سجاد (ع)", "گناهان خنده را نابود می‌کنند."),
]

LOCAL_VERSES = [
    ("﴿إِنَّ مَعَ الْعُسْرِ يُسْرًا﴾", "همانا با سختی آسانی است.", "شرح", "۶"),
    ("﴿فَاذْكُرُونِي أَذْكُرْكُمْ﴾", "مرا یاد کنید تا شما را یاد کنم.", "بقره", "۱۵۲"),
    ("﴿وَمَن يَتَوَكَّلْ عَلَى اللَّهِ فَهُوَ حَسْبُهُ﴾", "هر که بر خدا توکل کند، او برایش کافی است.", "طلاق", "۳"),
    ("﴿لَا يُكَلِّفُ اللَّهُ نَفْسًا إِلَّا وُسْعَهَا﴾", "خدا کسی را جز به اندازه توانش تکلیف نمی‌کند.", "بقره", "۲۸۶"),
    ("﴿وَبَشِّرِ الصَّابِرِينَ﴾", "و صابران را بشارت ده.", "بقره", "۱۵۵"),
    ("﴿إِنَّ اللَّهَ مَعَ الصَّابِرِينَ﴾", "همانا خدا با صابران است.", "بقره", "۱۵۳"),
    ("﴿ادْعُونِي أَسْتَجِبْ لَكُمْ﴾", "مرا بخوانید تا اجابت کنم شما را.", "غافر", "۶۰"),
    ("﴿أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ﴾", "آگاه باشید که با یاد خدا دل‌ها آرام می‌گیرد.", "رعد", "۲۸"),
]

# نام کتاب (انگلیسی/آوانگاری) → فارسی
_BOOK_FA = {
    "al-kafi": "الکافی",
    "al-kāfi": "الکافی",
    "alkafi": "الکافی",
    "kafi": "الکافی",
    "al-amali": "امالی",
    "al-amālī": "امالی",
    "amali": "امالی",
    "amālī": "امالی",
    "faqih": "من لا یحضره الفقیه",
    "man la yahduruhu": "من لا یحضره الفقیه",
    "tahdhib": "تهذیب الاحکام",
    "istibsar": "الاستبصار",
    "nahj": "نهج البلاغه",
    "sahifa": "صحیفه سجادیه",
    "bihar": "بحارالانوار",
    "wasail": "وسائل الشیعه",
    "tuhaf": "تحف العقول",
    "khisal": "الخصال",
    "uyun": "عیون اخبار الرضا",
    "ʿuyūn": "عیون اخبار الرضا",
    "uyūn": "عیون اخبار الرضا",
    "akhbar al-rida": "عیون اخبار الرضا",
    "akhbār al-riḍā": "عیون اخبار الرضا",
    "kamal": "کمال الدین",
    "ilal": "علل الشرائع",
    "tawhid": "التوحید",
    "thawab": "ثواب الاعمال",
    "iqbal": "اقبال الاعمال",
    "misbah": "مصباح المتهجد",
}

_AUTHOR_FA = {
    "kulayni": "شیخ کلینی",
    "kulaynī": "شیخ کلینی",
    "saduq": "شیخ صدوق",
    "ṣaduq": "شیخ صدوق",
    "ibn babawayh": "شیخ صدوق",
    "tusi": "شیخ طوسی",
    "ṭūsī": "شیخ طوسی",
    "mufid": "شیخ مفید",
    "mufīd": "شیخ مفید",
    "majlisi": "علامه مجلسی",
    "majlesi": "علامه مجلسی",
    "hur amili": "شیخ حر عاملی",
    "hurr": "شیخ حر عاملی",
}

_GRADE_FA = {
    "sahih": "صحیح",
    "ṣaḥīḥ": "صحیح",
    "hasan": "حسن",
    "ḥasan": "حسن",
    "muwathaq": "موثق",
    "muwaththaq": "موثق",
    "daif": "ضعیف",
    "ḍaʿīf": "ضعیف",
    "weak": "ضعیف",
    "good": "حسن",
    "authentic": "صحیح",
}


def _map_fa(name: str, table: dict, default: str = "") -> str:
    n = (name or "").strip()
    if not n:
        return default
    low = n.lower()
    for k, v in table.items():
        if k in low:
            return v
    # اگر هنوز لاتین است و جدول نخورد، خالی برگردان تا منبع شلوغ نشود
    if re.search(r"[A-Za-z]{4,}", n) and not re.search(r"[آ-ی]", n):
        return default
    return n


def _clean(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"^\d+[\-–.]\s*", "", s)
    return s


def _extract_hadith_quote(eng: str) -> str:
    """از متن انگلیسی، متن اصلی حدیث را جدا کن (بدون سند طولانی)."""
    s = _clean(eng)
    if not s:
        return ""

    # بعد از said: / has said the following:
    m = re.search(
        r"(?:has said|said|says|stated)(?: the following)?\s*[:：]\s*(.+)",
        s,
        re.I | re.S,
    )
    if m:
        q = _clean(m.group(1).strip(" \"'«»"))
        if len(q) >= 25:
            s = q

    # حذف مقدمه سند
    s = re.sub(
        r"^(?:It is narrated|Narrated|A number of our people|"
        r"Several of our companions)[^:]{0,200}:\s*",
        "",
        s,
        flags=re.I,
    )
    s = _clean(s)

    max_len = 380
    if len(s) > max_len:
        cut = s[:max_len]
        for sep in (". ", "! ", "? "):
            idx = cut.rfind(sep)
            if idx >= 80:
                cut = cut[: idx + 1]
                break
        else:
            idx = cut.rfind(" ")
            if idx >= 80:
                cut = cut[:idx]
        s = cut.strip().rstrip(".") + "."

    return s


def _looks_like_isnad(text: str) -> bool:
    """آیا متن بیشتر سند راوی است تا خود حدیث؟"""
    t = text.lower()
    markers = len(re.findall(r"\bfrom\b|ibn |bin |narrated|has narrated", t))
    return markers >= 4 and len(text) > 120


async def _en_to_fa(text: str, client: httpx.AsyncClient) -> Optional[str]:
    text = _clean(text)
    if not text or len(text) < 3:
        return None
    chunk = text[:420]

    def _ok(tr: str) -> bool:
        if not tr or tr.lower() == chunk.lower():
            return False
        u = tr.upper()
        if any(x in u for x in ("INVALID", "QUERY LENGTH", "MYMEMORY WARNING", "USED ALL AVAILABLE")):
            return False
        if not re.search(r"[آ-ی]{8,}", tr):
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
        logger.debug("hadith gtx: %s", e)

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
        logger.debug("hadith mymemory: %s", e)

    return None


async def _fetch_thaqalayn(client: httpx.AsyncClient) -> Optional[Tuple[str, str]]:
    """(منبع فارسی، متن فارسی کامل — بدون بریدگی نامفهوم)."""
    try:
        r = await client.get(
            "https://www.thaqalayn-api.net/api/v2/random",
            timeout=8.0,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        if not isinstance(data, dict):
            return None

        book = _map_fa(str(data.get("book") or data.get("bookId") or ""), _BOOK_FA, "منابع اهل‌بیت")
        author = _map_fa(str(data.get("author") or ""), _AUTHOR_FA, "")
        grade_raw = str(
            data.get("majlisiGrading")
            or data.get("mohseniGrading")
            or data.get("behbudiGrading")
            or ""
        ).strip()
        grade = _map_fa(grade_raw, _GRADE_FA, grade_raw if re.search(r"[آ-ی]", grade_raw) else "")

        eng = _extract_hadith_quote(str(data.get("englishText") or ""))
        ara = _clean(str(data.get("arabicText") or ""))

        if not eng and not ara:
            return None
        if eng and _looks_like_isnad(eng):
            # سندخالی — رد کن تا fallback محلی بیاید
            return None

        fa = await _en_to_fa(eng, client) if eng else None

        # اگر ترجمه نشد، حدیث API را رها کن (متن انگلیسی برای کاربر فارسی بد است)
        if not fa:
            return None

        # ترجمه هم نباید ناقص/سندگونه باشد
        if fa.endswith("...") or fa.endswith("…") or _looks_like_isnad(fa):
            return None
        if len(fa) < 20:
            return None

        bits = [book]
        if author:
            bits.append(author)
        if grade:
            bits.append(f"درجه: {grade}")
        source = " — ".join(bits)

        return source, fa
    except Exception as e:
        logger.error("thaqalayn: %s", e)
        return None


async def daily_verse_hadith(user_id: int = 0) -> str:
    """آیه + حدیث شیعی تمیز و کامل."""
    verse_text = None
    hadith_source = None
    hadith_body = None

    try:
        async with httpx.AsyncClient(timeout=14.0) as client:
            try:
                r = await client.get(
                    "https://api.alquran.cloud/v1/ayah/random/fa.fooladvand",
                    timeout=8.0,
                )
                if r.status_code == 200:
                    data = r.json().get("data") or {}
                    fa_text = (data.get("text") or "").strip()
                    surah = (data.get("surah") or {}).get("name") or ""
                    num = data.get("numberInSurah") or ""
                    number = data.get("number")
                    ar_text = ""
                    if number:
                        try:
                            r2 = await client.get(
                                f"https://api.alquran.cloud/v1/ayah/{number}/quran-uthmani",
                                timeout=6.0,
                            )
                            if r2.status_code == 200:
                                ar_text = (r2.json().get("data") or {}).get("text") or ""
                        except Exception:
                            pass
                    if fa_text or ar_text:
                        lines = []
                        if ar_text:
                            lines.append(f"﴿{ar_text}﴾")
                        if fa_text:
                            lines.append(f"«{fa_text}»")
                        lines.append(f"— {surah} آیه {num}")
                        verse_text = "\n".join(lines)
            except Exception as e:
                logger.error("verse api: %s", e)

            # چند بار تلاش برای حدیث تمیز
            for _ in range(3):
                got = await _fetch_thaqalayn(client)
                if got:
                    hadith_source, hadith_body = got
                    break
    except Exception as e:
        logger.error("verse_hadith: %s", e)

    if not verse_text:
        vitem = random.choice(LOCAL_VERSES)
        verse_text = f"{vitem[0]}\n«{vitem[1]}»\n— {vitem[2]} آیه {vitem[3]}"

    if not hadith_body:
        src, txt = random.choice(HADITHS)
        hadith_source, hadith_body = src, txt

    return (
        "📖 **آیه و حدیث**\n\n"
        f"**آیه:**\n{verse_text}\n\n"
        f"**حدیث:**\n*{hadith_source}:*\n{hadith_body}\n\n"
        "💚 تدبر کنید و به کار بندید."
    )
