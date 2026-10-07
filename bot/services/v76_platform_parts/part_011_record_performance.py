# Auto-split part 11: record_performance
def record_performance(component: str, latency_ms: float, ok: bool=True) -> None:
    _PERF.append({"component":component,"latency_ms":round(float(latency_ms),2),"ok":bool(ok),"ts":time.time()})
    try:
        c=_db(); c.execute("INSERT INTO v76_perf(component,latency_ms,ok) VALUES(?,?,?)",(component,float(latency_ms),int(ok))); c.commit(); c.close()
    except Exception: pass
