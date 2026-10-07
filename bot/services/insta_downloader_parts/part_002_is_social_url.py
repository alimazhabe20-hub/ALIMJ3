# Auto-split part 2: is_social_url
def is_social_url(url: str) -> bool:
    host = (urlparse((url or "").strip()).hostname or "").lower().rstrip(".")
    social = (
        "instagram.com",
        "cdninstagram.com",
        "tiktok.com",
        "vm.tiktok.com",
        "twitter.com",
        "x.com",
        "t.co",
        "facebook.com",
        "fb.watch",
        "reddit.com",
        "redd.it",
        "pinterest.com",
        "pin.it",
    )
    return any(host == h or host.endswith("." + h) for h in social)
