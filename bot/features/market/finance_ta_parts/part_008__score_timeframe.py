# Auto-split part 8: _score_timeframe
def _score_timeframe(ta: dict) -> tuple:
    """امتیاز 1-10 و جهت برای یک تایم‌فریم"""
    score = 5
    trend = ta.get("trend") or "خنثی"
    rsi = ta.get("rsi")
    adx = ta.get("adx") or 0
    direction = "خنثی"

    if trend == "صعودی":
        score += 2
        direction = "صعودی"
    elif trend == "نزولی":
        score += 2
        direction = "نزولی"

    if rsi is not None:
        if direction == "صعودی" and 40 <= rsi <= 68:
            score += 1
        elif direction == "نزولی" and 32 <= rsi <= 60:
            score += 1
        elif direction == "صعودی" and rsi >= 75:
            score -= 2
        elif direction == "نزولی" and rsi <= 25:
            score -= 2

    if adx >= 25:
        score += 1
    elif adx < 18:
        score -= 2
        direction = "رنج/ضعیف"

    # الگوها
    for p in ta.get("patterns") or []:
        if "صعودی" in p or "چکش" in p:
            if direction != "نزولی":
                score += 1
        if "نزولی" in p or "دنباله‌دار" in p:
            if direction != "صعودی":
                score += 1

    score = max(1, min(10, score))
    return score, direction, adx
