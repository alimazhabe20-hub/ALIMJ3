from typing import Any

# Auto-split part 9: advanced_intent
def advanced_intent(text: str) -> dict[str, Any]:
    s = str(text or "").strip().lower()
    rules = [
        ("market", r"بازار|قیمت|کریپتو|بیت.?کوین|اتریوم|طلا|ارز|btc|eth|gold|crypto"),
        ("news", r"خبر|اخبار|نیوز|news|latest|خبر جدید"),
        ("calendar", r"تقویم|تقویم اقتصادی|economic calendar|cpi|ppi|nfp|fomc|نرخ بهره"),
        ("web", r"جستجو|وب|منبع|سرچ|search|research"),
        ("download", r"دانلود|download|لینک فایل|فایل دانلود"),
        ("document", r"pdf|word|excel|سند|فایل|متن فایل|جدول"),
        ("report", r"گزارش|report|xlsx|csv|pdf گزارش"),
        ("alert", r"هشدار|آلارم|alert|اعلان قیمت"),
        ("backup", r"بکاپ|پشتیبان|backup|restore|بازیابی"),
        ("system", r"سلامت|وضعیت سیستم|health|status|diagnostic|عیب"),
        ("code", r"کد|برنامه|python|code|bug|باگ"),
    ]
    candidates = [name for name, pat in rules if re.search(pat, s, re.I)]
    return {"primary": candidates[0] if candidates else "general", "candidates": candidates, "needs_tool": bool(candidates), "confidence": min(1.0, 0.35 + 0.15 * len(candidates))}
