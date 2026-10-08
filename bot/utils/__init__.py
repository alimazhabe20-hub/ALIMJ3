

# Compatibility loader kept inside the existing package so no new module file is required.
from pathlib import Path as _Path
from types import ModuleType as _ModuleType
import sys as _sys
import inspect as _inspect

def _load_modular_part(base_file, relative_part, namespace=None):
    ns = namespace if namespace is not None else _inspect.currentframe().f_back.f_globals
    part = _Path(base_file).resolve().parent / relative_part
    if not part.exists():
        # Parts are merged into their existing host files in this flattened release.
        return None
    exec(compile(part.read_text(encoding="utf-8"), str(part), "exec"), ns, ns)

_modular_loader = _ModuleType("bot.utils.modular_loader")
_modular_loader.load_modular_part = _load_modular_part
_sys.modules.setdefault("bot.utils.modular_loader", _modular_loader)
load_modular_part = _load_modular_part
