# Auto-split part 10: github_enabled
def github_enabled() -> bool:
    return bool(GITHUB_TOKEN and _normalized_repo()) and _normalized_repo().count("/") == 1
