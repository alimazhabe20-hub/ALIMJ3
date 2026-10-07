from typing import Any

# Auto-split part 20: economic_surprise
def economic_surprise(actual: Any, forecast: Any) -> dict[str,Any]:
    try: a=float(str(actual).replace('%','').replace(',','')); f=float(str(forecast).replace('%','').replace(',','')); delta=a-f
        # percent-free normalized surprise
    except Exception: return {"available":False,"score":0,"direction":"unknown"}
    scale=max(abs(f),1.0); score=delta/scale
    return {"available":True,"delta":round(delta,6),"score":round(score,4),"direction":"above" if delta>0 else "below" if delta<0 else "inline"}
