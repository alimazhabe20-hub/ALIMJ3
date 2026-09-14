# Auto-split part 15: github_upload_db
def github_upload_db():
    """Upload a compressed, validated SQLite snapshot to a private GitHub repo."""
    if not github_enabled():
        return False, "GitHub تنظیم نشده یا GITHUB_REPO نامعتبر است"
    repo_ok, repo_msg = _github_repo_check()
    if not repo_ok:
        return False, repo_msg
    users = _user_count(DB_PATH)
    if users == 0:
        return False, "DB خالی است — آپلود نشد"

    snap = _sqlite_snapshot_to_temp()
    if not snap:
        return False, "اسنپ‌شات SQLite ساخته نشد"
    compressed = snap.with_suffix(snap.suffix + ".gz")
    try:
        with open(snap, "rb") as src, gzip.open(compressed, "wb", compresslevel=6) as dst:
            shutil.copyfileobj(src, dst)
        raw = compressed.read_bytes()
        # Contents API is unsuitable for large files; compression usually keeps DBs well below this limit.
        if len(raw) > 900_000:
            return False, f"بکاپ فشرده هنوز {len(raw)//1024}KB است؛ برای GitHub Contents API بزرگ است"
        content_b64 = base64.b64encode(raw).decode("ascii")
        sha = _github_get_sha()
        payload = {
            "message": f"auto backup — {users} users — {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC",
            "content": content_b64,
            "branch": GITHUB_BRANCH,
        }
        if sha:
            payload["sha"] = sha
        repo = _normalized_repo()
        url = f"{API}/repos/{repo}/contents/{GITHUB_FILE}"
        r = _github_request("PUT", url, json=payload, timeout=max(REMOTE_BACKUP_TIMEOUT, 45))
        if r.status_code in (200, 201):
            logger.info("GitHub backup OK (%s users, %s compressed bytes)", users, len(raw))
            return True, f"GitHub:OK ({users} کاربر، {len(raw)//1024}KB)"
        if r.status_code == 409:
            # Another backup may have updated the same path; refresh SHA once.
            sha2 = _github_get_sha()
            if sha2:
                payload["sha"] = sha2
                r2 = _github_request("PUT", url, json=payload, timeout=max(REMOTE_BACKUP_TIMEOUT, 45))
                if r2.status_code in (200, 201):
                    return True, f"GitHub:OK after conflict retry ({users} کاربر)"
                r = r2
        if r.status_code == 404:
            return False, "GitHub 404: Repository/Branch/Token اشتباه است یا Token دسترسی Contents ندارد"
        if r.status_code in (401, 403):
            return False, f"GitHub {r.status_code}: Token دسترسی نوشتن به Contents ندارد"
        return False, f"GitHub error {r.status_code}: {r.text[:240]}"
    except Exception as e:
        logger.error("github_upload: %s", e, exc_info=True)
        return False, str(e)
    finally:
        for candidate in (snap, compressed):
            try:
                candidate.unlink(missing_ok=True)
            except Exception:
                pass
