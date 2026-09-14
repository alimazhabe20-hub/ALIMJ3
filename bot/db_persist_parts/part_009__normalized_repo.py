# Auto-split part 9: _normalized_repo
def _normalized_repo() -> str:
    """Normalize owner/repo and reject accidental URL forms."""
    value = GITHUB_REPO.strip().strip("/")
    value = re.sub(r"^https?://github\.com/", "", value, flags=re.I)
    value = value.removesuffix(".git").strip("/")
    return value
