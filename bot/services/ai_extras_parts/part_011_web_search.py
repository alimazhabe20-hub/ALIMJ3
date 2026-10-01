# Auto-split part 11: web_search
async def web_search(query: str, max_results: int = 5) -> str:
    """Live web search with freshness metadata and useful result snippets."""
    query = (query or "").strip()
    if not query:
        return "عبارت جستجو خالی است."

    try:
        from bot.services.ai_freshness import freshness_query
        live_query = freshness_query(query)
    except Exception:
        live_query = query

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
        results = []
        for item in soup.select(".result")[: max_results]:
            a = item.select_one("a.result__a")
            if not a:
                continue
            title = a.get_text(" ", strip=True)
            href = a.get("href") or ""
            snippet_node = item.select_one(".result__snippet")
            snippet = snippet_node.get_text(" ", strip=True) if snippet_node else ""
            block = f"• {title}\n  {href}"
            if snippet:
                block += f"\n  خلاصه: {snippet}"
            results.append(block)

        if not results:
            for sn in soup.select(".result__snippet")[:max_results]:
                text = sn.get_text(" ", strip=True)
                if text:
                    results.append("• " + text)

        if not results:
            return (
                "LIVE_WEB_NO_RESULT: برای این درخواست نتیجه قابل اتکایی از وب پیدا نشد. "
                "از دانش قبلی مدل برای ادعای اطلاعات فعلی استفاده نکن."
            )

        return (
            "LIVE_WEB_OK: نتایج وب برای اطلاعات زمان‌مند. "
            "این نتایج بر دانش قدیمی مدل اولویت دارند.\n"
            f"جستجو: {live_query}\n\n" + "\n\n".join(results)
        )
    except Exception as e:
        logger.warning("web_search failed: %s", e, exc_info=True)
        return (
            "LIVE_WEB_FAILED: جستجوی زنده وب در دسترس نیست. "
            "برای اطلاعاتی که نیاز به به‌روز بودن دارند، حدس نزن و آن را به‌عنوان اطلاعات فعلی ارائه نکن."
        )
