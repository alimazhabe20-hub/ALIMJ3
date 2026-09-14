# Auto-split part 28: rag_tokens
def rag_tokens(text: str) -> list[str]:
    return [t.lower() for t in re.findall(r"[\w\u0600-\u06ff]{3,}", str(text or "")) if t.lower() not in _STOP]
