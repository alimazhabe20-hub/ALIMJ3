# Auto-split part 9: classify_ai_complexity
def classify_ai_complexity(prompt: str) -> str:
    t = (prompt or "").strip()
    score = min(1.0, len(t) / 2200 + (len(re.findall(r"\n", t)) * .015))
    if re.search(r"کد|code|برنامه|تحلیل عمیق|deep|مقایسه|compare|سند|document|market|بازار", t, re.I): score += .45
    if re.search(r"ساده|quick|کوتاه|yes|no", t, re.I): score -= .12
    score = max(0.0, min(1.0, score))
    return "fast" if score < .25 else "quality" if score >= .65 else "balanced"
