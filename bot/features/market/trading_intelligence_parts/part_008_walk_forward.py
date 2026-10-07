# Auto-split part 8: walk_forward
def walk_forward(closes, scores, windows=(120, 60), threshold=60, horizon=6) -> dict:
    """Rolling out-of-sample evaluation; never trains on future candles."""
    train, test = windows
    results=[]; start=0
    while start + train + test + horizon < len(closes):
        a=start+train
        b=a+test
        bt=backtest_directional(closes[a:b+horizon], scores[a:b+horizon], threshold, horizon)
        results.append(bt); start += test
    if not results: return {"windows":0, "out_of_sample": {"trades":0}}
    trades=sum(x.get("trades",0) for x in results)
    wins=sum(x.get("wins",0) for x in results)
    return {"windows":len(results), "out_of_sample":{"trades":trades,
            "win_rate":round(100*wins/trades,2) if trades else 0,
            "avg_return_pct":round(mean([x.get("return_pct",0) for x in results]),2)}}
