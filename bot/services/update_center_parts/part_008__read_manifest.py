from typing import Any

# Auto-split part 8: _read_manifest
def _read_manifest() -> tuple[dict[str, Any] | None, str | None]:
    url = _manifest_url()
    if not url:
        return None, "manifest_not_configured"
    if not _valid_manifest_url(url):
        return None, "manifest_url_invalid"
    try:
        response = requests.get(
            url,
            timeout=TIMEOUT,
            headers={"Accept": "application/json", "User-Agent": "ALIMJ3-UpdateCenter/1.0"},
            allow_redirects=False,
        )
        if response.status_code != 200:
            return None, f"manifest_http_{response.status_code}"
        raw = response.content
        if len(raw) > MAX_MANIFEST_BYTES:
            return None, "manifest_too_large"
        data = response.json()
        if not isinstance(data, dict):
            return None, "manifest_invalid_json"
        version = str(data.get("version", ""))
        if not _VERSION_RE.match(version):
            return None, "manifest_version_invalid"
        data["version"] = version.lstrip("v")
        return data, None
    except requests.RequestException:
        return None, "manifest_network_error"
    except (ValueError, TypeError):
        return None, "manifest_invalid_json"
    except Exception:
        return None, "manifest_error"
