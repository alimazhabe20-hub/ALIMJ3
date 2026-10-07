# Auto-split part 17: _safe_member
def _safe_member(name: str) -> bool:
    p = Path(name)
    return not p.is_absolute() and ".." not in p.parts and not name.startswith(("/", "\\"))
