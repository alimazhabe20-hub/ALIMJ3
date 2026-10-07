"""finance_ict: math responsibilities."""
from .finance_ict_common import *  # noqa: F401,F403
from . import finance_ict_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def _f(x, default: float = 0.0) -> float:
    try:
        v = float(x)
        if v != v:  # NaN
            return default
        return v
    except Exception:
        return default

def _pct(a: float, b: float) -> float:
    if not b:
        return 0.0
    return abs(a - b) / abs(b) * 100.0

def _atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> float | None:
    if len(closes) < period + 2:
        return None
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    if len(trs) < period:
        return None
    return sum(trs[-period:]) / period

def _body(o: float, c: float) -> float:
    return abs(c - o)

def _range(h: float, l: float) -> float:
    return max(h - l, 1e-12)

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

def _swing_strength(
    idx: int,
    price: float,
    highs: list[float],
    lows: list[float],
    mode: str,
    atr: float | None,
) -> float:
    """0–100 rough strength: range vs ATR + isolation."""
    left = max(0, idx - 5)
    right = min(len(highs), idx + 6)
    if mode == "high":
        span = price - min(lows[left:right])
    else:
        span = max(highs[left:right]) - price
    if atr and atr > 0:
        return max(0.0, min(100.0, (span / atr) * 35.0))
    return 50.0
