# Auto-split part 13: _github_get_sha
def _github_get_sha():
    repo = _normalized_repo()
    url = f"{API}/repos/{repo}/contents/{GITHUB_FILE}?ref={GITHUB_BRANCH}"
    r = _github_request("GET", url, timeout=max(REMOTE_BACKUP_TIMEOUT, 20))
    if r.status_code == 200:
        return r.json().get("sha")
    if r.status_code in (404,):
        return None
    raise RuntimeError(f"GitHub lookup {r.status_code}: {r.text[:220]}")
