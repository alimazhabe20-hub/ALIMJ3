from pathlib import Path
from typing import Any

# Auto-split part 37: release_gate
def release_gate(root: str|Path=".") -> dict[str,Any]:
    root=Path(root); syntax=[]; forbidden=[]; count=0
    for p in root.rglob("*.py"):
        count+=1
        try:ast.parse(p.read_text(encoding="utf-8"))
        except Exception:syntax.append(str(p))
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".db",".sqlite",".sqlite3",".pyc",".pyo"} and "__pycache__" not in p.parts and p.parts and p.parts[0] not in {"data","runtime","backups"}:forbidden.append(str(p))
    required=["requirements.txt","Dockerfile","render.yaml","bot/main.py"]
    missing=[x for x in required if not (root/x).exists()]
    return {"ok":not syntax and not forbidden and not missing,"python_files":count,"syntax_failures":syntax[:50],"forbidden_artifacts":forbidden[:50],"missing_required":missing}
