# Auto-split part 11: web_search  (v79 — real search APIs + keyless fallback)
#
# Provider order (first one with a key wins, then automatic fallback to the next):
#   1. TAVILY_API_KEY   -> https://tavily.com           (best for LLMs: returns page text)
#   2. BRAVE_API_KEY    -> https://brave.com/search/api  (also BRAVE_SEARCH_API_KEY)
#   3. SERPER_API_KEY   -> https://serper.dev            (Google results)
#   4. SEARXNG_URL      -> your own SearXNG instance     (free, self-hosted)
#   5. DuckDuckGo HTML  -> no key, last resort (snippets only)
#
# The query is sent AS IS. (Older versions appended "(current as of DATE)" to the
# query which polluted results; freshness is now requested via provider params.)

_WS_NEWS_RE = None


def _ws_env(*names: str) -> str:
    import os
    for n in names:
        v = (os.getenv(n) or "").strip()
        if v:
            return v
    return ""


def _ws_is_newsy(query: str) -> bool:
    global _WS_NEWS_RE
    import re
    if _WS_NEWS_RE is None:
        _WS_NEWS_RE = re.compile(
            r"خبر|اخبار|امروز|دیشب|امشب|الان|اخیر|جدیدترین|آخرین|news|latest|today|breaking|"
            r"نتیجه|برنده|انتخابات|رونمایی|عرضه|release|launch",
            re.I,
        )
    return bool(_WS_NEWS_RE.search(query or ""))


def _ws_fmt(title: str, url: str, snippet: str = "", date: str = "") -> str:
    block = f"• {title}\n  {url}"
    if date:
        block += f"\n  تاریخ انتشار: {date}"
    if snippet:
        block += f"\n  خلاصه: {snippet}"
    return block


async def _ws_tavily(client, query: str, n: int, newsy: bool) -> list[str]:
    key = _ws_env("TAVILY_API_KEY")
    if not key:
        return []
    body = {
        "api_key": key,
        "query": query,
        "max_results": n,
        "search_depth": "advanced" if n >= 6 else "basic",
        "include_answer": False,
        "topic": "news" if newsy else "general",
    }
    if newsy:
        body["days"] = 14
    r = await client.post("https://api.tavily.com/search", json=body)
    r.raise_for_status()
    out = []
    for it in (r.json().get("results") or [])[:n]:
        text = (it.get("content") or "").strip().replace("\n", " ")
        out.append(_ws_fmt(
            it.get("title") or it.get("url") or "",
            it.get("url") or "",
            text[:600],
            str(it.get("published_date") or ""),
        ))
    return out


async def _ws_brave(client, query: str, n: int, newsy: bool) -> list[str]:
    key = _ws_env("BRAVE_API_KEY", "BRAVE_SEARCH_API_KEY")
    if not key:
        return []
    params = {"q": query, "count": n}
    if newsy:
        params["freshness"] = "pm"  # past month
    r = await client.get(
        "https://api.search.brave.com/res/v1/web/search",
        params=params,
        headers={"X-Subscription-Token": key, "Accept": "application/json"},
    )
    r.raise_for_status()
    out = []
    for it in ((r.json().get("web") or {}).get("results") or [])[:n]:
        desc = (it.get("description") or "").replace("<strong>", "").replace("</strong>", "")
        out.append(_ws_fmt(it.get("title") or "", it.get("url") or "", desc[:600], str(it.get("age") or "")))
    return out


async def _ws_serper(client, query: str, n: int, newsy: bool) -> list[str]:
    key = _ws_env("SERPER_API_KEY")
    if not key:
        return []
    body = {"q": query, "num": n, "hl": "fa"}
    if newsy:
        body["tbs"] = "qdr:m"
    r = await client.post(
        "https://google.serper.dev/search", json=body,
        headers={"X-API-KEY": key, "Content-Type": "application/json"},
    )
    r.raise_for_status()
    out = []
    for it in (r.json().get("organic") or [])[:n]:
        out.append(_ws_fmt(it.get("title") or "", it.get("link") or "", (it.get("snippet") or "")[:600], str(it.get("date") or "")))
    return out


async def _ws_searxng(client, query: str, n: int, newsy: bool) -> list[str]:
    base = _ws_env("SEARXNG_URL").rstrip("/")
    if not base:
        return []
    params = {"q": query, "format": "json", "language": "fa"}
    if newsy:
        params["time_range"] = "month"
    r = await client.get(f"{base}/search", params=params)
    r.raise_for_status()
    out = []
    for it in (r.json().get("results") or [])[:n]:
        out.append(_ws_fmt(it.get("title") or "", it.get("url") or "", (it.get("content") or "")[:600], str(it.get("publishedDate") or "")))
    return out


async def _ws_duckduckgo(client, query: str, n: int, newsy: bool) -> list[str]:
    from bs4 import BeautifulSoup

    data = {"q": query}
    if newsy:
        data["df"] = "m"  # last month
    r = await client.post(
        "https://html.duckduckgo.com/html/",
        data=data,
        headers={"User-Agent": "Mozilla/5.0 (compatible; RoozeZibaBot/1.0)"},
    )
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    out = []
    for node in soup.select(".result")[:n]:
        a = node.select_one("a.result__a")
        if not a:
            continue
        sn = node.select_one(".result__snippet")
        out.append(_ws_fmt(
            a.get_text(" ", strip=True),
            a.get("href") or "",
            sn.get_text(" ", strip=True) if sn else "",
        ))
    return out


async def web_search(query: str, max_results: int = 5) -> str:
    """Live web search with freshness metadata and bounded snippets.

    Never invents a result: if every provider fails the response starts with
    LIVE_DATA_UNAVAILABLE so the AI layer refuses to present stale model
    knowledge as current data.
    """
    from datetime import datetime, timezone

    query = (query or "").strip()
    if not query:
        return "LIVE_DATA_UNAVAILABLE: عبارت جستجو خالی است."
    max_results = max(1, min(int(max_results or 5), 10))
    date_tag = datetime.now(timezone.utc).date().isoformat()
    newsy = _ws_is_newsy(query)

    providers = (
        ("tavily", _ws_tavily),
        ("brave", _ws_brave),
        ("serper", _ws_serper),
        ("searxng", _ws_searxng),
        ("duckduckgo", _ws_duckduckgo),
    )
    try:
        import httpx
    except Exception as e:  # pragma: no cover
        logger.warning("web_search: httpx unavailable: %s", e)
        return "LIVE_DATA_UNAVAILABLE: جستجوی وب فعلاً در دسترس نیست؛ اطلاعات قدیمی را جایگزین نکن."

    last_error = None
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        for name, fn in providers:
            try:
                results = await fn(client, query, max_results, newsy)
            except Exception as e:
                last_error = e
                logger.warning("web_search provider %s failed: %s", name, e)
                continue
            if results:
                return (
                    f"LIVE_WEB_RESULTS (provider={name}, searched {date_tag} UTC) برای «{query}»:\n\n"
                    + "\n\n".join(results)
                    + "\n\nقانون پاسخ: فقط از همین نتایج استفاده کن، تاریخ/منبع را ذکر کن، "
                      "و اگر نتایج کافی یا مرتبط نیستند صریحاً بگو."
                )
    if last_error is not None:
        logger.warning("web_search: all providers failed, last error: %s", last_error)
        return "LIVE_DATA_UNAVAILABLE: جستجوی وب فعلاً در دسترس نیست؛ اطلاعات قدیمی را جایگزین نکن."
    return f"LIVE_DATA_UNAVAILABLE: برای «{query}» نتیجه قابل اتکایی پیدا نشد."
