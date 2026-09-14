# Auto-split part 11: _github_request
def _github_request(method: str, url: str, **kwargs):
    """GitHub request with retry for transient failures and rate limits."""
    last = None
    for attempt in range(1, GITHUB_RETRIES + 1):
        try:
            r = requests.request(
                method, url, headers=_gh_headers(),
                timeout=kwargs.pop("timeout", max(REMOTE_BACKUP_TIMEOUT, 30)),
                **kwargs,
            )
            if r.status_code in {429, 500, 502, 503, 504}:
                last = r
                retry_after = r.headers.get("Retry-After")
                delay = float(retry_after) if retry_after and retry_after.replace('.', '', 1).isdigit() else GITHUB_BACKOFF * attempt
                time.sleep(min(delay, 12))
                continue
            return r
        except requests.RequestException as exc:
            last = exc
            if attempt < GITHUB_RETRIES:
                time.sleep(min(GITHUB_BACKOFF * attempt, 8))
    if isinstance(last, requests.Response):
        return last
    raise last if isinstance(last, Exception) else RuntimeError("GitHub request failed")
