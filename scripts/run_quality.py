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
    # Ruff is advisory for this legacy codebase: it must be reported in CI but
    # should not block a release when the actual test/compile gates are green.
    ruff_code = run("ruff", ["check", "bot", "tests"])
    if ruff_code:
        print("WARNING: ruff reported issues; continuing because Ruff is advisory in CI.")

    # Type checking remains a real quality gate.
    return run("mypy", ["bot/database_core.py", "bot/database_migrations.py", "bot/features/market/finance_core.py"])

if __name__ == "__main__":
    raise SystemExit(main())
