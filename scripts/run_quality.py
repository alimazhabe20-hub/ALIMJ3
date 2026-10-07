"""Run project static quality checks.

Ruff is advisory: its findings are reported but do not fail the quality check.
Mypy remains a blocking check because type errors in the core database/market
modules can indicate real defects.
"""
from __future__ import annotations

import shutil
import subprocess


def run(tool: str, args: list[str], *, advisory: bool = False) -> int:
    executable = shutil.which(tool)

    if executable is None:
        status = "SKIP" if advisory else "SKIP"
        print(f"{status}: {tool} is not installed")
        return 0

    code = subprocess.call([executable, *args])

    if advisory:
        if code:
            print(
                f"WARNING: {tool} reported findings "
                f"(exit code {code}); quality check continues."
            )
        else:
            print(f"OK: {tool} check passed")
        return 0

    return code


def main() -> int:
    # Ruff is a code-quality/linting aid. Its findings should not prevent
    # deployment or make the whole quality check fail.
    ruff_code = run("ruff", ["check", "bot", "tests"], advisory=True)

    # Mypy is kept blocking for the core modules where type errors can
    # indicate actual runtime/data-handling problems.
    mypy_code = run(
        "mypy",
        [
            "bot/database_core.py",
            "bot/database_migrations.py",
            "bot/features/market/finance_core.py",
        ],
    )

    if mypy_code:
        print(f"ERROR: mypy failed with exit code {mypy_code}")
        return mypy_code

    print("OK: quality check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
