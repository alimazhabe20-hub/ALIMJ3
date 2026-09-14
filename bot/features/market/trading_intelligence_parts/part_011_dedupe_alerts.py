# Auto-split part 11: dedupe_alerts
def dedupe_alerts(alerts, *, key="default", ttl_seconds=900, now=None):
    """Return only newly-seen alert flags for a bounded process-local window."""
    now = time.time() if now is None else float(now)
    store = getattr(dedupe_alerts, "_seen", {})
    previous = store.get(str(key), {})
    out = []
    for alert in list(alerts or []):
        stamp = float(previous.get(alert, 0.0))
        if now - stamp >= max(1, int(ttl_seconds)):
            out.append(alert)
            previous[alert] = now
    store[str(key)] = previous
    # Keep the structure bounded for long-running bots.
    if len(store) > 512:
        cutoff = now - max(1, int(ttl_seconds))
        for k in list(store):
            if all(float(v) < cutoff for v in store[k].values()):
                store.pop(k, None)
    dedupe_alerts._seen = store
    return out
