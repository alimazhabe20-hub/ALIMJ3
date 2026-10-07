from typing import Any

# Auto-split part 4: format_options
def format_options(info: dict[str, Any]) -> list[dict[str, Any]]:
    """Return deduplicated quality choices that fit Telegram's size cap when known."""
    formats = info.get("formats") or []
    heights = {int(f.get("height")) for f in formats if str(f.get("height") or "").isdigit()}
    out = []
    for mode in ("best", "1080p", "720p", "480p", "audio"):
        if mode == "audio" or mode == "best" or any(h <= int(mode[:-1]) for h in heights):
            out.append({"mode": mode, "label": {"best": "🎬 بهترین کیفیت", "1080p": "📺 تا 1080p", "720p": "📺 تا 720p", "480p": "📺 تا 480p", "audio": "🎵 فقط صدا (MP3)"}[mode]})
    return out
