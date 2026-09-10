"""Advanced trading intelligence: backtesting, regime, risk, calibration and alerts.
Pure helpers are intentionally dependency-free so they can be unit-tested offline.
"""
from __future__ import annotations
import math
from statistics import mean


def _clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, float(x)))


def detect_regime(ta=None, mtf=None, vol_ratio=None, closes=None) -> dict:
    ta, mtf = ta or {}, mtf or {}
    adx = float(ta.get("adx") or 0)
    vr = float(vol_ratio or ta.get("vol_ratio") or 1)
    bias = float(mtf.get("bias") or 0)
    chg = float(ta.get("chg_24h_bar") or 0)
    if adx < 18:
        label = "رنج"
    elif vr >= 1.8 and abs(chg) >= 2:
        label = "نوسان شدید"
    elif bias >= .35:
        label = "روند صعودی"
    elif bias <= -.35:
        label = "روند نزولی"
    elif adx >= 25:
        label = "روند خنثی/انتقالی"
    else:
        label = "نوسان کم"
    return {"label": label, "adx": adx, "vol_ratio": vr, "bias": bias, "high_vol": vr >= 1.8}


def dynamic_weights(regime: dict | None = None) -> dict:
    r = (regime or {}).get("label", "")
    w = {"trend": .18, "momentum": .12, "volume": .10, "structure": .14,
         "derivatives": .12, "sentiment": .08, "macro": .08, "market": .10, "onchain": .08}
    if "رنج" in r or "نوسان کم" in r:
        w.update(trend=.12, momentum=.12, volume=.12, structure=.18, derivatives=.10, macro=.08, market=.10, onchain=.08)
    elif "نوسان شدید" in r:
        w.update(trend=.14, momentum=.10, volume=.16, structure=.14, derivatives=.16, sentiment=.08, macro=.08, market=.08, onchain=.06)
    elif "روند" in r:
        w.update(trend=.22, momentum=.13, volume=.10, structure=.16, derivatives=.12, sentiment=.07, macro=.07, market=.07, onchain=.06)
    s = sum(w.values()) or 1
    return {k: v / s for k, v in w.items()}


def quality_gate(score: float, confidence: float, mtf=None, data_quality: float = 100, regime=None) -> dict:
    mtf = mtf or {}
    conflict = bool(mtf.get("conflict"))
    reasons = []
    if data_quality < 60: reasons.append("کیفیت داده پایین")
    if confidence < 55: reasons.append("اطمینان پایین")
    if conflict: reasons.append("تضاد تایم‌فریم")
    if mtf.get("force_wait"): reasons.append("ADX روزانه ضعیف")
    if abs(float(score) - 50) < 8: reasons.append("برتری جهت‌دار کافی نیست")
    blocked = bool(reasons)
    return {"allowed": not blocked, "reasons": reasons, "label": "تأیید نسبی" if not blocked else "صبر / عدم‌تأیید"}


def risk_plan(entry, stop, target, equity=None, risk_pct=1.0) -> dict:
    if entry is None or stop is None or target is None or entry == stop:
        return {"valid": False}
    entry, stop, target = map(float, (entry, stop, target))
    risk_per_unit = abs(entry - stop)
    reward_per_unit = abs(target - entry)
    rr = reward_per_unit / risk_per_unit if risk_per_unit else 0
    out = {"valid": True, "risk_per_unit": risk_per_unit, "reward_per_unit": reward_per_unit,
           "rr": rr, "risk_pct": float(risk_pct)}
    if equity:
        cash_risk = float(equity) * float(risk_pct) / 100
        out["cash_risk"] = cash_risk
        out["position_size"] = cash_risk / risk_per_unit if risk_per_unit else 0
    return out


def _forward_return(closes, i, horizon):
    if i + horizon >= len(closes) or closes[i] in (0, None): return None
    return (float(closes[i+horizon]) / float(closes[i]) - 1) * 100


def backtest_directional(closes, scores, threshold=60, horizon=6, fee_pct=0.08) -> dict:
    """Simple non-lookahead directional backtest. scores[i] must only use data <= i."""
    if not closes or not scores or len(closes) != len(scores): return {"trades": 0}
    trades=[]; equity=1.0
    for i in range(len(closes)-horizon):
        s=float(scores[i]); direction=1 if s >= threshold else -1 if s <= 100-threshold else 0
        if not direction: continue
        ret=_forward_return(closes,i,horizon)
        if ret is None: continue
        net=direction*ret-fee_pct
        trades.append(net); equity *= 1 + net/100
    wins=sum(x>0 for x in trades)
    gross_profit=sum(x for x in trades if x>0); gross_loss=abs(sum(x for x in trades if x<0))
    return {"trades":len(trades), "wins":wins, "losses":len(trades)-wins,
            "win_rate": round(100*wins/len(trades),2) if trades else 0,
            "return_pct": round((equity-1)*100,2),
            "profit_factor": round(gross_profit/gross_loss,2) if gross_loss else (99.0 if gross_profit else 0),
            "avg_trade_pct": round(mean(trades),3) if trades else 0}


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


def calibration(confidence: float, historical_win_rate: float | None, samples: int = 0) -> float:
    if historical_win_rate is None or samples < 20: return _clamp(confidence, 0, 100)
    # Blend model confidence with empirically observed hit rate; shrink small samples.
    alpha=min(0.65, samples/(samples+80))
    return round(_clamp((1-alpha)*float(confidence)+alpha*float(historical_win_rate)),1)


def alert_flags(current, support=None, resistance=None, ta=None, binance=None, market=None) -> list:
    ta, binance, market = ta or {}, binance or {}, market or {}
    flags=[]
    if current is not None and resistance and current > resistance: flags.append("breakout_above_resistance")
    if current is not None and support and current < support: flags.append("breakdown_below_support")
    if float(ta.get("vol_ratio") or 0) >= 1.8: flags.append("volume_spike")
    fr=binance.get("funding_rate")
    if fr is not None and abs(float(fr)) >= .08: flags.append("funding_extreme")
    liq=float(binance.get("liquidations_total") or 0)
    if liq > 0: flags.append("liquidation_activity")
    if bool((market.get("news") or {}).get("count")) and (market.get("news") or {}).get("label") in ("مثبت","منفی"):
        flags.append("news_sentiment_shift")
    return flags
