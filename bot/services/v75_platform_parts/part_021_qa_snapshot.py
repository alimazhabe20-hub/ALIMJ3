from pathlib import Path
from typing import Any

# Auto-split part 21: qa_snapshot
def qa_snapshot(root: str | Path = ".") -> dict[str, Any]:
    root=Path(root); files=list(root.rglob("*.py")) if root.exists() else []
    bad=[]
    for p in files:
        try: ast.parse(p.read_text(encoding="utf-8"),filename=str(p))
        except Exception: bad.append(str(p))
    return {"ok":not bad,"python_files":len(files),"syntax_errors":bad[:20],"security":security_center_snapshot(),"performance":performance_snapshot()}
