# Auto-split part 3: dynamic_weights
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
