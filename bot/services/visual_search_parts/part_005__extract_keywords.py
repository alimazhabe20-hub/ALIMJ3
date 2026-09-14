# Auto-split part 5: _extract_keywords
def _extract_keywords(text: str, limit: int = 14) -> list[str]:
    words = _tokens(text)
    if not words:
        return []
    counts = Counter(words)
    return [w for w, _ in counts.most_common(limit)]
