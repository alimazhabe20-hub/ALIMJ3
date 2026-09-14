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
    has_long = _has_any(lower, "سناریوی long", "سناریوی لانگ", "long")
    has_short = _has_any(lower, "سناریوی short", "سناریوی شورت", "short")
    has_result = _has_any(lower, "نتیجه نهایی", "نتیجه گیری", "نتیجه‌گیری", "جمع‌بندی", "جمع بندی")
    return missing >= 3 or not (has_long and has_short and has_result)

async def build_crypto_ai_report(*, user_id: int, symbol: str, base_report: str, timeframe: str = "4H") -> str:
    """Generate the full crypto AI report; use one continuation only if incomplete."""
    base = (base_report or "").strip()
    prompt = (
        f"تو تحلیل‌گر ارشد Price Action و بازارهای مالی هستی. تایم‌فریم تمرکز: {timeframe}. "
        "داده‌های زیر از منابع زنده سیستم آمده‌اند. همه داده‌های موجود را بررسی کن و هیچ قیمت، سطح یا درصدی را حدس نزن. "
        "خروجی برای Telegram است و باید گزارش کامل و چندبخشی باشد؛ جدول Markdown نساز. "
        "حتماً این ۱۶ بخش را تا انتها پوشش بده: "
        "1) وضعیت بازار، 2) HH/HL/LH/LL، 3) BOS/CHOCH، 4) کندل و rejection، "
        f"5) حمایت/مقاومت همان {timeframe}، 6) عرضه/تقاضا، 7) نقدینگی و Equal High/Low، "
        "8) شکست و retest، 9) RSI/ADX/ATR و حجم، 10) واگرایی، 11) Funding/OI/Long-Short، "
        "12) MTF، 13) سناریوی Long، 14) سناریوی Short، 15) invalidation و مدیریت ریسک، "
        "16) نتیجه نهایی. اگر داده‌ای نیست صریحاً «داده‌ای موجود نیست» بنویس. "
        "در بازار ضعیف یا متناقض، ورود را تأیید نکن. تیترها واضح و شماره‌گذاری‌شده باشند. "
        "فقط از اعداد موجود در داده استفاده کن.\n\n" + base[:12000]
    )
    answer, _ = await ask_ai(user_id, prompt)
    answer = (answer or "").strip()
    if not answer or not _looks_incomplete(answer):
        return answer

    continuation_prompt = (
        "این گزارش Price Action زودتر از موعد متوقف شده است. فقط ادامه گزارش را بنویس و بخش‌های قبلی را تکرار نکن. "
        "بخش‌های باقی‌مانده را پوشش بده، مخصوصاً شکست و retest، RSI/ADX/ATR، حجم، واگرایی، Funding/OI/Long-Short، "
        "MTF، سناریوی Long، سناریوی Short، invalidation/مدیریت ریسک و نتیجه نهایی. "
        "اگر داده‌ای نیست بگو «داده‌ای موجود نیست». هیچ عددی را حدس نزن. پاسخ فقط ادامه متن باشد.\n\n"
        "گزارش پایه:\n" + base[:12000] + "\n\nپاسخ فعلی:\n" + answer[-9000:]
    )
    try:
        continuation, _ = await ask_ai(user_id, continuation_prompt)
        continuation = (continuation or "").strip()
        if continuation:
            return answer + "\n\n" + continuation
    except Exception:
        pass
    return answer
