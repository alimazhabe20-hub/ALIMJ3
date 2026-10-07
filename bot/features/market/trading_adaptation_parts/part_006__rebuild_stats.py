# Auto-split part 6: _rebuild_stats
def _rebuild_stats(d):
    groups=defaultdict(list)
    for s in d.get("signals",[]):
        if s.get("result") in ("win","loss","flat"):
            groups[(s.get("symbol",""),s.get("regime",""),s.get("setup","default"))].append(float(s.get("return_pct",0)))
    stats={}
    for key, vals in groups.items():
        k="|".join(key); wins=sum(v>0 for v in vals)
        stats[k]={"samples":len(vals),"win_rate":round(100*wins/len(vals),2),"avg_return":round(mean(vals),4)}
    d["stats"]=stats
