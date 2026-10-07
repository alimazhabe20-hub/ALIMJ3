"""v77_platform: market responsibilities."""
from .v77_platform_common import *  # noqa: F401,F403
from . import v77_platform_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def _num(values: Iterable[Any]) -> list[float]:
    out=[]
    for x in values:
        try: out.append(float(x))
        except (TypeError,ValueError): pass
    return out

def _ema(vals: list[float], period: int) -> float|None:
    if not vals:return None
    p=max(1,min(period,len(vals))); a=2/(p+1); e=vals[0]
    for x in vals[1:]:e=a*x+(1-a)*e
    return e

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

def correlation(a: Iterable[float], b: Iterable[float]) -> float|None:
    x=_num(a); y=_num(b); n=min(len(x),len(y))
    if n<3:return None
    x=x[-n:];y=y[-n:];mx=sum(x)/n;my=sum(y)/n;dx=[z-mx for z in x];dy=[z-my for z in y];den=(sum(z*z for z in dx)*sum(z*z for z in dy))**.5
    return round(sum(dx[i]*dy[i] for i in range(n))/den,4) if den else 0.0

def news_fusion(items: Iterable[dict[str,Any]]) -> list[dict[str,Any]]:
    groups: dict[str,list[dict[str,Any]]]={}
    for raw in items:
        x=dict(raw); title=re.sub(r"\W+"," ",str(x.get("title","")).lower()).strip(); words=set(title.split()); key=" ".join(sorted(words))[:220] or hashlib.sha1(str(x).encode()).hexdigest()[:12]
        groups.setdefault(key,[]).append(x)
    out=[]
    for key,group in groups.items():
        text=" ".join(str(x.get("title","")).lower()+" "+str(x.get("content","")).lower() for x in group); pos=sum(w in text for w in _POS); neg=sum(w in text for w in _NEG); sentiment="positive" if pos>neg else "negative" if neg>pos else "neutral"
        out.append({"canonical_key":key,"title":group[0].get("title",key),"sources":len(group),"items":group,"sentiment":sentiment,"impact":round(max([float(x.get("impact",0) or 0) for x in group]+[0]),3),"confidence":round(min(1,.35+.12*len(group)),3)})
    return sorted(out,key=lambda x:(-x["impact"],-x["sources"]))

def economic_surprise(actual: Any, forecast: Any) -> dict[str,Any]:
    try:a=float(str(actual).replace("%","").replace(",",""));f=float(str(forecast).replace("%","").replace(",",""))
    except (TypeError,ValueError):return {"available":False,"score":0,"direction":"unknown"}
    delta=a-f; score=delta/max(abs(f),1.0)
    return {"available":True,"actual":a,"forecast":f,"delta":round(delta,6),"score":round(score,4),"direction":"above" if delta>0 else "below" if delta<0 else "inline"}
