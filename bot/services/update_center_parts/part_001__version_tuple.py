# Auto-split part 1: _version_tuple
def _version_tuple(value: str) -> tuple[int, int, int]:
    m = _VERSION_RE.match(str(value or "").strip())
    if not m:
        return (0, 0, 0)
    return tuple(int(x) for x in m.groups())
