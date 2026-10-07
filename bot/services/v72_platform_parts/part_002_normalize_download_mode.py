# Auto-split part 2: normalize_download_mode
def normalize_download_mode(mode: str) -> str:
    mode = (mode or "best").strip().lower()
    aliases = {"mp3": "audio", "sound": "audio", "bestvideo": "best", "1080": "1080p", "720": "720p", "480": "480p"}
    mode = aliases.get(mode, mode)
    return mode if mode in QUALITY_MODES else "best"
