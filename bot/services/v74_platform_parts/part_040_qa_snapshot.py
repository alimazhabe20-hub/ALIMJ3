from pathlib import Path
from typing import Any

# Auto-split part 40: qa_snapshot
def qa_snapshot(root: str | Path = ".") -> dict[str, Any]:
    root=Path(root); py=list(root.rglob("*.py")); syntax=[]; unsafe=[]
    for p in py:
        try: ast.parse(p.read_text(encoding="utf-8"),filename=str(p))
        except Exception as exc: syntax.append(f"{p}: {type(exc).__name__}")
        try:
            text=p.read_text(encoding="utf-8")
            if re.search(r"(?i)eval\s*\(|exec\s*\(|subprocess\.Popen\s*\(",text): unsafe.append(str(p))
        except Exception: pass
    return {"python_files":len(py),"syntax_ok":not syntax,"syntax_errors":syntax[:50],
            "unsafe_pattern_files":unsafe[:50],"security_checks":"enabled","agent_limits":
            {"steps":MAX_AGENT_STEPS,"calls":MAX_AGENT_CALLS,"repairs":MAX_AGENT_REPAIRS,"budget_ms":AGENT_BUDGET_MS}}
