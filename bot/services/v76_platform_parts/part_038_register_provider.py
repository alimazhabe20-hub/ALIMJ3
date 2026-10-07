from typing import Iterable

# Auto-split part 38: register_provider
def register_provider(name:str,capabilities:Iterable[str]=(),weight:float=1.0)->None:
    _PROVIDERS[name]={"capabilities":set(capabilities),"weight":float(weight),"failures":0,"latency":0.0,"enabled":True}
