# Auto-split part 6: _swings
def _swings(
    highs: list[float],
    lows: list[float],
    left: int = 3,
    right: int = 3,
) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
    """Confirmed fractal swings (need `right` bars after pivot)."""
    sh: list[tuple[int, float]] = []
    sl: list[tuple[int, float]] = []
    n = len(highs)
    if n < left + right + 1:
        return sh, sl
    for i in range(left, n - right):
        h_win = highs[i - left : i + right + 1]
        l_win = lows[i - left : i + right + 1]
        if highs[i] >= max(h_win) - 1e-12:
            # unique peak in window
            if list(h_win).count(highs[i]) == 1 or highs[i] == max(h_win):
                sh.append((i, highs[i]))
        if lows[i] <= min(l_win) + 1e-12:
            if list(l_win).count(lows[i]) == 1 or lows[i] == min(l_win):
                sl.append((i, lows[i]))
    return sh, sl
