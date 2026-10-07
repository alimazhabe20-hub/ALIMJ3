# Auto-split part 38: set_readiness
def set_readiness(name: str, ok: bool, detail: str = "") -> None:
    _RUNTIME["readiness"][name]={"ok":bool(ok),"detail":redact_secrets(detail)[:300],"updated_at":time.time()}
