"""downloader: cache responsibilities."""
from .downloader_common import *  # noqa: F401,F403
from . import downloader_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def _cache_key(url: str, mode: str) -> str:
    return hashlib.sha256(f"{url}\n{mode}".encode()).hexdigest()

def _cache_paths(key: str) -> tuple[Path, Path]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{key}.bin", CACHE_DIR / f"{key}.json"

def _cache_get(url: str, mode: str) -> dict | None:
    if CACHE_TTL <= 0:
        return None
    path, meta = _cache_paths(_cache_key(url, mode))
    try:
        info = json.loads(meta.read_text("utf-8"))
        if time.time() - float(info.get("created", 0)) > CACHE_TTL or not path.is_file():
            return None
        if path.stat().st_size > MAX_BYTES:
            return None
        return {**info, "path": str(path), "size": path.stat().st_size, "cached": True}
    except Exception as exc:
        logger.debug("downloader cache read failed: %s", exc)
        return None

def _cache_put(result: dict, url: str, mode: str) -> None:
    if CACHE_TTL <= 0 or result.get("size", 0) <= 0 or result.get("size", 0) > MAX_BYTES:
        return
    try:
        path, meta = _cache_paths(_cache_key(url, mode))
        src = Path(result["path"])
        if src.resolve() != path.resolve():
            shutil.copy2(src, path)
        meta.write_text(json.dumps({k: result.get(k) for k in ("title", "content_type", "method")}|{"created": time.time()}, ensure_ascii=False), "utf-8")
        _prune_cache()
    except Exception:
        logger.debug("downloader cache write failed", exc_info=True)

def _prune_cache() -> None:
    try:
        files = sorted(CACHE_DIR.glob("*.bin"), key=lambda p: p.stat().st_mtime, reverse=True)
        total = 0
        for p in files:
            size = p.stat().st_size
            if total + size > CACHE_MAX_BYTES:
                p.unlink(missing_ok=True)
                p.with_suffix(".json").unlink(missing_ok=True)
            else:
                total += size
    except Exception as exc:
        logger.debug("non-fatal exception: %s", exc)

def _content_disposition_name(value: str) -> str:
    m = re.search(r"filename\*?=(?:UTF-8''|\")?([^;\"]+)", value or "", re.I)
    return _safe_name(m.group(1).strip() if m else "")
