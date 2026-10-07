"""v74_platform: providers responsibilities."""
from .v74_platform_common import *  # noqa: F401,F403
from . import v74_platform_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def provider_event(provider: str, *, ok: bool, elapsed_ms: float) -> None:
    p=_PROVIDER[provider]; p["calls"]+=1; p["total_ms"]+=elapsed_ms
    if not ok: p["errors"]+=1
    if p["errors"] >= 4 and p["errors"] > p["calls"]*.5: p["cooldown_until"]=time.monotonic()+30

def provider_available(provider: str) -> bool:
    return time.monotonic() >= float(_PROVIDER[provider].get("cooldown_until",0))

def provider_snapshot() -> dict[str, Any]:
    return {k:{"calls":int(v["calls"]),"errors":int(v["errors"]),"avg_ms":round(v["total_ms"]/max(1,v["calls"]),2),
               "available":provider_available(k)} for k,v in sorted(_PROVIDER.items())}

def set_readiness(name: str, ok: bool, detail: str = "") -> None:
    _RUNTIME["readiness"][name]={"ok":bool(ok),"detail":redact_secrets(detail)[:300],"updated_at":time.time()}
