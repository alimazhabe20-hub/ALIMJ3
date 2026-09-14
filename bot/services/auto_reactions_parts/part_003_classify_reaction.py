from typing import Optional

# Auto-split part 3: classify_reaction
def classify_reaction(text: str) -> Optional[tuple[str, str, float]]:
    value = _normalize(text)
    if not value or len(value) < 3:
        return None
    max_len = max(40, int(getattr(config, "AUTO_REACTIONS_MAX_TEXT_LENGTH", 1200)))
    value = value[:max_len]
    best = None
    for category, phrases, emoji, confidence in _RULES:
        hits = sum(1 for phrase in phrases if _normalize(phrase) in value)
        if hits:
            score = min(.995, confidence + min(.025, (hits - 1) * .01))
            candidate = (category, emoji, score, hits)
            if best is None or candidate[2:] > best[2:]:
                best = candidate
    if best is None:
        return None
    category, emoji, score, _ = best
    if score < float(getattr(config, "AUTO_REACTIONS_MIN_CONFIDENCE", .80)):
        return None
    return category, emoji, score
