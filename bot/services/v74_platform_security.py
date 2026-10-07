"""v74_platform: security responsibilities."""
from .v74_platform_common import *  # noqa: F401,F403
from . import v74_platform_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def redact_secrets(value: Any) -> str:
    text = str(value if value is not None else "")
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(
            lambda m: (m.group(1) + "=[REDACTED]") if m.lastindex == 2 else "[REDACTED]",
            text,
        )
    return text[:5000]

def detect_prompt_injection(text: str) -> dict[str, Any]:
    sample = (text or "")[:12000]
    hits = [p for p in _PROMPT_INJECTION_PATTERNS if re.search(p, sample, re.I)]
    return {"detected": bool(hits), "count": len(hits), "severity": "high" if len(hits) >= 2 else "medium" if hits else "none"}

def safe_public_url(url: str, *, allow_http: bool = True) -> tuple[bool, str]:
    raw = (url or "").strip()
    if not raw or len(raw) > 2048:
        return False, "invalid_url"
    try:
        p = urllib.parse.urlsplit(raw)
    except Exception:
        return False, "invalid_url"
    allowed = {"https", "http"} if allow_http else {"https"}
    if p.scheme.lower() not in allowed or not p.hostname or p.username or p.password:
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

def safe_archive_member(name: str) -> bool:
    n = (name or "").replace("\\", "/")
    if not n or n.startswith("/") or re.match(r"^[A-Za-z]:", n):
        return False
    return ".." not in [p for p in n.split("/") if p]

def safe_path(path: str | Path, root: str | Path) -> bool:
    try:
        p, r = Path(path).resolve(), Path(root).resolve()
        return p == r or r in p.parents
    except Exception:
        return False

def sanitize_untrusted_text(text: str, max_chars: int = 12000) -> str:
    """Keep external text bounded and explicitly mark it as untrusted context."""
    clean = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", str(text or ""))
    return "[UNTRUSTED_EXTERNAL_CONTENT]\n" + redact_secrets(clean)[:max_chars]

class ToolPolicy:
    name: str
    version: str = "1.0"
    risk: str = "read"
    network: bool = False
    timeout: float = 25.0
    retries: int = TOOL_RETRIES
    cache_ttl: int = 0
    dependencies: tuple[str, ...] = ()
    enabled: bool = True
    schema_validated: bool = True
    owner: str = "core"

def register_tool_policy(name: str, **kwargs: Any) -> ToolPolicy:
    policy = ToolPolicy(name=name, **{k: v for k, v in kwargs.items() if k in ToolPolicy.__dataclass_fields__})
    _TOOL_POLICIES[name] = policy
    return policy

def tool_policy_snapshot() -> dict[str, Any]:
    now = time.monotonic()
    return {
        name: {
            "version": p.version, "risk": p.risk, "network": p.network,
            "timeout": p.timeout, "retries": p.retries, "cache_ttl": p.cache_ttl,
            "dependencies": list(p.dependencies), "enabled": p.enabled,
            "cooldown": round(max(0.0, _TOOL_DISABLED_UNTIL.get(name, 0) - now), 1),
        }
        for name, p in sorted(_TOOL_POLICIES.items())
    }

def tool_allowed(name: str, *, source: str = "system", approved: bool = False) -> tuple[bool, str]:
    p = _TOOL_POLICIES.get(name)
    if p and not p.enabled:
        return False, "disabled"
    if p and time.monotonic() < _TOOL_DISABLED_UNTIL.get(name, 0):
        return False, "cooldown"
    if p and p.risk in {"write", "admin"} and source in {"agent", "agent_repair"} and not approved:
        return False, "approval_required"
    return True, "ok"
