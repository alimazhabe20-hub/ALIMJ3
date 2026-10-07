# Auto-split part 8: _search
async def _search(query: str, domain: str = "", limit: int = 8, extra: str = "") -> list[dict[str, str]]:
    """جستجوی سریع چندموتوره؛ اولین منبع معتبر برگردانده می‌شود تا Shopping روی Render timeout نشود."""
    import asyncio
    from urllib.parse import quote_plus

    parts = []
    if domain:
        parts.append(f"site:{domain}")
    parts.append(query)
    if extra:
        parts.append(extra)
    q = " ".join(parts).strip()

    key = f"search:v4:{q}:{limit}"
    now = time.time()
    cached = CACHE.get(key)
    if cached and now - cached[0] < CACHE_TTL:
        try:
            return json.loads(cached[1])
        except Exception:
            pass

    headers = {"User-Agent": UA, "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8"}

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
            if "search.brave.com" in href.lower():
                continue
            out.append({"url": href, "title": title, "snippet": ""})
            if len(out) >= limit:
                break
        return out

    async def _one(client, name, method, url, parser, data=None):
        try:
            if method == "post":
                r = await asyncio.wait_for(client.post(url, data=data), timeout=5.5)
            else:
                r = await asyncio.wait_for(client.get(url), timeout=5.5)
            if r.status_code >= 400:
                return name, []
            return name, parser(BeautifulSoup(r.text, "html.parser"))
        except Exception as exc:
            logger.debug("shopping %s failed for %s: %s", name, q, exc)
            return name, []

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers=headers) as client:
            engines = [
                ("ddg", "post", SEARCH_URL, lambda soup: [
                    {"url": a.get("href") or "", "title": _clean_title(a.get_text(" ", strip=True)),
                     "snippet": (a.find_parent("div", class_="result").select_one(".result__snippet").get_text(" ", strip=True)
                                 if a.find_parent("div", class_="result") and a.find_parent("div", class_="result").select_one(".result__snippet") else "")}
                    for a in soup.select("a.result__a")[:limit]
                    if a.get("href") and a.get_text(" ", strip=True)
                ], {"q": q}),
                ("google", "get", f"https://www.google.com/search?hl=en&q={quote_plus(q)}", _google_links, None),
                ("bing", "get", f"https://www.bing.com/search?q={quote_plus(q)}", _bing_links, None),
                ("brave", "get", f"https://search.brave.com/search?q={quote_plus(q)}", _brave_links, None),
            ]
            tasks = [asyncio.create_task(_one(client, *e)) for e in engines]
            pending = set(tasks)
            out = []
            while pending:
                done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    try:
                        name, candidate = task.result()
                    except Exception:
                        continue
                    if candidate:
                        out = candidate[:limit]
                        logger.info("shopping search engine=%s query=%s results=%d", name, q, len(out))
                        for other in pending:
                            other.cancel()
                        await asyncio.gather(*pending, return_exceptions=True)
                        CACHE[key] = (now, json.dumps(out, ensure_ascii=False))
                        return out
            CACHE[key] = (now, json.dumps([], ensure_ascii=False))
            return []
    except Exception as exc:
        logger.debug("shopping search failed for %s: %s", q, exc)
        return []
