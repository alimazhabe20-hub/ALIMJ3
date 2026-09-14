from typing import Any

# Auto-split part 1: redact
def redact(value: Any, limit: int = 8000) -> str:
    text = str(value if value is not None else "")
    text = _SECRET_RE.sub(lambda m: f"{m.group(1)}=[REDACTED]", text)
    text = re.sub(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{12,}", "Bearer [REDACTED]", text)
    return text[:limit]
