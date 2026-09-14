from __future__ import annotations

from bot.services.ai_service import ask_ai

_REQUIRED = (
    "وضعیت بازار", "ساختار", "BOS", "کندل", "حمایت", "عرضه",
    "نقدینگی", "شکست", "RSI", "حجم", "Funding", "MTF",
    "Long", "Short", "invalidation", "نتیجه",
)


def _has_any(text: str, *terms: str) -> bool:
    return any(term.lower() in text for term in terms)


def _looks_incomplete(answer: str) -> bool:
    lower = (answer or "").lower()
    missing = sum(section.lower() not in lower for section in _REQUIRED)
    has_long = _has_any(lower, "سناریوی long", "سناریوی لانگ", "لانگ", "long")
    has_short = _has_any(lower, "سناریوی short", "سناریوی شورت", "شورت", "short")
    has_result = _has_any(lower, "نتیجه نهایی", "نتیجه گیری", "نتیجه‌گیری", "جمع‌بندی", "جمع بندی")
    return missing >= 3 or not (has_long and has_short and has_result)


def _missing_sections(answer: str) -> str:
    lower = (answer or "").lower()
    labels = (
        ("شکست و retest", "شکست"),
        ("RSI/ADX/ATR", "rsi"),
        ("حجم", "حجم"),
        ("واگرایی", "واگرایی"),
        ("Funding/OI/Long-Short", "funding"),
        ("MTF", "mtf"),
        ("سناریوی Long", "سناریوی long", "سناریوی لانگ", "لانگ"),
        ("سناریوی Short", "سناریوی short", "سناریوی شورت", "شورت"),
        ("invalidation و مدیریت ریسک", "invalidation", "ابطال", "مدیریت ریسک"),
        ("نتیجه نهایی", "نتیجه نهایی", "جمع‌بندی", "جمع بندی"),
    )
    missing = []
    for label, *terms in labels:
        if not _has_any(lower, *terms):
            missing.append(label)
    return "، ".join(missing) or "بخش‌های پایانی"


async def build_crypto_ai_report(*, user_id: int, symbol: str, base_report: str, timeframe: str = "4H") -> str:
    """Generate a complete report with one continuation only when truly needed."""
    base = (base_report or "").strip()
    prompt = (
        f"تو تحلیل‌گر ارشد Price Action و بازارهای مالی هستی. تایم‌فریم تمرکز: {timeframe}. "
        "داده‌های زیر از منابع زنده سیستم آمده‌اند. هیچ قیمت، سطح، درصد یا داده‌ای را حدس نزن. "
        "گزارش را برای Telegram، کوتاه اما کامل و با تیترهای شماره‌دار تولید کن؛ جدول Markdown نساز. "
        "حتماً تا انتهای ۱۶ بخش برو و قبل از پایان، همه بخش‌ها را تکمیل کن: "
        "1) وضعیت بازار، 2) HH/HL/LH/LL، 3) BOS/CHOCH، 4) کندل و rejection، "
        f"5) حمایت/مقاومت همان {timeframe}، 6) عرضه/تقاضا، 7) نقدینگی و Equal High/Low، "
        "8) شکست و retest، 9) RSI/ADX/ATR، 10) حجم، 11) واگرایی، "
        "12) Funding/OI/Long-Short، 13) MTF، 14) سناریوی Long، "
        "15) سناریوی Short و invalidation/مدیریت ریسک، 16) نتیجه نهایی. "
        "اگر داده‌ای نیست دقیقاً بگو «داده‌ای موجود نیست». در بازار ضعیف یا متناقض ورود را تأیید نکن. "
        "مهم: پاسخ را با بخش‌های ابتدایی طولانی نکن؛ هر بخش را مختصر نگه دار تا همه ۱۶ بخش در همین پاسخ جا شود. "
        "فقط از اعداد موجود در داده استفاده کن.\n\n" + base[:12000]
    )
    answer, _ = await ask_ai(user_id, prompt)
    answer = (answer or "").strip()
    if not answer or not _looks_incomplete(answer):
        return answer

    missing = _missing_sections(answer)
    continuation_prompt = (
        "پاسخ قبلی قبل از پایان قطع شده است. فقط بخش‌های باقی‌مانده را ادامه بده و هیچ‌کدام از بخش‌های قبلی را تکرار نکن. "
        f"بخش‌های مورد انتظار باقی‌مانده: {missing}. "
        "برای هر مورد یک تیتر کوتاه و نتیجه مشخص بده و در پایان حتماً «نتیجه نهایی» را بنویس. "
        "اگر داده‌ای نیست بگو «داده‌ای موجود نیست» و هیچ عددی را حدس نزن. "
        "این بار پاسخ را فشرده بنویس تا تمام موارد باقی‌مانده در یک پاسخ جا شود.\n\n"
        "پاسخ قبلی (فقط برای دانستن نقطه توقف):\n" + answer[-7000:] +
        "\n\nداده پایه: \n" + base[:7000]
    )
    try:
        continuation, _ = await ask_ai(user_id, continuation_prompt)
        continuation = (continuation or "").strip()
        if continuation:
            return answer + "\n\n" + continuation
    except Exception:
        pass
    return answer
