# Auto-split part 3: _tokens
def _tokens(text: str) -> list[str]:
    return [
        t for t in _normalize(text).split()
        if len(t) > 1 and t not in _STOPWORDS
    ]
