# Auto-split part 12: _github_repo_check
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
