from typing import Any

# Auto-split part 6: _load_cache
def _load_cache() -> dict[str, Any] | None:
    path = _cache_path()
    try:
        if not path.exists() or time.time() - path.stat().st_mtime > CACHE_TTL:
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None
