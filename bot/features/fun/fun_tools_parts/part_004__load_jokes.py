# Auto-split part 4: _load_jokes
def _load_jokes():
    global _JOKES_CACHE
    if _JOKES_CACHE is not None:
        return _JOKES_CACHE
    path = Path(__file__).parent / "jokes_data.json"
    try:
        with open(path, encoding="utf-8") as f:
            _JOKES_CACHE = json.load(f)
    except Exception:
        _JOKES_CACHE = {
            "labels": {"general": "😄 عمومی"},
            "jokes": {"general": ["جوکی موجود نیست."]},
        }
    return _JOKES_CACHE
