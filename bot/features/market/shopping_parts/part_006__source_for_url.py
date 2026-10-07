# Auto-split part 6: _source_for_url
def _source_for_url(url: str) -> str:
    d = _domain(url)
    for key, cfg in SOURCES.items():
        if any(x in d for x in cfg["domains"]):
            return key
    return "general"
