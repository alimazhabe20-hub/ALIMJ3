from typing import Any

# Auto-split part 12: _status_for
def _status_for(current: str, manifest: dict[str, Any] | None, error: str | None) -> str:
    if error:
        return "unknown"
    latest = _version_tuple(str(manifest.get("version", "0.0.0"))) if manifest else _version_tuple(current)
    cur = _version_tuple(current)
    if latest > cur:
        return "update_required" if str(manifest.get("severity", "")).lower() in {"critical", "required", "security"} else "update_available"
    return "up_to_date"
