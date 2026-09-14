# Auto-split part 3: _normalize
def _normalize(text: str) -> str:
    text = (text or "").lower().replace("ي", "ی").replace("ك", "ک")
    text = re.sub(r"[\u200c\u200d]", " ", text)
    return re.sub(r"\s+", " ", text).strip()
