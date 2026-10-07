from typing import Any
from typing import Iterable

# Auto-split part 29: market_intelligence_3
def market_intelligence_3(closes: Iterable[float], volumes: Iterable[float]|None=None) -> dict[str,Any]:
    v=_num(closes); vol=_num(volumes or []); result={"samples":len(v),"trend":"unknown","regime":"unknown","momentum":0.0,"volatility":0.0,"rsi":None,"ema_fast":None,"ema_slow":None,"volume_trend":"unknown","confidence":0.0}
    if not v:return result
    result["ema_fast"]=_ema(v,12); result["ema_slow"]=_ema(v,26)
    base=v[max(0,len(v)-6)]; result["momentum"]=round((v[-1]-base)/abs(base),6) if base else 0
    rets=[(v[i]-v[i-1])/v[i-1] for i in range(1,len(v)) if v[i-1]]
    result["volatility"]=round(statistics.pstdev(rets),6) if len(rets)>1 else 0.0
    gains=[max(0,x) for x in rets[-14:]]; losses=[max(0,-x) for x in rets[-14:]]; avg_gain=sum(gains)/max(1,len(gains)); avg_loss=sum(losses)/max(1,len(losses))
    result["rsi"]=round(100-(100/(1+avg_gain/max(avg_loss,1e-12))),2) if rets else None
    if result["ema_fast"] and result["ema_slow"]:
        if result["ema_fast"] > result["ema_slow"] and result["momentum"] > 0.005:
            result["trend"] = "bullish"
        elif result["ema_fast"] < result["ema_slow"] and result["momentum"] < -0.005:
            result["trend"] = "bearish"
        elif result["momentum"] > 0.02:
            result["trend"] = "bullish"
        elif result["momentum"] < -0.02:
            result["trend"] = "bearish"
        else:
            result["trend"] = "neutral"
    result["regime"]="high_volatility" if result["volatility"]>.03 else "normal"
    if len(vol)>=4: result["volume_trend"]="rising" if sum(vol[-3:])/3>sum(vol[-6:-3])/3 else "falling"
    result["confidence"]=round(min(1,.25+abs(result["momentum"])*8+(0.15 if result["trend"]!="neutral" else 0)),3)
    return result
