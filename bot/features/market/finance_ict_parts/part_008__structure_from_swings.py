from typing import Any

# Auto-split part 8: _structure_from_swings
def _structure_from_swings(
    sh: list[tuple[int, float]],
    sl: list[tuple[int, float]],
    close: float,
    label: str = "external",
) -> dict[str, Any]:
    """
    BOS = continuation break of structure in trend direction.
    MSS/CHoCH = break against prior trend (shift).
    """
    out: dict[str, Any] = {
        "label": label,
        "trend": "رنج / نامشخص",
        "phase": "neutral",
        "bos": None,
        "mss": None,
        "last_high": sh[-1][1] if sh else None,
        "last_low": sl[-1][1] if sl else None,
        "prev_high": sh[-2][1] if len(sh) >= 2 else None,
        "prev_low": sl[-2][1] if len(sl) >= 2 else None,
        "events": [],
    }
    if len(sh) < 2 or len(sl) < 2:
        return out

    # Character of last two swing pairs
    hh = sh[-1][1] > sh[-2][1]
    hl = sl[-1][1] > sl[-2][1]
    lh = sh[-1][1] < sh[-2][1]
    ll = sl[-1][1] < sl[-2][1]

    prior_bull = False
    prior_bear = False
    if len(sh) >= 3 and len(sl) >= 3:
        prior_bull = sh[-2][1] > sh[-3][1] and sl[-2][1] > sl[-3][1]
        prior_bear = sh[-2][1] < sh[-3][1] and sl[-2][1] < sl[-3][1]

    if hh and hl:
        out["trend"] = "صعودی (Bullish HH/HL)"
        out["phase"] = "bullish"
        if close > sh[-1][1]:
            out["bos"] = {
                "side": "bullish",
                "level": sh[-1][1],
                "text": f"BOS صعودی — شکست سقف سوئینگ {sh[-1][1]:.6g}",
            }
            out["events"].append(out["bos"]["text"])
        if prior_bear and close > sh[-2][1]:
            out["mss"] = {
                "side": "bullish",
                "level": sh[-2][1],
                "text": f"MSS/CHoCH صعودی — شکست ساختار نزولی در {sh[-2][1]:.6g}",
            }
            out["events"].append(out["mss"]["text"])
    elif lh and ll:
        out["trend"] = "نزولی (Bearish LH/LL)"
        out["phase"] = "bearish"
        if close < sl[-1][1]:
            out["bos"] = {
                "side": "bearish",
                "level": sl[-1][1],
                "text": f"BOS نزولی — شکست کف سوئینگ {sl[-1][1]:.6g}",
            }
            out["events"].append(out["bos"]["text"])
        if prior_bull and close < sl[-2][1]:
            out["mss"] = {
                "side": "bearish",
                "level": sl[-2][1],
                "text": f"MSS/CHoCH نزولی — شکست ساختار صعودی در {sl[-2][1]:.6g}",
            }
            out["events"].append(out["mss"]["text"])
    elif hh and ll:
        out["trend"] = "انبساط (HH+LL) — نوسان در حال گسترش"
        out["phase"] = "expanding"
    elif lh and hl:
        out["trend"] = "فشردگی (LH+HL) — احتمال MSS"
        out["phase"] = "contracting"
        out["mss"] = {
            "side": "mixed",
            "level": close,
            "text": "ساختار مختلط — منتظر تأیید BOS/MSS بمانید",
        }
    return out
