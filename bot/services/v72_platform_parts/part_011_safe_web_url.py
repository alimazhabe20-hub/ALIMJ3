# Auto-split part 11: safe_web_url
def safe_web_url(url: str) -> str:
    p = urlparse((url or "").strip())
    if p.scheme not in {"http", "https"} or not p.hostname or p.username or p.password:
        raise ValueError("invalid_url")
    host = p.hostname.rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain", "metadata.google.internal"}:
        raise ValueError("blocked_host")
    # Syntax validation is deliberately DNS-free so pure validation/caching does not
    # depend on the host network. The actual fetch path resolves and validates every
    # redirect target immediately before connecting.
    return p.geturl()
