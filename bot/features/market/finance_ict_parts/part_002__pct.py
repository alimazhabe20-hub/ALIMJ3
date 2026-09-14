# Auto-split part 2: _pct
def _pct(a: float, b: float) -> float:
    if not b:
        return 0.0
    return abs(a - b) / abs(b) * 100.0
