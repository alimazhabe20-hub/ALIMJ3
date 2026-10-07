# Auto-split part 3: _normalize_instagram_url
def _normalize_instagram_url(url: str) -> str:
    """Strip tracking query params like the production ALIMJ3 normalizer."""
    p = urlparse((url or "").strip())
    host = (p.hostname or "").lower().rstrip(".")
    if host == "instagram.com" or host.endswith(".instagram.com"):
        return p._replace(query="").geturl()
    return url.strip()
