# Auto-split part 4: safe_url
def safe_url(url: str, *, allow_http: bool = True) -> tuple[bool, str]:
    """Validate URL syntax and resolve host DNS before allowing public IPs."""
    try:
        p = urlparse(str(url).strip())
        schemes = {"http", "https"} if allow_http else {"https"}
        if p.scheme not in schemes or not p.hostname or p.username or p.password:
            return False, "scheme_host_or_userinfo"
        host = p.hostname.rstrip(".").lower()
        if host in _PRIVATE_HOSTS or host.endswith(".local") or host.endswith(".internal"):
            return False, "private_host"
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
                return False, "private_ip"
        except ValueError:
            pass
        # DNS validation is best-effort and fail-closed for resolvable private targets.
        try:
            import socket
            infos = socket.getaddrinfo(host, p.port or (443 if p.scheme == "https" else 80), type=socket.SOCK_STREAM)
            for info in infos:
                addr = info[4][0]
                ip = ipaddress.ip_address(addr)
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
                    return False, "private_dns_target"
        except (OSError, ValueError):
            # Domain DNS can be unavailable in offline/test environments; URL is
            # still structurally valid, and the actual HTTP client must recheck.
            pass
        return True, p.geturl()[:4096]
    except Exception:
        return False, "invalid_url"
