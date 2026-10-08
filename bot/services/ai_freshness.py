"""Freshness routing for AI requests.

Requests whose answer can change with time must use a live tool before the model
is allowed to answer.  This module deliberately does not contain provider logic;
it only classifies the user request and supplies a safe instruction.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class FreshnessDecision:
    required: bool
    tool: str | None
    reason: str


_NB = r"(?<![\u0600-\u06ff])"   # not preceded by a Persian letter
_NA = r"(?![\u0600-\u06ff])"    # not followed by a Persian letter

_LIVE_MARKERS = re.compile(
    r"(?:امروز|الان|همین الان|فعلی|فعلاً|فعلیه|جدیدترین|آخرین|جدیدترین|به.?روز|به.?روزترین|(?<![\u0600-\u06ff])روز(?![\u0600-\u06ff])|این روزها|20[2-9]\d|latest|current|today|now|newest|recent|live|real.?time)",
    re.I,
)
_NEWS_MARKERS = re.compile(
    r"(?:خبر|اخبار|آخرین خبر|خبر جدید|چه خبر|news|breaking|headline)", re.I
)
_PRODUCT_MARKERS = re.compile(
    r"(?:خرید|بخر|فروشگاه|فروشنده|قیمت.*(?:گوشی|آیفون|iphone|لپ.?تاپ|تلویزیون|کفش|خمیر|محصول|کالا)|"
    r"(?:گوشی|آیفون|iphone|لپ.?تاپ|تلویزیون|کفش|خمیر|محصول|کالا).*(?:قیمت|خرید|موجودی)|"
    r"قیمت روز محصول|لینک خرید|ارزان.?ترین|موجودی|price.*product|buy|shop)",
    re.I,
)
_MARKET_MARKERS = re.compile(
    r"(?:بیت.?کوین|bitcoin|اتریوم|ethereum|تتر|usdt|کریپتو|رمزارز|"
    r"(?<![\u0600-\u06ff])طلا(?![\u0600-\u06ff])|xau|دلار|یورو|سکه|"
    r"(?<![\u0600-\u06ff])ارز(?![\u0600-\u06ff])|"
    r"قیمت.*(?:دلار|یورو|طلا|سکه|بیت|اتریوم|تتر)|نرخ.*(?:دلار|یورو|ارز))",
    re.I,
)
_WEATHER_MARKERS = re.compile(
    r"(?:(?<![\u0600-\u06ff])هوا(?![\u0600-\u06ff])|(?<![\u0600-\u06ff])هوای\s|آب.?وهوا|دمای|باران|برف|رطوبت|weather|forecast|air quality|کیفیت هوا)",
    re.I,
)
# Cover common Persian phrasings including «تاریخ الان» / «الان تاریخ»
_DATETIME_MARKERS = re.compile(
    r"(?:"
    r"تاریخ\s*(?:دقیق|فعلی|الان|امروز|فردا|دیروز|چنده|چندمه)|"
    r"(?:الان|امروز|فردا|دیروز)\s*تاریخ|"
    r"امروز\s*(?:چندمه|چه\s*روز|چه\s*تاریخی)|"
    r"الان\s*(?:چه\s*)?(?:ساعت|چه\s*ساعتی|چندمه|چه\s*روزی)|"
    r"ساعت\s*(?:الان|چنده|چند\s*است)|"
    r"(?:فردا|دیروز|پس\s*فردا)\s*(?:چندمه|تاریخ|چه\s*روز)|"
    r"current\s*(?:date|time|datetime)|"
    r"today(?:\s*date)?|tomorrow|yesterday|"
    r"what\s*(?:time|date)\s*is\s*it|right\s*now"
    r")",
    re.I,
)
_MOVIE_MARKERS = re.compile(
    r"(?:فیلم|سریال|movie|series|IMDb|فیلم\s*(?:جدید|تازه|امسال|این ماه|اخیر)|جدیدترین\s*(?:فیلم|سریال)|آخرین\s*(?:فیلم|سریال))", re.I
)

# ── v79: broad "volatile knowledge" detection ────────────────────────────────
# A model's memory is stale for anything that gets released, priced, elected or
# announced over time.  Instead of only matching explicit words like «قیمت», we
# also treat "recommend / find / compare / best / specs of <thing that changes>"
# as live.  Anything that matches here is routed to a live tool first.
_CATEGORY_WORDS = (
    r"گوشی|موبایل|تلفن\s*همراه|آیفون|iphone|گلکسی|galaxy|پیکسل|pixel|شیائومی|xiaomi|پوکو|poco|ردمی|redmi|"
    r"سامسونگ|samsung|اپل|apple|هواوی|huawei|آنر|honor|نوکیا|nokia|موتورولا|motorola|وان.?پلاس|oneplus|"
    r"لپ.?تاپ|laptop|مک.?بوک|macbook|تبلت|tablet|آیپد|ipad|ساعت\s*هوشمند|smart.?watch|ایرپاد|airpods|"
    r"هدفون|هدست|هندزفری|پاور.?بانک|شارژر|کارت\s*گرافیک|gpu|rtx|پردازنده|cpu|رم|ssd|مانیتور|"
    r"تلویزیون|tv|کنسول|ps[45]|playstation|xbox|نینتندو|nintendo|دوربین|پهپاد|dron|"
    r"ماشین|خودرو|اتومبیل|موتور.?سیکلت|دوچرخه|اسکوتر|یخچال|لباسشویی|ظرفشویی|جاروبرقی|اسپیلت|کولر|"
    r"ربات\s*جارو|ایرفرایر|اجاق|مایکروویو|کفش|کتانی|لباس|ساعت\s*مچی|عطر|لوازم\s*آرایشی"
)
_CATEGORY = re.compile(r"(?:" + _CATEGORY_WORDS + r")", re.I)
_RECOMMEND = re.compile(
    r"(?:پیدا\s*کن|پیدا\s*کنی|بگرد|جستجو|سرچ|پیشنهاد|معرفی|توصیه|راهنمایی|کدوم|کدام|چی\s*بخرم|"
    r"بهترین|بهتره|ارزش\s*خرید|مقایسه|مناسب|به\s*صرفه|ارزون|ارزان|گرون|گران|"
    r"best|recommend|suggest|compare|vs\.?|which|find me|top\s*\d*)",
    re.I,
)
_BUDGET = re.compile(
    r"(?:\d[\d,٬.]*\s*(?:میلیون|ملیون|هزار|تومن|تومان|ریال|دلار|\$|million|usd)|"
    r"(?:بودجه|زیر|تا|حدود|حدودا|حدوداً|بین)\s*\d|بودجه|budget|under\s*\$?\d)",
    re.I,
)
_SPEC_OR_NEW = re.compile(
    r"(?:مشخصات|specs?|ویژگی|نقد\s*و\s*بررسی|بررسی|review|مدل\s*(?:جدید|تازه|امسال)|"
    r"نسخه\s*(?:جدید|تازه)|عرضه|معرفی\s*شد|رونمایی|منتشر\s*شد|release|launch|"
    r"چه\s*خبر|چی\s*شد|آپدیت|update|ورژن|version|نسل)",
    re.I,
)
_AI_TECH = re.compile(
    r"(?:chatgpt|gpt[- ]?\d|openai|claude|gemini|llama|deepseek|grok|mistral|midjourney|sora|"
    r"هوش\s*مصنوعی|مدل\s*زبانی|ai\s*model|بهترین\s*مدل|ios\s*\d|android\s*\d+|اندروید\s*\d+|ویندوز\s*\d+|"
    r"python\s*3\.\d+|node\s*\d+|react\s*\d+|لایبرری|کتابخانه.*(?:نسخه|جدید))",
    re.I,
)
_OFFICE_HOLDER = re.compile(
    r"(?:رئیس.?جمهور|رییس.?جمهور|نخست.?وزیر|وزیر|مدیرعامل|ceo|پادشاه|رهبر|سخنگو|شهردار|"
    r"کاپیتان|مربی|سرمربی|president|prime minister|chancellor)",
    re.I,
)
_SPORT_RESULT = re.compile(
    r"(?:نتیجه|برنده|قهرمان|قهرمانی|جدول|رده.?بندی|بازی|مسابقه|لیگ|جام|score|standings|champion|winner|fixture)",
    re.I,
)
_EVENT_NOW = re.compile(
    r"(?:تحریم|انتخابات|جنگ|زلزله|سیل|اعتصاب|توافق|مذاکره|قانون\s*جدید|بخشنامه|مصوبه|یارانه|وام|"
    r"بنزین|حقوق|عیدی|مالیات|تعطیلی|تعطیل\s*است|ساعت\s*کاری|باز\s*است|ثبت.?نام|کنکور|اطلاعیه)",
    re.I,
)


def _norm(text: str) -> str:
    """Normalize Persian/Arabic variants and digits so regexes behave."""
    t = (text or "").replace("ي", "ی").replace("ك", "ک")
    t = t.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
    return re.sub(r"[\u200c\u200f\u200e]+", " ", t)


def _is_volatile_knowledge(q: str) -> tuple[bool, str | None, str]:
    """Return (required, tool, reason) for requests whose answer ages quickly."""
    # Shopping-like: a product category plus a recommend/find/budget signal.
    if _CATEGORY.search(q) and (_RECOMMEND.search(q) or _BUDGET.search(q)):
        return True, "search_shopping", "product recommendation/availability/prices change constantly"
    # Specs / new models / releases of products or AI & software versions.
    if (_CATEGORY.search(q) or _AI_TECH.search(q)) and _SPEC_OR_NEW.search(q):
        return True, "web_search", "product/model/version information is release-dependent"
    if _AI_TECH.search(q) and _RECOMMEND.search(q):
        return True, "web_search", "'best/latest' AI or software model rankings change monthly"
    if _OFFICE_HOLDER.search(q) and re.search(r"(?:کیه|کیست|کی\s*هست|چه\s*کسی|who|current|فعلی|الان|الآن)", q, re.I):
        return True, "web_search", "office holders change"
    if _SPORT_RESULT.search(q) and re.search(r"(?:دیشب|امشب|امروز|هفته|فصل|امسال|آخرین|اخیر|نتیجه|برنده|latest|last|current)", q, re.I):
        return True, "web_search", "sports results are time-sensitive"
    if _EVENT_NOW.search(q) and re.search(r"(?:الان|فعلی|امسال|جدید|آخرین|اخیر|چنده|چقدره|چقدر|کی\s*است|کی\s*هست|latest|current)", q, re.I):
        return True, "web_search", "current events/regulations change"
    return False, None, ""


def is_live_required(text: str) -> bool:
    """Return True when answering from model memory would be unsafe/stale."""
    q = _norm((text or "").strip())
    if not q:
        return False
    if _is_volatile_knowledge(q)[0]:
        return True
    return bool(
        _DATETIME_MARKERS.search(q)
        or _LIVE_MARKERS.search(q)
        or _NEWS_MARKERS.search(q)
        or _PRODUCT_MARKERS.search(q)
        or _MARKET_MARKERS.search(q)
        or _WEATHER_MARKERS.search(q)
        or _MOVIE_MARKERS.search(q)
    )


def classify(text: str) -> FreshnessDecision:
    q = _norm((text or "").strip())
    if not is_live_required(q):
        return FreshnessDecision(False, None, "static_or_general")
    if _DATETIME_MARKERS.search(q):
        return FreshnessDecision(
            True,
            "get_current_datetime",
            "current date/time must come from the real system clock",
        )
    if _PRODUCT_MARKERS.search(q):
        return FreshnessDecision(True, "search_shopping", "product/shopping data can change")
    if _MARKET_MARKERS.search(q):
        return FreshnessDecision(True, None, "market data can change")
    if _WEATHER_MARKERS.search(q):
        return FreshnessDecision(True, None, "weather data can change")
    if _MOVIE_MARKERS.search(q):
        return FreshnessDecision(
            True,
            "hub_movie_tv_latest",
            "movie/TV recommendations must use current catalog data",
        )
    volatile, tool, reason = _is_volatile_knowledge(q)
    if volatile:
        return FreshnessDecision(True, tool, reason)
    return FreshnessDecision(True, "web_search", "time-sensitive information requires live verification")


def today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _live_clock_snapshot() -> str:
    """Best-effort real clock text for datetime questions (never invent)."""
    try:
        from bot.services.current_datetime import current_datetime

        return current_datetime("")
    except Exception as exc:
        # Absolute fallback so the model still sees a real system timestamp.
        now = datetime.now(timezone.utc)
        return (
            f"UTC fallback clock: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC "
            f"(tool error: {type(exc).__name__})"
        )


def build_instruction(text: str) -> str:
    decision = classify(text)
    if not decision.required:
        return ""
    tool_line = (
        f"ابزار اجباری برای این درخواست: {decision.tool}."
        if decision.tool
        else "ابتدا از ابزار زنده/مرتبط ثبت‌شده استفاده کن و نتیجه آن را مبنا قرار بده."
    )
    parts = [
        "\n\n[LIVE DATA REQUIRED]\n"
        f"این سؤال زمان‌مند است ({decision.reason}). {tool_line} "
        "قبل از پاسخ نهایی، داده زنده را بررسی کن. از دانش قدیمی مدل برای قیمت، خبر، "
        "موجودی، وضعیت فعلی یا مشخصات عرضه‌شده به‌عنوان واقعیت امروز استفاده نکن. "
        "اگر ابزار زنده شکست خورد یا داده قابل تأیید نداد، صریحاً بگو اطلاعات فعلی قابل تأیید نیست "
        "و هیچ عدد/خبر/موجودی/تاریخ حدسی ارائه نکن.\n"
        f"تاریخ مرجع سیستم: {today_utc()} (UTC). "
        "برای پیشنهاد/مقایسه/مشخصات محصول (گوشی، لپ‌تاپ، خودرو، ...) فقط مدل‌هایی را معرفی کن که در نتایج ابزار همین الان دیده‌ای؛ "
        "مدل‌هایی که فقط از حافظه یادت هست (مثلاً نسل‌های قدیمی) را به‌عنوان پیشنهاد فعلی نده و منبع/تاریخ نتیجه را ذکر کن. "
        "برای فیلم/سریال جدید، سال فعلی را از تاریخ مرجع استخراج کن و هرگز سال ثابتی مثل 2024 را سال جاری فرض نکن. "
        "نتایج را بر اساس سال فعلی و سپس سال قبل مرتب کن."
    ]

    # For pure date/time questions, also embed the real system clock so even if
    # the tool-calling path fails, the model still has ground-truth text and
    # must not invent Jalali/Gregorian dates from training memory.
    if decision.tool == "get_current_datetime":
        clock = _live_clock_snapshot()
        parts.append(
            "\n[SYSTEM CLOCK — SOURCE OF TRUTH]\n"
            f"{clock}\n"
            "پاسخ تاریخ/ساعت را فقط بر اساس بلوک بالا بنویس. "
            "هیچ تاریخ شمسی یا میلادی دیگری از حافظه مدل نساز و اعداد را عوض نکن."
        )
    return "".join(parts)
