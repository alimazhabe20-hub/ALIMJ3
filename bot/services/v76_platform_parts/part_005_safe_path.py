from pathlib import Path

# Auto-split part 5: safe_path
def safe_path(root: str | Path, candidate: str | Path) -> tuple[bool, Path]:
    base = Path(root).resolve(); target = (base / str(candidate)).resolve()
    try: target.relative_to(base); return True, target
    except ValueError: return False, target
