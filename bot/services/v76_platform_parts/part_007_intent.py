from typing import Any

# Auto-split part 7: intent
def intent(text: str) -> dict[str, Any]:
    s = str(text or "").lower()
    candidates = []
    rules = [("market", r"بازار|قیمت|کریپتو|بیت.?کوین|طلا|ارز|btc|gold|crypto"),
             ("news", r"خبر|اخبار|news|latest"), ("calendar", r"تقویم|economic calendar|خبر اقتصادی"),
             ("web", r"جستجو|وب|search|منبع"), ("download", r"دانلود|download|فایل"),
             ("document", r"pdf|word|excel|فایل|سند"), ("workflow", r"workflow|اتومات|خودکار"),
             ("report", r"گزارش|report"), ("code", r"کد|برنامه|code|python")]
    for name, pattern in rules:
        if re.search(pattern, s, re.I): candidates.append(name)
    return {"primary": candidates[0] if candidates else "general", "candidates": candidates, "needs_tool": bool(candidates)}
