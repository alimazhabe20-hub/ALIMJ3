"""Utility compatibility layer for the flattened deployment."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import sys

def load_modular_part(owner_file, relative_path):
    """Load an optional modular part without allowing it to crash startup."""
    owner = Path(owner_file).resolve()
    target = (owner.parent / relative_path).resolve()
    if not target.is_file():
        return None
    name = f"_alimj_part_{abs(hash(str(target)))}"
    try:
        spec = importlib.util.spec_from_file_location(name, str(target))
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None
