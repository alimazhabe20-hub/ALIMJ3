# Auto-split part 5: risk_plan
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
