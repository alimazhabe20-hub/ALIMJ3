# Auto-split part 4: safe_archive_member
def safe_archive_member(name: str) -> bool:
    n = (name or "").replace("\\", "/")
    if not n or n.startswith("/") or re.match(r"^[A-Za-z]:", n):
        return False
    return ".." not in [p for p in n.split("/") if p]
