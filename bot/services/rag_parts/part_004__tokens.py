# Auto-split part 4: _tokens
def _tokens(text: str) -> tuple[str, ...]:
    return tuple(_TOKEN_RE.findall(_normalize(text)))
