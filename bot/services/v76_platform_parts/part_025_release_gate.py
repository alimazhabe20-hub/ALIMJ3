from pathlib import Path
from typing import Any

# Auto-split part 25: release_gate
def release_gate(root: str|Path=".") -> dict[str,Any]:
    root=Path(root); failures=[]; files=0
    for p in root.rglob("*.py"):
        files+=1
        try: ast.parse(p.read_text(encoding="utf-8"))
        except Exception as e: failures.append(str(p))
    return {"ok":not failures,"python_files":files,"syntax_failures":failures[:50],"security":security_center()}
