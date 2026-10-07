from typing import Any
from typing import Callable
from typing import Iterable

# Auto-split part 36: register_plugin
def register_plugin(name:str,version:str,handler:Callable[...,Any],permissions:Iterable[str]=())->None:
    if name and callable(handler):_PLUGINS[name]={"version":version,"handler":handler,"permissions":set(permissions)}
