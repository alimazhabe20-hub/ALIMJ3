from pathlib import Path
from typing import Any

# Auto-split part 32: db_integrity
def db_integrity(path: str | Path) -> dict[str, Any]:
    p=Path(path)
    if not p.exists(): return {"ok": False, "reason": "missing", "path": str(p)}
    try:
        conn=sqlite3.connect(str(p), timeout=10)
        row=conn.execute("PRAGMA integrity_check").fetchone(); count=0
        try: count=int(conn.execute("SELECT COUNT(*) FROM users").fetchone()[0])
        except sqlite3.Error: pass
        conn.close(); ok=bool(row and row[0]=="ok")
        return {"ok": ok, "integrity": row[0] if row else "unknown", "users": count, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    except Exception as exc:
        return {"ok": False, "reason": type(exc).__name__, "path": str(p)}
