# Auto-split part 24: provider_health
def provider_health(name: str, ok: bool, latency_ms: float=0.0, cost: float=0.0) -> None:
    p=_PROVIDERS.setdefault(name,{"capabilities":set(),"weight":1.0,"cost_per_1k":0.0,"failures":0,"successes":0,"latency_ms":0.0,"enabled":True})
    p["latency_ms"]=(p["latency_ms"]*.7)+float(latency_ms)*.3
    p["cost_per_1k"]=(p["cost_per_1k"]*.9)+max(0,float(cost))*.1
    if ok:p["successes"]+=1;p["failures"]=max(0,p["failures"]-1)
    else:p["failures"]+=1
    p["enabled"]=p["failures"]<5
