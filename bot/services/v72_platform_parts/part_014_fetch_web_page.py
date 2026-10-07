from typing import Any

# Auto-split part 14: fetch_web_page
async def fetch_web_page(url: str) -> dict[str, Any]:
    import httpx
    from bs4 import BeautifulSoup
    url = safe_web_url(url)
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ALIMJ3-WebIntel/1.0)", "Accept": "text/html,application/xhtml+xml"}
    async with httpx.AsyncClient(timeout=WEB_TIMEOUT, follow_redirects=False, headers=headers) as client:
        current = url
        for _ in range(4):
            current = safe_web_url(current)
            _assert_public_host(urlparse(current).hostname or "")
            r = await client.get(current)
            if r.status_code in {301,302,303,307,308}:
                loc = r.headers.get("location")
                if not loc: break
                current = urljoin(current, loc); continue
            if r.status_code >= 400:
                return {"url": current, "ok": False, "status": r.status_code, "text": ""}
            soup = BeautifulSoup(r.text, "html.parser")
            for tag in soup(["script", "style", "noscript"]): tag.decompose()
            title = (soup.title.get_text(" ", strip=True) if soup.title else "")[:300]
            text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))[:MAX_DOCUMENT_CHARS]
            return {"url": current, "ok": True, "status": r.status_code, "title": title, "text": text}
    return {"url": current, "ok": False, "status": 0, "text": ""}
