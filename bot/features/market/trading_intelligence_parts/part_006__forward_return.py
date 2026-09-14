# Auto-split part 6: _forward_return
def _forward_return(closes, i, horizon):
    if i + horizon >= len(closes) or closes[i] in (0, None): return None
    return (float(closes[i+horizon]) / float(closes[i]) - 1) * 100
