from __future__ import annotations

import re

from bot.services.ai_service import ask_ai


# These are the exact 16 report sections the smart-analysis button must return.
_SECTION_LABELS = (
    "وضعیت بازار",
    "HH / HL / LH / LL",
    "BOS / CHOCH",
    "کندل و Rejection",
    "حمایت/مقاومت",
    "عرضه/تقاضا",
    "نقدینگی",
    "شکست و Retest",
    "RSI / ADX / ATR",
    "حجم",
    "واگرایی",
    "Funding / OI / Long-Short",
    "MTF",
    "سناریوی Long",
    "سناریوی Short",
    "نتیجه نهایی",
)


def _has_any(text: str, *terms: str) -> bool:
    low = (text or "").lower()
    return any(term.lower() in low for term in terms)


def _numbered_sections(answer: str) -> set[int]:
    """Return numbered section ids actually present in the model output."""
    found: set[int] = set()
    for match in re.finditer(r"(?m)^\s*\*{0,2}\s*(\d{1,2})\s*[.)：:-]", answer or ""):
        number = int(match.group(1))
        if 1 <= number <= 16:
            found.add(number)
    return found


def _looks_incomplete(answer: str) -> bool:
    """Detect truncation even when a heading itself is only partially printed."""
    text = (answer or "").strip()
    if not text:
        return True

    sections = _numbered_sections(text)
    if not set(range(1, 17)).issubset(sections):
        return True

    low = text.lower()
    # The last section must contain a real conclusion, not just its heading.
    tail = low[-1200:]
    has_result = _has_any(tail, "نتیجه نهایی", "نتیجه گیری", "نتیجه‌گیری", "جمع‌بندی", "جمع بندی")
    has_long = _has_any(low, "سناریوی long", "سناریوی لانگ", "لانگ")
    has_short = _has_any(low, "سناریوی short", "سناریوی شورت", "شورت")
    if not (has_long and has_short and has_result):
        return True

    # A response ending in a cut heading/word is a hard truncation signal.
    if re.search(r"(?i)(Funding\s*/\s*O(?:\s*$)|MTF\s*$|Long\s*$|Short\s*$|invalidation\s*$|/\s*$)", text):
        return True
    return False


def _missing_sections(answer: str) -> list[int]:
    """Find the exact numbered sections still missing or truncated."""
    present = _numbered_sections(answer)
    missing = [n for n in range(1, 17) if n not in present]

    # If section 12 is printed as e.g. "Funding / O", it has a heading but no
    # usable body. Treat it and everything after it as unfinished.
    lines = (answer or "").splitlines()
    for i, line in enumerate(lines):
        if re.search(r"(?i)\bFunding\s*/\s*O\s*$", line.strip("* ")):
            for n in range(12, 17):
                if n not in missing:
                    missing.append(n)
            break

    return sorted(set(missing))


def _compact_missing_text(missing: list[int]) -> str:
    if not missing:
        return "بخش‌های ناقص انتهایی"
    return "، ".join(f"{n}) { _SECTION_LABELS[n-1] }" for n in missing)


async def build_crypto_ai_report(*, user_id: int, symbol: str, base_report: str, timeframe: str = "4H") -> str:
    """Generate a complete 16-section crypto report with bounded continuation."""
    base = (base_report or "").strip()
    prompt = (
        f"تو تحلیل‌گر ارشد Price Action و بازارهای مالی هستی. تایم‌فریم تمرکز: {timeframe}. "
        "داده‌های زیر از منابع زنده سیستم آمده‌اند. هیچ قیمت، سطح، درصد یا داده‌ای را حدس نزن. "
        "گزارش برای Telegram است و باید دقیقاً ۱۶ بخش شماره‌دار داشته باشد. جدول Markdown نساز. "
        "هر بخش حداکثر ۱ تا ۲ خط باشد تا هر ۱۶ بخش حتماً در همین پاسخ تمام شود. "
        "هیچ بخش یا تیتر را نیمه‌کاره رها نکن و بعد از بخش ۱۶ پاسخ را تمام کن. "
        "اگر داده‌ای برای یک بخش نیست دقیقاً بنویس «داده‌ای موجود نیست». "
        "در بازار ضعیف یا متناقض ورود را تأیید نکن. فقط از اعداد موجود در داده استفاده کن.\n\n"
        "بخش‌های اجباری: "
        "1) وضعیت بازار، 2) HH/HL/LH/LL، 3) BOS/CHOCH، 4) کندل و rejection، "
        f"5) حمایت/مقاومت همان {timeframe}، 6) عرضه/تقاضا، 7) نقدینگی و Equal High/Low، "
        "8) شکست و retest، 9) RSI/ADX/ATR، 10) حجم، 11) واگرایی، "
        "12) Funding/OI/Long-Short، 13) MTF، 14) سناریوی Long، "
        "15) سناریوی Short + invalidation/مدیریت ریسک، 16) نتیجه نهایی.\n\n"
        + base[:12000]
    )

    answer, _ = await ask_ai(user_id, prompt)
    answer = (answer or "").strip()
    if not _looks_incomplete(answer):
        return answer

    missing = _missing_sections(answer)
    missing_text = _compact_missing_text(missing)
    continuation_prompt = (
        "پاسخ قبلی قطع شده است. فقط بخش‌های ناقص زیر را کامل کن؛ هیچ متن قبلی را تکرار نکن. "
        f"بخش‌های ناقص: {missing_text}. "
        "از همان شماره‌گذاری استفاده کن و برای هر بخش حداکثر ۲ خط بنویس. "
        "اگر داده‌ای نیست دقیقاً «داده‌ای موجود نیست» بنویس و عدد جدید نساز. "
        "حتماً بخش ۱۲ Funding/OI/Long-Short را کامل کن و سپس MTF، Long، Short، "
        "invalidation/مدیریت ریسک و در آخر «16) نتیجه نهایی» را کامل و تمام کن. "
        "پاسخ را فشرده نگه دار و بعد از نتیجه نهایی هیچ جمله‌ای اضافه نکن.\n\n"
        "آخرین قسمت پاسخ قبلی:\n" + answer[-5000:] +
        "\n\nداده پایه:\n" + base[:7000]
    )

    try:
        continuation, _ = await ask_ai(user_id, continuation_prompt)
        continuation = (continuation or "").strip()
    except Exception:
        continuation = ""

    if continuation:
        combined = answer + "\n\n" + continuation
        if not _looks_incomplete(combined):
            return combined
        # One final compact repair is allowed only when the continuation itself
        # was also cut. This avoids returning another visibly incomplete report.
        remaining = _missing_sections(combined)
        if remaining:
            repair_prompt = (
                "فقط بخش‌های زیر در گزارش تحلیل ناقص مانده‌اند. بدون تکرار بخش‌های قبلی، "
                f"این موارد را کامل کن: {_compact_missing_text(remaining)}. "
                "هر مورد حداکثر ۲ خط. در پایان حتماً «16) نتیجه نهایی» را کامل کن. "
                "اگر داده‌ای نیست بنویس «داده‌ای موجود نیست».\n\n"
                "گزارش فعلی:\n" + combined[-7000:]
            )
            try:
                repair, _ = await ask_ai(user_id, repair_prompt)
                repair = (repair or "").strip()
                if repair:
                    combined += "\n\n" + repair
            except Exception:
                pass
        return combined

    return answer
