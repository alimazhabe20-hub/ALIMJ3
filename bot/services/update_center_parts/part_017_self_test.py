from typing import Any

# Auto-split part 17: self_test
def self_test() -> dict[str, Any]:
    local = _local_checks()
    url = _manifest_url()
    url_ok = (not url) or _valid_manifest_url(url)
    return {"ok": bool(local["ok"] and url_ok), "checks": {"local_runtime": local["ok"], "manifest_url": url_ok, "version": bool(_VERSION_RE.match(VERSION))}}
