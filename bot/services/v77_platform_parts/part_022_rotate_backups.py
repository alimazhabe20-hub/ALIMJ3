from pathlib import Path
from typing import Any

# Auto-split part 22: rotate_backups
def rotate_backups(directory: str|Path, keep: int=5) -> dict[str,Any]:
    d=Path(directory); files=sorted([p for p in d.glob("*.db") if p.is_file()], key=lambda p:p.stat().st_mtime, reverse=True) if d.exists() else []
    removed=[]
    for p in files[max(1,int(keep)):]:
        try:p.unlink(); removed.append(p.name)
        except OSError: pass
    return {"ok":True,"kept":min(len(files),max(1,int(keep))),"removed":removed}
