# Auto-split part 44: record_failure
def record_failure(name: str, threshold: int=5, cooldown: float=60) -> None:
    n=str(name);now=time.monotonic();q=_FAILURES[n];q.append(now);p=_CIRCUITS.setdefault(n,{"failures":0,"opened_until":0.0});p["failures"]=len(q)
    if len(q)>=threshold:p["opened_until"]=now+max(1,float(cooldown))
