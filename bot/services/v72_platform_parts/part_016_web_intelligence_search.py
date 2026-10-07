from typing import Any

# Auto-split part 16: web_intelligence_search
async def web_intelligence_search(query: str, max_results: int = 5) -> dict[str, Any]:
    """Multi-stage web search: discover, deduplicate, then fetch a bounded set of pages."""
    from bot.services.ai_extras import web_search
    raw = await web_search(query, max_results=max(3, min(10, max_results * 2)))
    urls = re.findall(r"https?://[^\s<>]+", raw or "")
    candidates = [{"url": u.rstrip(".,)]}"), "title": "", "score": 0.4} for u in urls]
    sources = dedupe_sources(candidates)
    fetched = await asyncio.gather(*(fetch_web_page(x["url"]) for x in sources[:max_results]), return_exceptions=True)
    final = []
    for base, item in zip(sources, fetched):
        if isinstance(item, Exception) or not item.get("ok"):
            continue
        final.append({**base, **item, "score": round(min(1.0, float(base.get("score", 0)) + min(.45, len(item.get("text", "")) / 20000)), 4)})
    return {"query": query[:300], "sources": dedupe_sources(final), "raw": raw[:12000]}
