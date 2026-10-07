# Auto-split part 2: safe_public_url
def safe_public_url(url: str, *, allow_http: bool = True) -> tuple[bool, str]:
    """Reject malformed URLs and SSRF-sensitive destinations."""
    raw = (url or "").strip()
    if not raw or len(raw) > 2048:
        return False, "invalid_url"
    try:
        p = urllib.parse.urlsplit(raw)
    except Exception:
        return False, "invalid_url"
    schemes = {"https", "http"} if allow_http else {"https"}
    if p.scheme.lower() not in schemes or not p.hostname or p.username or p.password:
        return False, "unsafe_scheme_or_credentials"
    host = p.hostname.rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain", "metadata.google.internal"}:
        return False, "private_host"
    try:
        infos = socket.getaddrinfo(host, p.port or (443 if p.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except OSError:
        return False, "dns_failed"
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            return False, "private_host"
    return True, "ok"
