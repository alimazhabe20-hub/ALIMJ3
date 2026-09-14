# Auto-split part 8: cleanup_path
def cleanup_path(path: str | None) -> None:
    if not path:
        return
    try:
        p = Path(path)
        parent = p.parent
        p.unlink(missing_ok=True)
        if parent.exists() and parent.name.startswith("alimj3_") and not any(parent.iterdir()):
            parent.rmdir()
    except Exception:
        pass
