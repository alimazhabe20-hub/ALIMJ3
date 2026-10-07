"""v74_platform: persistence responsibilities."""
from .v74_platform_common import *  # noqa: F401,F403
from . import v74_platform_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


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

def verify_backup(path: str | Path) -> dict[str, Any]:
    result=db_integrity(path); result["backup"] = True; return result

def persistence_snapshot() -> dict[str, Any]:
    try:
        from bot.config import config
        current=db_integrity(config.DB_PATH)
        backup_dir=Path(config.BACKUP_DIR)
        candidates=sorted(backup_dir.glob("bot_*.db"), key=lambda p:p.stat().st_mtime, reverse=True)[:5] if backup_dir.exists() else []
        backups=[verify_backup(p) | {"name": p.name} for p in candidates]
        return {"current": {k:v for k,v in current.items() if k != "path"}, "backups": backups,
                "verified_backups": sum(1 for x in backups if x.get("ok"))}
    except Exception as exc:
        return {"current": {"ok": False, "reason": type(exc).__name__}, "backups": []}
