# Auto-split part 2: _sma
def _sma(arr: list, n: int):
    if len(arr) < n:
        return None
    return sum(arr[-n:]) / n
