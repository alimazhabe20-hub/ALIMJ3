# Auto-split part 3: ytdlp_format
def ytdlp_format(mode: str) -> str:
    mode = normalize_download_mode(mode)
    if mode == "audio":
        return "bestaudio/best"
    if mode == "best":
        return "bv*+ba/b"
    height = mode[:-1]
    return f"bv*[height<={height}]+ba/b[height<={height}]/b[height<={height}]/b"
