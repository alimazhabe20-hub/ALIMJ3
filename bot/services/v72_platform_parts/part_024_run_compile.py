from pathlib import Path
from typing import Any

# Auto-split part 24: run_compile
def run_compile(root: str | Path) -> dict[str, Any]:
    try:
        proc = subprocess.run([sys.executable, "-m", "compileall", "-q", str(root)], capture_output=True, text=True, timeout=120)
        return {"ok": proc.returncode == 0, "output": (proc.stdout + proc.stderr)[-4000:]}
    except Exception as exc:
        return {"ok": False, "output": type(exc).__name__}
