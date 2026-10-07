# Auto-split part 2: _load
def _load():
    try:
        with open(_path(), "r", encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict):
            d.setdefault("signals", []); d.setdefault("weights", {}); d.setdefault("stats", {})
            return d
    except Exception:
        pass
    return copy.deepcopy(_DEFAULT)
