# Auto-split part 8: _search
async def _search(query: str, domain: str = "", limit: int = 8, extra: str = "") -> list[dict[str, str]]:
    """جستجوی چندموتوره؛ اگر DuckDuckGo در Render در دسترس نبود، fallback می‌شود."""
    import html as _html
    from urllib.parse import parse_qs, urlsplit

    parts = []
    if domain:
        parts.append(f"site:{domain}")
    parts.append(query)
    if extra:
        parts.append(extra)
    q = " ".join(parts).strip()

    key = f"search:v3:{q}:{limit}"
    now = time.time()
    cached = CACHE.get(key)
    if cached and now - cached[0] < CACHE_TTL:
        try:
            return json.loads(cached[1])
        except Exception:
            pass

    async def _ddg(client):
        try:
            r = await client.post(SEARCH_URL, data={"q": q})
            if r.status_code >= 400:
                return []
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
            return out
        except Exception as exc:
            logger.debug("shopping DDG failed for %s: %s", q, exc)
            return []

    def _google_links(soup):
        out = []
        for a in soup.select("a"):
            href = a.get("href") or ""
            title = _clean_title(a.get_text(" ", strip=True))
            if not href.startswith("http") or not title:
                continue
            low = href.lower()
            if any(x in low for x in ("google.com", "googleusercontent.com", "gstatic.com")):
                continue
            out.append({"url": href, "title": title, "snippet": ""})
            if len(out) >= limit:
                break
        return out

    def _bing_links(soup):
        out = []
        for item in soup.select("li.b_algo")[:limit]:
            a = item.select_one("h2 a")
            if not a:
                continue
            href = a.get("href") or ""
            title = _clean_title(a.get_text(" ", strip=True))
            sn = item.select_one(".b_caption p")
            snippet = sn.get_text(" ", strip=True) if sn else ""
            if href and title:
                out.append({"url": href, "title": title, "snippet": snippet})
        return out

    def _brave_links(soup):
        out = []
        for a in soup.select("a"):
            href = a.get("href") or ""
            title = _clean_title(a.get_text(" ", strip=True))
            if not href.startswith("http") or not title:
                continue
            low = href.lower()
            if "search.brave.com" in low:
                continue
            out.append({"url": href, "title": title, "snippet": ""})
            if len(out) >= limit:
                break
        return out

    headers = {"User-Agent": UA, "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8"}
    try:
        async with httpx.AsyncClient(timeout=12, follow_redirects=True, headers=headers) as client:
            # DDG first: lowest overhead for the existing implementation.
            out = await _ddg(client)
            if not out:
                engines = [
                    ("google", f"https://www.google.com/search?hl=en&q={quote_plus(q)}", _google_links),
                    ("bing", f"https://www.bing.com/search?q={quote_plus(q)}", _bing_links),
                    ("brave", f"https://search.brave.com/search?q={quote_plus(q)}", _brave_links),
                ]
                for name, url, parser in engines:
                    try:
                        r = await client.get(url)
                        if r.status_code >= 400:
                            continue
                        out = parser(BeautifulSoup(r.text, "html.parser"))
                        if out:
                            logger.info("shopping search engine=%s query=%s results=%d", name, q, len(out))
                            break
                    except Exception as exc:
                        logger.debug("shopping %s failed for %s: %s", name, q, exc)

        CACHE[key] = (now, json.dumps(out[:limit], ensure_ascii=False))
        return out[:limit]
    except Exception as exc:
        logger.debug("shopping search failed for %s: %s", q, exc)
        return []
