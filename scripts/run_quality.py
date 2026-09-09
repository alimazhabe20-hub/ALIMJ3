"""Run V37 static quality checks when the developer tools are installed."""
from __future__ import annotations
import shutil
import subprocess

def run(tool: str, args: list[str]) -> int:
    executable = shutil.which(tool)
    if executable is None:
        print(f"SKIP: {tool} is not installed")
        return 0
    return subprocess.call([executable, *args])

def main() -> int:
    code = run("ruff", ["check", "bot", "tests"])
    if code:
        return code
    return run("mypy", ["bot/database_core.py", "bot/database_migrations.py", "bot/features/market/finance_core.py"])

if __name__ == "__main__":
    raise SystemExit(main())
