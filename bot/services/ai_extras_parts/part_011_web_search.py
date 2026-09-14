# Auto-split part 11: web_search
async def web_search(query: str, max_results: int = 5) -> str:
    """جستجوی وب ساده (DuckDuckGo HTML)."""
    query = (query or "").strip()
    if not query:
        return "عبارت جستجو خالی است."
    try:
        import httpx
        from bs4 import BeautifulSoup

        url = "https://html.duckduckgo.com/html/"
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            r = await client.post(
                url,
                data={"q": query},
                headers={"User-Agent": "Mozilla/5.0 (compatible; RoozeZibaBot/1.0)"},
            )
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        for a in soup.select("a.result__a")[: max_results]:
            title = a.get_text(" ", strip=True)
            href = a.get("href") or ""
            results.append(f"• {title}\n  {href}")
        if not results:
            # fallback snippets
            for sn in soup.select(".result__snippet")[:max_results]:
                results.append("• " + sn.get_text(" ", strip=True))
        if not results:
            return f"نتیجه‌ای برای «{query}» پیدا نشد."
        return f"نتایج جستجو برای «{query}»:\n\n" + "\n\n".join(results)
    except Exception as e:
        # جزئیات فنی فقط در لاگ بماند؛ به کاربر نشت نکند.
        logger.warning("web_search failed: %s", e, exc_info=True)
        return "⚠️ جستجوی وب فعلاً در دسترس نیست. چند ثانیه بعد دوباره امتحان کنید."
