# Auto-split part 35: provider_event
def provider_event(provider: str, *, ok: bool, elapsed_ms: float) -> None:
    p=_PROVIDER[provider]; p["calls"]+=1; p["total_ms"]+=elapsed_ms
    if not ok: p["errors"]+=1
    if p["errors"] >= 4 and p["errors"] > p["calls"]*.5: p["cooldown_until"]=time.monotonic()+30
