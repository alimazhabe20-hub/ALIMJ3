# Auto-split part 8: adaptive_weights
def adaptive_weights(base_weights, symbol, regime="", setup="default") -> dict:
    """Small, bounded empirical adjustment; never lets learning dominate."""
    w={k:float(v) for k,v in (base_weights or {}).items()}; p=adaptive_profile(symbol,regime,setup)
    if not p["ready"]: return w
    # Factor attribution from settled trades: reward factors aligned with winners.
    d=_load(); rows=[s for s in d.get("signals",[]) if s.get("result") in ("win","loss") and s.get("symbol")==str(symbol).upper() and s.get("regime")==regime]
    if len(rows)<12:return w
    delta=defaultdict(float)
    for s in rows[-80:]:
        sign=1 if s.get("result")=="win" else -1
        for k,v in (s.get("factors") or {}).items():
            centered=(float(v)-50)/50
            delta[k]+=sign*centered
    for k in w:
        adj=max(-0.20,min(0.20,delta.get(k,0)/max(20,len(rows))))
        w[k]*=(1+adj)
    total=sum(w.values()) or 1
    return {k:v/total for k,v in w.items()}
