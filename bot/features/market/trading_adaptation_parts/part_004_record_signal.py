# Auto-split part 4: record_signal
def record_signal(symbol, direction, entry, stop=None, target=None, regime="", score=50,
                  confidence=50, factors=None, horizon_seconds=21600, setup="default",
                  model_version="58.0.0-adaptive-hardened") -> str:
    """Record a signal snapshot. It is settled later, never immediately."""
    try: entry=float(entry)
    except Exception: return ""
    if direction not in ("long", "short"): return ""
    d=_load()
    symbol_u = str(symbol).upper()
    setup_u = setup or "default"
    # Alert/signal deduplication: repeated analyses of the same setup in a short
    # window must not inflate the adaptive ledger or spam downstream alerts.
    now = time.time()
    for old in reversed(d.get("signals", [])[-80:]):
        if (old.get("symbol") == symbol_u and old.get("direction") == direction
                and old.get("regime") == (regime or "نامشخص")
                and old.get("setup") == setup_u
                and now - float(old.get("ts", 0)) < 1800):
            return str(old.get("id") or "")
    sid=uuid.uuid4().hex[:12]
    d["signals"].append({"id":sid,"ts":time.time(),"settle_after":time.time()+max(60,int(horizon_seconds or 21600)),
        "symbol":symbol_u,"direction":direction,"entry":entry,"stop":stop,"target":target,
        "regime":regime or "نامشخص","score":float(score),"confidence":float(confidence),
        "factors":{k:float(v) for k,v in (factors or {}).items() if isinstance(v,(int,float))},"setup":setup_u,"model_version":str(model_version or "58.0.0-adaptive-hardened")})
    d["signals"]=d["signals"][-500:]
    _save(d); return sid
