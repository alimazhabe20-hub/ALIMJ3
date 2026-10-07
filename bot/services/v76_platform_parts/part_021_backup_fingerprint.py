from pathlib import Path
from typing import Any

# Auto-split part 21: backup_fingerprint
def backup_fingerprint(path: str|Path) -> dict[str,Any]:
    p=Path(path)
    if not p.exists() or not p.is_file(): return {"ok":False,"reason":"missing"}
    h=hashlib.sha256(); size=0
    with p.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""): h.update(block); size+=len(block)
    return {"ok":True,"sha256":h.hexdigest(),"size":size,"path":str(p)}
