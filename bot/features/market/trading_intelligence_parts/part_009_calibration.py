# Auto-split part 9: calibration
def calibration(confidence: float, historical_win_rate: float | None, samples: int = 0) -> float:
    if historical_win_rate is None or samples < 20: return _clamp(confidence, 0, 100)
    # Blend model confidence with empirically observed hit rate; shrink small samples.
    alpha=min(0.65, samples/(samples+80))
    return round(_clamp((1-alpha)*float(confidence)+alpha*float(historical_win_rate)),1)
