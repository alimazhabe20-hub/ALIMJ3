from typing import Iterable

# Auto-split part 30: correlation
def correlation(a: Iterable[float], b: Iterable[float]) -> float|None:
    x=_num(a); y=_num(b); n=min(len(x),len(y))
    if n<3:return None
    x=x[-n:];y=y[-n:];mx=sum(x)/n;my=sum(y)/n;dx=[z-mx for z in x];dy=[z-my for z in y];den=(sum(z*z for z in dx)*sum(z*z for z in dy))**.5
    return round(sum(dx[i]*dy[i] for i in range(n))/den,4) if den else 0.0
