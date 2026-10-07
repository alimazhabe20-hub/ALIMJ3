from pathlib import Path

# Auto-split part 5: safe_path
def safe_path(path: str | Path, root: str | Path) -> bool:
    try:
        p, r = Path(path).resolve(), Path(root).resolve()
        return p == r or r in p.parents
    except Exception:
        return False
