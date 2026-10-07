# Auto-split part 7: backtest_directional
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
