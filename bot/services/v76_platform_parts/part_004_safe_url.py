# Auto-split part 4: safe_url
def safe_url(url: str, *, allow_http: bool = True) -> tuple[bool, str]:
    try:
        p = urlparse(str(url).strip())
        if p.scheme not in ({"http", "https"} if allow_http else {"https"}) or not p.hostname:
            return False, "scheme_or_host"
        host = p.hostname.lower().rstrip(".")
        if host in _PRIVATE_HOSTS or host.endswith(".local"):
            return False, "private_host"
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False, "private_ip"
        except ValueError:
            pass
        if p.username or p.password:
            return False, "userinfo_not_allowed"
        return True, p.geturl()[:4096]
    except Exception:
        return False, "invalid_url"
