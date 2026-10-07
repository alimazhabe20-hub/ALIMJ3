from typing import Any

# Auto-split part 3: build_plan
def build_plan(goal: str) -> list[dict[str, Any]]:
    """Create a small, explainable plan from the user's goal."""
    q = (goal or "").strip()
    if not q:
        return []
    steps: list[dict[str, Any]] = []
    # Fresh/current requests should go through hybrid retrieval first so that
    # web freshness is available before domain-specific tools are considered.
    if _current(q) and bool(re.search(r"خبر|اخبار|اطلاعات|بررسی|وضعیت|latest|news|current", q, re.I)):
        steps.append({"tool": "hybrid_retrieve", "arguments": {"query": q, "include_web": True}})
        if len(steps) >= MAX_PLAN_STEPS:
            return steps
    weather = bool(re.search(r"هوا|آب\s*و\s*هوا|دما|باران|بارون|weather", q, re.I))
    aqi = bool(re.search(r"کیفیت\s*هوا|آلودگی|aqi", q, re.I))
    market = bool(re.search(r"قیمت|دلار|یورو|طلا|سکه|ارز|کریپتو|بیت.?کوین|market|price", q, re.I))
    knowledge = bool(re.search(r"مستندات|راهنمای ربات|قابلیت.*ربات|تنظیمات.*ربات|knowledge|documentation", q, re.I))
    shopping = bool(re.search(r"خرید|بخر|قیمت.*محصول|لینک.*خرید|فروشگاه|shopping", q, re.I))

    if weather:
        args = {}
        city = _city_from_query(q)
        if city:
            args["city"] = city
        steps.append({"tool": "get_weather", "arguments": args})
        if aqi and len(steps) < MAX_PLAN_STEPS:
            steps.append({"tool": "get_air_quality", "arguments": args})
    if market and len(steps) < MAX_PLAN_STEPS:
        steps.append({"tool": "get_market_prices", "arguments": {}})
    if shopping and len(steps) < MAX_PLAN_STEPS:
        steps.append({"tool": "search_shopping", "arguments": {"query": q, "source": "all", "max_results": 8}})
    if knowledge and len(steps) < MAX_PLAN_STEPS:
        steps.append({"tool": "search_knowledge_base", "arguments": {"query": q, "limit": 5}})
    if not steps and _current(q):
        steps.append({"tool": "hybrid_retrieve", "arguments": {"query": q, "include_web": True}})
    if not steps and re.search(r"اینترنت|وب|جستجو|خبر", q, re.I):
        steps.append({"tool": "web_search", "arguments": {"query": q}})
    return steps[:MAX_PLAN_STEPS]
