from typing import Any

# Auto-split part 32: economic_surprise
def economic_surprise(actual: Any, forecast: Any) -> dict[str,Any]:
    try:a=float(str(actual).replace("%","").replace(",",""));f=float(str(forecast).replace("%","").replace(",",""))
    except (TypeError,ValueError):return {"available":False,"score":0,"direction":"unknown"}
    delta=a-f; score=delta/max(abs(f),1.0)
    return {"available":True,"actual":a,"forecast":f,"delta":round(delta,6),"score":round(score,4),"direction":"above" if delta>0 else "below" if delta<0 else "inline"}
