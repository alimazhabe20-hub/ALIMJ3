# Auto-split part 7: is_video_path
def is_video_path(path: str) -> bool:
    return Path(path).suffix.lower() in VIDEO_EXTS
