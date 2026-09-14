# Auto-split part 25: source_score
def source_score(url: str, text: str = "", base: float = .4) -> float:
    try: host = (urllib.parse.urlsplit(url).hostname or "").lower()
    except Exception: host = ""
    score = base + (.05 if url.lower().startswith("https://") else 0)
    for domain, weight in _SOURCE_WEIGHTS.items():
        if host.endswith(domain): score = max(score, weight)
    if len(text) > 1500: score += .05
    return round(min(1.0, score), 4)
