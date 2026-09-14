from typing import Any

# Auto-split part 13: _safe_manifest_view
def _safe_manifest_view(manifest: dict[str, Any] | None) -> dict[str, Any] | None:
    if not manifest:
        return None
    allowed = ("version", "severity", "release_date", "title", "notes", "min_supported_version", "package_url", "sha256", "changelog_url")
    out = {k: manifest[k] for k in allowed if k in manifest}
    if "package_url" in out and not _valid_manifest_url(str(out["package_url"])):
        out.pop("package_url", None)
    if "changelog_url" in out and not _valid_manifest_url(str(out["changelog_url"])):
        out.pop("changelog_url", None)
    return out
