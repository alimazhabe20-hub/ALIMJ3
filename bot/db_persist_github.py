"""db_persist: github responsibilities."""
from .db_persist_common import *  # noqa: F401,F403
from . import db_persist_common as _common
globals().update({k:v for k,v in _common.__dict__.items() if not k.startswith('__')})


def _gh_headers():
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

def _normalized_repo() -> str:
    """Normalize owner/repo and reject accidental URL forms."""
    value = GITHUB_REPO.strip().strip("/")
    value = re.sub(r"^https?://github\.com/", "", value, flags=re.I)
    value = value.removesuffix(".git").strip("/")
    return value

def github_enabled() -> bool:
    return bool(GITHUB_TOKEN and _normalized_repo()) and _normalized_repo().count("/") == 1

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

def _github_repo_check():
    repo = _normalized_repo()
    if not github_enabled():
        return False, "GITHUB_TOKEN/GITHUB_REPO تنظیم نشده یا GITHUB_REPO باید owner/repo باشد"
    url = f"{API}/repos/{repo}"
    try:
        r = _github_request("GET", url, timeout=max(REMOTE_BACKUP_TIMEOUT, 20))
        if r.status_code == 200:
            data = r.json()
            if data.get("archived"):
                return False, "Repository آرشیو شده است"
            if data.get("private") is not True:
                return False, "Repository بکاپ باید Private باشد تا اطلاعات کاربران عمومی نشود"
            return True, "GitHub repository OK"
        if r.status_code == 404:
            return False, "GitHub 404: repository پیدا نشد یا Token به آن دسترسی ندارد (owner/repo و دسترسی Contents را بررسی کن)"
        if r.status_code in (401, 403):
            return False, f"GitHub {r.status_code}: Token نامعتبر یا فاقد دسترسی Repository/Contents است"
        return False, f"GitHub repository check {r.status_code}: {r.text[:220]}"
    except Exception as exc:
        return False, f"GitHub connection error: {exc}"

def _github_get_sha():
    repo = _normalized_repo()
    url = f"{API}/repos/{repo}/contents/{GITHUB_FILE}?ref={GITHUB_BRANCH}"
    r = _github_request("GET", url, timeout=max(REMOTE_BACKUP_TIMEOUT, 20))
    if r.status_code == 200:
        return r.json().get("sha")
    if r.status_code in (404,):
        return None
    raise RuntimeError(f"GitHub lookup {r.status_code}: {r.text[:220]}")

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
