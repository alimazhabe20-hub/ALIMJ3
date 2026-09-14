from pathlib import Path
from typing import Any

# Auto-split part 19: verify_sqlite
def verify_sqlite(path: str|Path) -> dict[str,Any]:
    try:
        c=sqlite3.connect(str(path),timeout=8); integrity=c.execute("PRAGMA integrity_check").fetchone(); quick=c.execute("PRAGMA quick_check").fetchone(); c.close()
        return {"ok":bool(integrity and integrity[0]=="ok" and quick and quick[0]=="ok"),"result":integrity[0] if integrity else "unknown"}
    except Exception: return {"ok":False,"result":"unavailable"}
