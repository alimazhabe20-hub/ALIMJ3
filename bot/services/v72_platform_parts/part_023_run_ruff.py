from pathlib import Path
from typing import Any

# Auto-split part 23: run_ruff
def run_ruff(root: str | Path) -> dict[str, Any]:
    root = str(root)
    try:
        proc = subprocess.run([sys.executable, "-m", "ruff", "check", root], capture_output=True, text=True, timeout=120)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "ok": False, "reason": type(exc).__name__}
    return {"available": True, "ok": proc.returncode == 0, "returncode": proc.returncode, "output": (proc.stdout + proc.stderr)[-12000:]}
