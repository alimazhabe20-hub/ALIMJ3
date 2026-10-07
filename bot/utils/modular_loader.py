"""Tiny loader used by generated module fragments; preserves the original module namespace."""
from __future__ import annotations
from pathlib import Path
from types import ModuleType
from typing import MutableMapping

def load_modular_part(base_file: str, relative_part: str, namespace: MutableMapping[str, object] | None = None) -> None:
    ns = namespace if namespace is not None else __import__('inspect').currentframe().f_back.f_globals
    part = Path(base_file).resolve().parent / relative_part
    code = compile(part.read_text(encoding='utf-8'), str(part), 'exec')
    exec(code, ns, ns)
