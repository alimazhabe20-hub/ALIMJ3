# Auto-split part 17: github_download_db
def github_download_db():
    if not github_enabled():
        return False, "GitHub تنظیم نشده"
    try:
        url = f"{API}/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}?ref={GITHUB_BRANCH}"
        r = requests.get(url, headers=_gh_headers(), timeout=max(REMOTE_BACKUP_TIMEOUT, 30))
        if r.status_code != 200:
            return False, f"دانلود نشد ({r.status_code})"
        data = r.json()
        content_b64 = data.get("content", "")
        if not content_b64:
            dl = data.get("download_url")
            if dl:
                raw = requests.get(dl, timeout=max(REMOTE_BACKUP_TIMEOUT, 45)).content
            else:
                return False, "محتوای خالی"
        else:
            raw = base64.b64decode("".join(content_b64.split()))
        if GITHUB_FILE.lower().endswith(".gz"):
            try:
                raw = gzip.decompress(raw)
            except OSError:
                return False, "بکاپ GitHub فشرده خراب است"
        if len(raw) < 100:
            return False, "فایل دانلودشده خیلی کوچک است"
        Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        tmp = Path(DB_PATH).with_suffix(f".db.ghdownload.{secrets.token_hex(3)}")
        tmp.write_bytes(raw)
        valid, count_or_error = _validate_sqlite_backup(tmp)
        if not valid:
            tmp.unlink(missing_ok=True)
            return False, f"بکاپ GitHub نامعتبر است: {count_or_error}"
        n = int(count_or_error)
        if n == 0:
            tmp.unlink(missing_ok=True)
            return False, "بکاپ گیت‌هاب کاربر ندارد"
        local_n = _user_count(DB_PATH)
        if local_n > 0:
            try:
                backup_db()
            except Exception as _exc:
                logger.debug("%s: %s", __name__, _exc)
        # جایگزینی امن با backup API تا connectionهای باز نشکنند
        dest = Path(DB_PATH)
        source = sqlite3.connect(str(tmp), timeout=30)
        target = sqlite3.connect(str(dest), timeout=30)
        try:
            target.execute("PRAGMA busy_timeout=30000")
            source.backup(target)
            target.commit()
        finally:
            target.close()
            source.close()
            tmp.unlink(missing_ok=True)
        logger.warning(f"Restored from GitHub — {n} users (local was {local_n})")
        return True, f"از GitHub بازگردانی شد — {n} کاربر"
    except Exception as e:
        logger.error(f"github_download: {e}")
        return False, str(e)
