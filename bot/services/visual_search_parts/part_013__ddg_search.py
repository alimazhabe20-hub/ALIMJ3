from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from bot.services.visual_search import MAX_RESULTS_PER_QUERY
if TYPE_CHECKING:
    from bot.services.visual_search import SearchResult

# Auto-split part 13: _ddg_search
async def _ddg_search(query: str, limit: int = MAX_RESULTS_PER_QUERY) -> list[SearchResult]:
    url = "https://html.duckduckgo.com/html/"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ALIMJ-VisualLens/2.0; +https://example.com)",
        "Accept-Language": "fa,en;q=0.8",
    }
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True, headers=headers) as client:
            response = await client.get(url, params={"q": query, "kl": SEARCH_REGION})
            response.raise_for_status()
        body = response.text
    except Exception:
        return []

    results: list[SearchResult] = []
    # DuckDuckGo HTML markup is intentionally parsed conservatively.
    pattern = re.compile(
        r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>(.*?)(?=<div class="result|$)',
        re.I | re.S,
    )
    for match in pattern.finditer(body):
        raw_url, raw_title, tail = match.groups()
        title = _clean_html(raw_title)
        link = _strip_ddg_url(raw_url)
        snippet_match = re.search(r'class="result__snippet"[^>]*>(.*?)</(?:a|div)>', tail, re.I | re.S)
        snippet = _clean_html(snippet_match.group(1)) if snippet_match else ""
        if title and link.startswith(("http://", "https://")):
            results.append(SearchResult(title=title, url=link, snippet=snippet, matched_query=query))
        if len(results) >= limit:
            break
    return results
