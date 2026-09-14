from pathlib import Path

# Auto-split part 3: safe_path
def safe_path(path: str, root: str | Path) -> bool:
    try:
        target = Path(path).resolve()
        base = Path(root).resolve()
        return target == base or base in target.parents
    except Exception:
        return False
