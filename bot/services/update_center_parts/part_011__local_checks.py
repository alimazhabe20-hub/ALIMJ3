from typing import Any

# Auto-split part 11: _local_checks
def _local_checks() -> dict[str, Any]:
    py_ok = tuple(int(x) for x in platform.python_version_tuple()[:3]) >= (3, 10, 0)
    dep = _dependency_check()
    schema = _schema_check()
    return {
        "python": {"ok": py_ok, "version": platform.python_version()},
        "dependencies": dep,
        "database": schema,
        "release": {"version": VERSION, "channel": RELEASE_CHANNEL, "app": APP_NAME},
        "ok": bool(py_ok and dep["ok"] and schema["ok"]),
    }
