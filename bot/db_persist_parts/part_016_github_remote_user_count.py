# Auto-split part 16: github_remote_user_count
def github_remote_user_count() -> int:
    """تعداد کاربر در بکاپ GitHub بدون جایگزینی DB محلی."""
    if not github_enabled():
        return 0
    try:
        url = f"{API}/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}?ref={GITHUB_BRANCH}"
        r = requests.get(url, headers=_gh_headers(), timeout=max(REMOTE_BACKUP_TIMEOUT, 20))
        if r.status_code != 200:
            return 0
        data = r.json()
        content_b64 = data.get("content", "")
        if content_b64:
            raw = base64.b64decode("".join(content_b64.split()))
        else:
            dl = data.get("download_url")
            if not dl:
                return 0
            raw = requests.get(dl, timeout=max(REMOTE_BACKUP_TIMEOUT, 30)).content
        if GITHUB_FILE.lower().endswith(".gz"):
            try:
                raw = gzip.decompress(raw)
            except OSError:
                return 0
        tmp = Path(DB_PATH).with_suffix(f".db.ghprobe.{secrets.token_hex(3)}")
        try:
            tmp.write_bytes(raw)
            valid, count_or_error = _validate_sqlite_backup(tmp)
            if not valid:
                return 0
            return int(count_or_error)
        finally:
            tmp.unlink(missing_ok=True)
    except Exception as exc:
        logger.debug("github_remote_user_count failed: %s", exc)
        return 0
