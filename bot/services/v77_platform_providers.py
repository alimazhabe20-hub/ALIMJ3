"""v77_platform: providers responsibilities."""
from .v77_platform_common import *  # noqa: F401,F403
from . import v77_platform_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def register_provider(name: str, capabilities: Iterable[str]=(), weight: float=1.0, cost_per_1k: float=0.0) -> None:
    _PROVIDERS[str(name)]={"capabilities":set(capabilities),"weight":max(.1,float(weight)),"cost_per_1k":max(0,float(cost_per_1k)),"failures":0,"successes":0,"latency_ms":0.0,"enabled":True}

def provider_health(name: str, ok: bool, latency_ms: float=0.0, cost: float=0.0) -> None:
    p=_PROVIDERS.setdefault(name,{"capabilities":set(),"weight":1.0,"cost_per_1k":0.0,"failures":0,"successes":0,"latency_ms":0.0,"enabled":True})
    p["latency_ms"]=(p["latency_ms"]*.7)+float(latency_ms)*.3
    p["cost_per_1k"]=(p["cost_per_1k"]*.9)+max(0,float(cost))*.1
    if ok:p["successes"]+=1;p["failures"]=max(0,p["failures"]-1)
    else:p["failures"]+=1
    p["enabled"]=p["failures"]<5

def choose_provider(capability: str, *, max_cost: float|None=None) -> str|None:
    choices=[]
    for name,p in _PROVIDERS.items():
        if not p["enabled"] or capability not in p["capabilities"]: continue
        if max_cost is not None and p["cost_per_1k"]>max_cost: continue
        reliability=p["successes"]/(p["successes"]+p["failures"]+1)
        score=(p["latency_ms"]+1)/(p["weight"]*reliability)
        choices.append((score,name))
    return min(choices)[1] if choices else None

def provider_snapshot() -> dict[str,Any]:
    return {k:{kk:(sorted(vv) if isinstance(vv,set) else vv) for kk,vv in v.items()} for k,v in _PROVIDERS.items()}
