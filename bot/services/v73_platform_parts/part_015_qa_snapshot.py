from pathlib import Path
from typing import Any

# Auto-split part 15: qa_snapshot
def qa_snapshot(root: str | Path = ".") -> dict[str, Any]:
    root = Path(root)
    py_files = list(root.rglob("*.py"))
    syntax_errors: list[str] = []
    for path in py_files:
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except Exception as exc:
            syntax_errors.append(f"{path}: {type(exc).__name__}")
    return {
        "python_files": len(py_files),
        "syntax_errors": syntax_errors[:50],
        "syntax_ok": not syntax_errors,
        "performance_components": len(_PERF),
        "security": "enabled",
        "agent_limits": {"steps": MAX_AGENT_STEPS, "calls": MAX_TOOL_CALLS_PER_RUN, "repairs": MAX_AGENT_REPAIRS},
    }
