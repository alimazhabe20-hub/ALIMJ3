# Auto-split part 42: rate_limit
def rate_limit(key: str, limit: int=30, window: float=60) -> bool:
    now=time.monotonic(); q=_RATE[str(key)]
    while q and now-q[0]>window:q.popleft()
    if len(q)>=max(1,int(limit)):return False
    q.append(now);return True
