from pathlib import Path
from typing import Any

# Auto-split part 20: backup_manifest
def backup_manifest(path: str|Path) -> dict[str,Any]:
    fp=backup_fingerprint(path); return {"version":VERSION,"created_at":int(time.time()),"integrity":verify_sqlite(path),"fingerprint":fp}
