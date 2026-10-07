# Auto-split part 4: _manifest_url
def _manifest_url() -> str:
    return (os.getenv("UPDATE_MANIFEST_URL", "") or "").strip()
