# Auto-split part 3: _save
def _save(d):
    p = _path(); tmp = p + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp, p)
    except Exception:
        try:
            if os.path.exists(tmp): os.remove(tmp)
        except Exception: pass
