from typing import Any

# Auto-split part 17: economic_surprise
def economic_surprise(actual: str, forecast: str) -> dict[str, Any]:
    def num(x):
        m=re.search(r"[-+]?\d+(?:\.\d+)?",str(x or "")); return float(m.group()) if m else None
    a,f=num(actual),num(forecast)
    if a is None or f is None: return {"available":False,"score":0,"direction":"unknown"}
    diff=a-f; scale=max(1,abs(f)); score=max(-1,min(1,diff/scale))
    return {"available":True,"difference":round(diff,6),"score":round(score,4),"direction":"above" if diff>0 else "below" if diff<0 else "inline"}
