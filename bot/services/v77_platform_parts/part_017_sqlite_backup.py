from pathlib import Path
from typing import Any

# Auto-split part 17: sqlite_backup
def sqlite_backup(source: str|Path, destination: str|Path) -> dict[str,Any]:
    src=Path(source); dst=Path(destination); dst.parent.mkdir(parents=True,exist_ok=True); tmp=dst.with_suffix(dst.suffix+".tmp")
    try:
        if tmp.exists(): tmp.unlink()
        s=sqlite3.connect(str(src),timeout=10); d=sqlite3.connect(str(tmp),timeout=10)
        with d: s.backup(d)
        s.close(); d.close(); tmp.replace(dst)
        verify=verify_sqlite(dst)
        fp=backup_fingerprint(dst)
        return {"ok":bool(verify["ok"]),"verify":verify,"fingerprint":fp,"path":str(dst)}
    except Exception:
        try: tmp.unlink(missing_ok=True)
        except Exception: pass
        return {"ok":False,"error":"backup_failed"}
