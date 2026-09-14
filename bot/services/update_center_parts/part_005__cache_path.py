from pathlib import Path

# Auto-split part 5: _cache_path
def _cache_path() -> Path:
    return Path(getattr(config, "BACKUP_DIR", "data/backups")) / "update_center.json"
