# Auto-split part 8: _search
async def _search(query: str, domain: str = "", limit: int = 8, extra: str = "") -> list[dict[str, str]]:
    """جستجو در DuckDuckGo با امکان محدود کردن به دامنه یا عبارت اضافه."""
    parts = []
    if domain:
        parts.append(f"site:{domain}")
    parts.append(query)
    if extra:
        parts.append(extra)
    q = " ".join(parts)

    key = f"search:{q}:{limit}"
    now = time.time()
    cached = CACHE.get(key)
    if cached and now - cached[0] < CACHE_TTL:
        try:
            return json.loads(cached[1])
        except Exception:
            pass

    try:
        async with httpx.AsyncClient(
            timeout=20, follow_redirects=True, headers={"User-Agent": UA}
        ) as client:
            r = await client.post(SEARCH_URL, data={"q": q})
            r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        out = []
        for a in soup.select("a.result__a")[:limit]:
            href = a.get("href") or ""
            title = _clean_title(a.get_text(" ", strip=True))
            parent = a.find_parent("div", class_="result")
            snippet = ""
            if parent:
                sn = parent.select_one(".result__snippet")
                snippet = sn.get_text(" ", strip=True) if sn else ""
            if href and title:
                out.append({"url": href, "title": title, "snippet": snippet})
        CACHE[key] = (now, json.dumps(out, ensure_ascii=False))
        return out
    except Exception as exc:
        logger.debug("shopping search failed for %s: %s", q, exc)
        return []
