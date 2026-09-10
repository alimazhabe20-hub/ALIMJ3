"""Persistent adaptive intelligence for the market-analysis engine.

This module learns only from recorded, settled signals. It never fabricates
outcomes and keeps an auditable JSON ledger with bounded size.
"""
from __future__ import annotations
import json, os, time, uuid, math
from collections import defaultdict
from statistics import mean

_DEFAULT = {"version": 1, "signals": [], "weights": {}, "stats": {}}


def _path():
    root = os.getenv("ALIMJ_DATA_DIR") or os.path.join(os.getcwd(), "data")
    os.makedirs(root, exist_ok=True)
    return os.path.join(root, "trading_adaptation.json")


def _load():
    try:
        with open(_path(), "r", encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict):
            d.setdefault("signals", []); d.setdefault("weights", {}); d.setdefault("stats", {})
            return d
    except Exception:
        pass
    return dict(_DEFAULT)


def _save(d):
    p = _path(); tmp = p + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp, p)
    except Exception:
        try:
            if os.path.exists(tmp): os.remove(tmp)
        except Exception: pass


def record_signal(symbol, direction, entry, stop=None, target=None, regime="", score=50,
                  confidence=50, factors=None, horizon_seconds=21600, setup="default") -> str:
    """Record a signal snapshot. It is settled later, never immediately."""
    try: entry=float(entry)
    except Exception: return ""
    if direction not in ("long", "short"): return ""
    d=_load(); sid=uuid.uuid4().hex[:12]
    d["signals"].append({"id":sid,"ts":time.time(),"settle_after":time.time()+max(60,int(horizon_seconds or 21600)),
        "symbol":str(symbol).upper(),"direction":direction,"entry":entry,"stop":stop,"target":target,
        "regime":regime or "نامشخص","score":float(score),"confidence":float(confidence),
        "factors":{k:float(v) for k,v in (factors or {}).items() if isinstance(v,(int,float))},"setup":setup or "default"})
    d["signals"]=d["signals"][-500:]
    _save(d); return sid


def settle_signals(symbol, current_price, now=None):
    """Settle due signals for symbol using only the later observed price."""
    try: price=float(current_price)
    except Exception: return 0
    now=time.time() if now is None else float(now); d=_load(); changed=0
    for s in d["signals"]:
        if s.get("result") or s.get("symbol") != str(symbol).upper() or now < float(s.get("settle_after", 0)): continue
        ret=(price/float(s["entry"])-1)*100 if s.get("entry") else 0
        if s.get("direction")=="short": ret=-ret
        s["exit"]=price; s["return_pct"]=round(ret,4); s["win"]=ret>0; s["result"]="win" if ret>0 else "loss" if ret<0 else "flat"
        s["settled_ts"]=now; changed+=1
    if changed:
        _rebuild_stats(d); _save(d)
    return changed


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


def adaptive_profile(symbol, regime="", setup="default", min_samples=12) -> dict:
    d=_load(); key=f"{str(symbol).upper()}|{regime or 'نامشخص'}|{setup or 'default'}"
    st=d.get("stats",{}).get(key,{}); n=int(st.get("samples",0))
    return {"samples":n,"win_rate":st.get("win_rate"),"avg_return":st.get("avg_return"),
            "ready":n>=min_samples,"kill": n>=20 and float(st.get("win_rate",50))<35}


def adaptive_weights(base_weights, symbol, regime="", setup="default") -> dict:
    """Small, bounded empirical adjustment; never lets learning dominate."""
    w={k:float(v) for k,v in (base_weights or {}).items()}; p=adaptive_profile(symbol,regime,setup)
    if not p["ready"]: return w
    # Factor attribution from settled trades: reward factors aligned with winners.
    d=_load(); rows=[s for s in d.get("signals",[]) if s.get("result") in ("win","loss") and s.get("symbol")==str(symbol).upper() and s.get("regime")==regime]
    if len(rows)<12:return w
    delta=defaultdict(float)
    for s in rows[-80:]:
        sign=1 if s.get("result")=="win" else -1
        for k,v in (s.get("factors") or {}).items():
            centered=(float(v)-50)/50
            delta[k]+=sign*centered
    for k in w:
        adj=max(-0.20,min(0.20,delta.get(k,0)/max(20,len(rows))))
        w[k]*=(1+adj)
    total=sum(w.values()) or 1
    return {k:v/total for k,v in w.items()}


def adapt_score(score, confidence, symbol, regime="", setup="default"):
    p=adaptive_profile(symbol,regime,setup); s=float(score); c=float(confidence)
    if p["samples"]>=12 and p.get("win_rate") is not None:
        empirical=float(p["win_rate"]); alpha=min(.25,p["samples"]/200)
        c=(1-alpha)*c+alpha*empirical
        if empirical<40: s=50+(s-50)*.75
        elif empirical>65: s=50+(s-50)*1.08
    return round(max(0,min(100,s)),1), round(max(0,min(100,c)),1), p


def kill_switch(profile, gate_allowed=True) -> tuple[bool,str]:
    if not gate_allowed: return True,"گیت کیفیت فعال است"
    if profile.get("kill"): return True,"عملکرد تاریخی این ستاپ در این رژیم ضعیف است"
    return False,""


def performance_summary(symbol=None) -> dict:
    d=_load(); rows=[s for s in d.get("signals",[]) if s.get("result") in ("win","loss","flat")]
    if symbol: rows=[s for s in rows if s.get("symbol")==str(symbol).upper()]
    wins=sum(s.get("result")=="win" for s in rows); rets=[float(s.get("return_pct",0)) for s in rows]
    return {"samples":len(rows),"win_rate":round(100*wins/len(rows),2) if rows else 0,
            "avg_return":round(mean(rets),4) if rets else 0,
            "max_drawdown":round(_max_dd(rets),4) if rets else 0}


def _max_dd(returns):
    eq=1.; peak=1.; maxdd=0.
    for r in returns:
        eq*=1+r/100; peak=max(peak,eq); maxdd=min(maxdd,(eq/peak-1)*100)
    return maxdd
