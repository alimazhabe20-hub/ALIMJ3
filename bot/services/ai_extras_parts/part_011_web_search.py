# Auto-split part 11: web_search
async def web_search(query: str, max_results: int = 5) -> str:
    """Live web search with freshness metadata and bounded snippets.

    This is intentionally a discovery tool. It never invents a result when the
    network fails and it marks the response as unavailable so the AI layer can
    refuse to present stale model knowledge as current data.
    """
    from datetime import datetime, timezone

    query = (query or "").strip()
    if not query:
        return "LIVE_DATA_UNAVAILABLE: عبارت جستجو خالی است."
    max_results = max(1, min(int(max_results or 5), 10))
    date_tag = datetime.now(timezone.utc).date().isoformat()
    live_query = f"{query} (current as of {date_tag})"
    try:
        import httpx
        from bs4 import BeautifulSoup

        url = "https://html.duckduckgo.com/html/"
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            r = await client.post(
                url,
                data={"q": live_query},
                headers={"User-Agent": "Mozilla/5.0 (compatible; RoozeZibaBot/1.0)"},
            )
            r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        result_nodes = soup.select(".result")[:max_results]
        results = []
        for node in result_nodes:
            a = node.select_one("a.result__a")
            if not a:
                continue
            title = a.get_text(" ", strip=True)
            href = a.get("href") or ""
            snippet_node = node.select_one(".result__snippet")
            snippet = snippet_node.get_text(" ", strip=True) if snippet_node else ""
            block = f"• {title}\n  {href}"
            if snippet:
                block += f"\n  خلاصه: {snippet}"
            results.append(block)
        if not results:
            return f"LIVE_DATA_UNAVAILABLE: برای «{query}» نتیجه قابل اتکایی پیدا نشد."
        return (
            f"LIVE_WEB_RESULTS (searched {date_tag} UTC) برای «{query}»:\n\n"
            + "\n\n".join(results)
        )
    except Exception as e:
        logger.warning("web_search failed: %s", e, exc_info=True)
        return "LIVE_DATA_UNAVAILABLE: جستجوی وب فعلاً در دسترس نیست؛ اطلاعات قدیمی را جایگزین نکن."
