from pathlib import Path

# Auto-split part 6: archive_member_safe
def archive_member_safe(root: str | Path, member: str) -> tuple[bool, Path]:
    """Prevent zip/tar style traversal and absolute extraction paths."""
    name = str(member).replace("\\", "/")
    if not name or name.startswith("/") or re.match(r"^[A-Za-z]:/", name):
        return False, Path(root) / name
    return safe_path(root, name)
