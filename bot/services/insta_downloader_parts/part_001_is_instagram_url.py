# Auto-split part 1: is_instagram_url
def is_instagram_url(url: str) -> bool:
    host = (urlparse((url or "").strip()).hostname or "").lower().rstrip(".")
    return host == "instagram.com" or host.endswith(".instagram.com")
