# Auto-split part 19: record_perf
def record_perf(component: str, latency_ms: float, ok: bool=True) -> None:
    _PERF[component].append((time.time(), float(latency_ms), bool(ok)))
    try:
        conn=_db(); conn.execute("INSERT INTO v75_metrics(component,operation,latency_ms,ok) VALUES(?,?,?,?)",(component,"runtime",float(latency_ms),1 if ok else 0)); conn.commit(); conn.close()
    except Exception: pass
