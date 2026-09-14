from typing import Any

# Auto-split part 34: persistence_snapshot
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
