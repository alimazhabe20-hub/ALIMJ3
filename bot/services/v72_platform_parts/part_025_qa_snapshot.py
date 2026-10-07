from pathlib import Path
from typing import Any

# Auto-split part 25: qa_snapshot
def qa_snapshot(root: str | Path) -> dict[str, Any]:
    compile_result = run_compile(root)
    ruff_result = run_ruff(root)
    details = {"compile": compile_result, "ruff": ruff_result}
    ok = bool(compile_result.get("ok")) and (bool(ruff_result.get("ok")) if ruff_result.get("available") else True)
    try: _execute_write("INSERT INTO v72_qa_runs(kind,ok,details) VALUES(?,?,?)", ("static", int(ok), json.dumps(details, ensure_ascii=False)[:20000]))
    except Exception: pass
    return {"ok": ok, "compile": compile_result, "ruff": ruff_result}
