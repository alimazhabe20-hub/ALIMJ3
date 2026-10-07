from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from bot.services.v74_platform import AgentStep

# Auto-split part 14: _agent_intents
def _agent_intents(goal: str, available: set[str]) -> list[AgentStep]:
    q = (goal or "").lower()
    patterns: list[tuple[str, str, str, dict[str, Any], int]] = [
        (r"هوا|آب\s*و\s*هوا|دما|باران|weather", "get_weather", "weather", {}, 4),
        (r"آلودگی|کیفیت\s*هوا|aqi|air", "get_air_quality", "air_quality", {}, 4),
        (r"قیمت|بازار|کریپتو|بیت.?کوین|طلا|دلار|ارز|market|price", "get_market_prices", "market", {}, 5),
        (r"تقویم\s*اقتصادی|economic\s*calendar|اخبار\s*اقتصادی", "get_economic_calendar", "calendar", {}, 5),
        (r"مستندات|راهنما|قابلیت.*ربات|knowledge|documentation", "search_knowledge_base", "knowledge", {"query": goal}, 4),
        (r"اینترنت|وب|جستجو|خبر|اخبار|latest|news|search", "hybrid_retrieve", "web", {"query": goal, "include_web": True}, 5),
        (r"خرید|بخر|فروشگاه|shopping|قیمت.*محصول", "search_shopping", "shopping", {"query": goal, "source": "all", "max_results": 8}, 4),
    ]
    found: list[tuple[int, AgentStep]] = []
    for pattern, tool, reason, args, score in patterns:
        if tool in available and re.search(pattern, q, re.I):
            found.append((score, AgentStep(tool, dict(args), reason)))
    found.sort(key=lambda x: (-x[0], x[1].tool))
    return [x[1] for x in found[:MAX_AGENT_STEPS]]
