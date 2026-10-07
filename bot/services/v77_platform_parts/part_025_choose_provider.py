# Auto-split part 25: choose_provider
def choose_provider(capability: str, *, max_cost: float|None=None) -> str|None:
    choices=[]
    for name,p in _PROVIDERS.items():
        if not p["enabled"] or capability not in p["capabilities"]: continue
        if max_cost is not None and p["cost_per_1k"]>max_cost: continue
        reliability=p["successes"]/(p["successes"]+p["failures"]+1)
        score=(p["latency_ms"]+1)/(p["weight"]*reliability)
        choices.append((score,name))
    return min(choices)[1] if choices else None
