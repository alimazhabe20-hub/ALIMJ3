from typing import Any
from typing import Iterable

# Auto-split part 18: market_advanced
def market_advanced(closes: Iterable[float]) -> dict[str,Any]:
    vals=[float(x) for x in closes if x is not None]
    if not vals: return {"trend":"unknown","volatility":0,"momentum":0,"confidence":0}
    momentum=(vals[-1]-vals[max(0,len(vals)-6)])/max(abs(vals[max(0,len(vals)-6)]),1e-9)
    mean=sum(vals)/len(vals); variance=sum((x-mean)**2 for x in vals)/len(vals); vol=(variance**0.5)/max(abs(mean),1e-9)
    trend="bullish" if momentum>0.01 else "bearish" if momentum<-0.01 else "neutral"
    return {"trend":trend,"momentum":round(momentum,5),"volatility":round(vol,5),"confidence":round(min(1,abs(momentum)*10+0.2),3),"regime":"high_vol" if vol>.03 else "normal"}
