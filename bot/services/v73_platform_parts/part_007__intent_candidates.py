from typing import Any

# Auto-split part 7: _intent_candidates
def _intent_candidates(goal: str, available: set[str]) -> list[dict[str, Any]]:
    q = goal.lower()
    candidates: list[tuple[int, str, dict[str, Any]]] = []
    patterns = [
        ("weather", r"هوا|آب\s*و\s*هوا|دما|باران|weather", "get_weather", {}),
        ("air", r"آلودگی|کیفیت\s*هوا|aqi", "get_air_quality", {}),
        ("market", r"قیمت|بازار|کریپتو|بیت.?کوین|طلا|دلار|ارز|market|price", "get_market_prices", {}),
        ("knowledge", r"مستندات|راهنما|قابلیت.*ربات|knowledge|documentation", "search_knowledge_base", {"query": goal}),
        ("web", r"اینترنت|وب|جستجو|خبر|اخبار|latest|news|search", "hybrid_retrieve", {"query": goal, "include_web": True}),
        ("shopping", r"خرید|بخر|فروشگاه|shopping", "search_shopping", {"query": goal, "source": "all", "max_results": 8}),
    ]
    for _, pattern, tool, args in patterns:
        if tool in available and re.search(pattern, q, re.I):
            score = len(re.findall(pattern, q, re.I)) + (2 if tool == "hybrid_retrieve" and re.search(r"جدید|فعلی|امروز|latest|news", q, re.I) else 0)
            candidates.append((score, tool, args))
    candidates.sort(key=lambda x: (-x[0], x[1]))
    return [{"tool": t, "arguments": a} for _, t, a in candidates[:MAX_AGENT_STEPS]]
