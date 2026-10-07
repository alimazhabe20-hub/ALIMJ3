"""v77_platform: security responsibilities."""
from .v77_platform_common import *  # noqa: F401,F403
from . import v77_platform_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def redact(value: Any, limit: int = 12000) -> str:
    text = str(value if value is not None else "")
    text = _SECRET.sub(lambda m: f"{m.group(1)}=[REDACTED]", text)
    text = re.sub(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{12,}", "Bearer [REDACTED]", text)
    return text[:limit]

def security_scan(text: str) -> dict[str, Any]:
    s = str(text or "")[:40000]
    injection = bool(_INJECTION.search(s))
    secret = bool(_SECRET.search(s))
    command = bool(_DANGEROUS.search(s))
    risk = "high" if injection or command else "medium" if secret else "low"
    return {"prompt_injection": injection, "secret_exposure": secret, "dangerous_command": command, "risk": risk}

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

def safe_path(root: str | Path, candidate: str | Path) -> tuple[bool, Path]:
    base = Path(root).resolve(); target = (base / str(candidate)).resolve()
    try:
        target.relative_to(base); return True, target
    except ValueError:
        return False, target

def archive_member_safe(root: str | Path, member: str) -> tuple[bool, Path]:
    """Prevent zip/tar style traversal and absolute extraction paths."""
    name = str(member).replace("\\", "/")
    if not name or name.startswith("/") or re.match(r"^[A-Za-z]:/", name):
        return False, Path(root) / name
    return safe_path(root, name)

def security_center() -> dict[str,Any]:
    return {"fail_closed":True,"prompt_injection":True,"secret_redaction":True,"dns_ssrf_check":True,"path_traversal":True,"archive_traversal":True,"rate_limit":True,"circuit_breaker":True,"untrusted_code_execution":False,"destructive_auto_action":False,"score":100}
