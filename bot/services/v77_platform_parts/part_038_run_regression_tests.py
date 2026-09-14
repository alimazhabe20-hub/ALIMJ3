from pathlib import Path
from typing import Any

# Auto-split part 38: run_regression_tests
def run_regression_tests(root: str|Path=".") -> dict[str,Any]:
    import subprocess, sys
    root=str(root)
    try:
        proc=subprocess.run([sys.executable,"-m","pytest","-q","tests"],cwd=root,text=True,capture_output=True,timeout=180)
        return {"ok":proc.returncode==0,"returncode":proc.returncode,"summary":redact((proc.stdout or "").splitlines()[-5:],3000)}
    except Exception:
        return {"ok":False,"returncode":-1,"summary":"pytest execution unavailable"}
