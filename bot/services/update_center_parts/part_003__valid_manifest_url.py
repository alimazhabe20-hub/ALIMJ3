# Auto-split part 3: _valid_manifest_url
def _valid_manifest_url(url: str) -> bool:
    try:
        p = urlparse(url)
        host = p.hostname
        if p.scheme != "https" or not host or p.username or p.password or p.port not in (None, 443):
            return False
        if not _is_public_ip(host):
            return False
        # Resolve hostnames before connecting to reject private/link-local DNS answers.
        infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        return bool(infos) and all(_is_public_ip(item[4][0]) for item in infos)
    except Exception:
        return False
