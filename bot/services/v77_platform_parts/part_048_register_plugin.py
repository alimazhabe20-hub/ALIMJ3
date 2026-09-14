from typing import Any
from typing import Callable
from typing import Iterable

# Auto-split part 48: register_plugin
def register_plugin(name: str, version: str, handler: Callable[...,Any], permissions: Iterable[str]=(), trusted: bool=False) -> dict[str,Any]:
    if not name or not callable(handler):return {"ok":False,"error":"invalid_plugin"}
    if not trusted:return {"ok":False,"error":"trust_required"}
    perms={str(x) for x in permissions if str(x) in {"read","network","files","market","admin"}}
    _PLUGINS[str(name)]={"version":str(version),"handler":handler,"permissions":perms,"trusted":True}
    return {"ok":True,"name":str(name),"version":str(version),"permissions":sorted(perms)}
