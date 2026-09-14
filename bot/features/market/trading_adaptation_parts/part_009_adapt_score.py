# Auto-split part 9: adapt_score
def adapt_score(score, confidence, symbol, regime="", setup="default"):
    p=adaptive_profile(symbol,regime,setup); s=float(score); c=float(confidence)
    if p["samples"]>=12 and p.get("win_rate") is not None:
        empirical=float(p["win_rate"]); alpha=min(.25,p["samples"]/200)
        c=(1-alpha)*c+alpha*empirical
        if empirical<40: s=50+(s-50)*.75
        elif empirical>65: s=50+(s-50)*1.08
    return round(max(0,min(100,s)),1), round(max(0,min(100,c)),1), p
