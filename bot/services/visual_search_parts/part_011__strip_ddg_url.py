# Auto-split part 11: _strip_ddg_url
def _strip_ddg_url(url: str) -> str:
    url = html.unescape(url or "").strip()
    if url.startswith("//"):
        url = "https:" + url
    try:
        parsed = urlparse(url)
        if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
            target = parse_qs(parsed.query).get("uddg", [""])[0]
            if target:
                return unquote(target)
    except Exception:
        pass
    return url
