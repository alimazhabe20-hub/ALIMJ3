# Auto-split part 2: _normalize
def _normalize(text: str) -> str:
    value = (text or "").strip().lower()
    value = value.replace("\u200c", " ").replace("\u200f", " ").replace("\u200e", " ")
    return re.sub(r"\s+", " ", value)
