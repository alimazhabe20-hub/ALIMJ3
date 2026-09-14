from typing import Any

# Auto-split part 12: observability
def observability() -> dict[str,Any]:
    vals=list(_PERF); lat=[x["latency_ms"] for x in vals]
    return {"version":VERSION,"samples":len(vals),"error_rate":round(sum(not x["ok"] for x in vals)/len(vals),3) if vals else 0,"avg_latency_ms":round(sum(lat)/len(lat),2) if lat else 0,"slow_requests":sum(x["latency_ms"]>2000 for x in vals),"components":sorted({x["component"] for x in vals})}
