from pathlib import Path
from typing import Any

# Auto-split part 22: verify_sqlite
def verify_sqlite(path: str|Path) -> dict[str,Any]:
    try:
        c=sqlite3.connect(str(path),timeout=5); row=c.execute("PRAGMA integrity_check").fetchone(); c.close(); return {"ok":row and row[0]=="ok","result":row[0] if row else "unknown"}
    except Exception as e: return {"ok":False,"result":"unavailable"}
