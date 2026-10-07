# Auto-split part 1: _clamp
def _clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, float(x)))
