from typing import Any

# Auto-split part 35: performance_snapshot
def performance_snapshot() -> dict[str,Any]:
    try:
        c=_db(); rows=c.execute("SELECT latency_ms,ok FROM v77_perf ORDER BY id DESC LIMIT 1000").fetchall();c.close()
        lat=[float(r[0]) for r in rows];err=sum(not bool(r[1]) for r in rows)
    except Exception:lat=[];err=0
    return {"samples":len(lat),"avg_ms":round(sum(lat)/len(lat),2) if lat else 0,"p95_ms":round(sorted(lat)[max(0,int(len(lat)*.95)-1)],2) if lat else 0,"error_rate":round(err/len(lat),4) if lat else 0,"cache_items":len(_CACHE)}
