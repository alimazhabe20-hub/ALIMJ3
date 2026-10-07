from typing import Any

# Auto-split part 20: performance_snapshot
def performance_snapshot() -> dict[str, Any]:
    out={}
    for name, rows in _PERF.items():
        vals=[r[1] for r in rows]; out[name]={"count":len(rows),"avg_ms":round(sum(vals)/len(vals),2) if vals else 0,"p95_ms":round(sorted(vals)[max(0,int(len(vals)*.95)-1)],2) if vals else 0,"errors":sum(not r[2] for r in rows)}
    return out
