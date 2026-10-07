from typing import Any

# Auto-split part 14: check_for_updates
def check_for_updates(*, force: bool = False) -> dict[str, Any]:
    """Return a safe update report. No remote code is executed or installed."""
    if not force:
        cached = _load_cache()
        if cached:
            cached["cached"] = True
            return cached

    manifest, error = _read_manifest()
    local = _local_checks()
    current = VERSION
    latest = str(manifest.get("version")) if manifest else current
    status = _status_for(current, manifest, error)
    result: dict[str, Any] = {
        "ok": bool(local["ok"] and status != "unknown"),
        "status": status,
        "current_version": current,
        "latest_version": latest,
        "channel": RELEASE_CHANNEL,
        "manifest_configured": bool(_manifest_url()),
        "manifest_error": error,
        "local_checks": local,
        "release": _safe_manifest_view(manifest),
        "checked_at": int(time.time()),
        "cached": False,
    }
    if manifest:
        min_supported = str(manifest.get("min_supported_version", "0.0.0"))
        if _version_tuple(current) < _version_tuple(min_supported):
            result["status"] = "update_required"
            result["ok"] = False
            result["reason"] = "current_version_below_min_supported"
    _save_cache(result)
    return result
