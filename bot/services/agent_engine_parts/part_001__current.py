# Auto-split part 1: _current
def _current(text: str) -> bool:
    return bool(re.search(r"امروز|الان|فعلی|جدیدترین|آخرین|اخبار|قیمت|نرخ|today|latest|current|news|price|rate", text, re.I))
