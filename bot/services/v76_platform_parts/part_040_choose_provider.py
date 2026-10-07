# Auto-split part 40: choose_provider
def choose_provider(capability:str)->str|None:
    candidates=[(n,p) for n,p in _PROVIDERS.items() if p["enabled"] and capability in p["capabilities"]]
    if not candidates:return None
    return min(candidates,key=lambda x:(x[1]["failures"],x[1]["latency"]/max(x[1]["weight"],.1)))[0]
