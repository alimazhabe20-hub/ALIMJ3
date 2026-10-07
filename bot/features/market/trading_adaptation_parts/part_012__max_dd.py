# Auto-split part 12: _max_dd
def _max_dd(returns):
    eq=1.; peak=1.; maxdd=0.
    for r in returns:
        eq*=1+r/100; peak=max(peak,eq); maxdd=min(maxdd,(eq/peak-1)*100)
    return maxdd
