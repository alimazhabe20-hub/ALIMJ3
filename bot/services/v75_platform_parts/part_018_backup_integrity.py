from pathlib import Path
from typing import Any

# Auto-split part 18: backup_integrity
def backup_integrity(path: str | Path) -> dict[str, Any]:
    p=Path(path)
    if not p.exists() or not p.is_file(): return {"ok":False,"reason":"missing"}
    h=hashlib.sha256(); size=0
    with p.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            size+=len(block); h.update(block)
    return {"ok":size>0,"size":size,"sha256":h.hexdigest()}
