from pathlib import Path
from typing import Any
from typing import Iterable

# Auto-split part 21: restore_plan
def restore_plan(current_db: str|Path, candidates: Iterable[str|Path]) -> dict[str,Any]:
    current=Path(current_db); current_size=current.stat().st_size if current.exists() else 0; ranked=[]
    for candidate in candidates:
        p=Path(candidate); v=verify_sqlite(p)
        if v["ok"]: ranked.append({"path":str(p),"size":p.stat().st_size,"score":(1 if p.stat().st_size else 0)+(p.stat().st_size>=current_size)})
    ranked.sort(key=lambda x:(x["score"],x["size"]),reverse=True)
    return {"ok":bool(ranked),"current_size":current_size,"candidates":ranked}
