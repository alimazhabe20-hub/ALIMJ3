from typing import Iterable

# Auto-split part 23: register_provider
def register_provider(name: str, capabilities: Iterable[str]=(), weight: float=1.0, cost_per_1k: float=0.0) -> None:
    _PROVIDERS[str(name)]={"capabilities":set(capabilities),"weight":max(.1,float(weight)),"cost_per_1k":max(0,float(cost_per_1k)),"failures":0,"successes":0,"latency_ms":0.0,"enabled":True}
