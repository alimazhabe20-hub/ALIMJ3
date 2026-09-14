# Auto-split part 45: record_success
def record_success(name: str) -> None:
    n=str(name);_FAILURES[n].clear();p=_CIRCUITS.setdefault(n,{"failures":0,"opened_until":0.0});p.update(failures=0,opened_until=0.0)
