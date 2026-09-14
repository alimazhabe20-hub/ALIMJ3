# Auto-split part 5: settle_signals
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
