# Auto-split part 11: performance_summary
def performance_summary(symbol=None) -> dict:
    d=_load(); rows=[s for s in d.get("signals",[]) if s.get("result") in ("win","loss","flat")]
    if symbol: rows=[s for s in rows if s.get("symbol")==str(symbol).upper()]
    wins=sum(s.get("result")=="win" for s in rows); rets=[float(s.get("return_pct",0)) for s in rows]
    return {"samples":len(rows),"win_rate":round(100*wins/len(rows),2) if rows else 0,
            "avg_return":round(mean(rets),4) if rets else 0,
            "max_drawdown":round(_max_dd(rets),4) if rets else 0}
