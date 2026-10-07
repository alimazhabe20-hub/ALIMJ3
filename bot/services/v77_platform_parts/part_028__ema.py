# Auto-split part 28: _ema
def _ema(vals: list[float], period: int) -> float|None:
    if not vals:return None
    p=max(1,min(period,len(vals))); a=2/(p+1); e=vals[0]
    for x in vals[1:]:e=a*x+(1-a)*e
    return e
