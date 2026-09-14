# Auto-split part 36: record_performance
def record_performance(component: str, latency_ms: float, ok: bool=True) -> None:
    try:
        c=_db();c.execute("INSERT INTO v77_perf(component,latency_ms,ok) VALUES(?,?,?)",(redact(component,160),float(latency_ms),int(ok)));c.commit();c.close()
    except Exception:pass
