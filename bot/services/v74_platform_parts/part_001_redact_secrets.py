from typing import Any

# Auto-split part 1: redact_secrets
def redact_secrets(value: Any) -> str:
    text = str(value if value is not None else "")
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(
            lambda m: (m.group(1) + "=[REDACTED]") if m.lastindex == 2 else "[REDACTED]",
            text,
        )
    return text[:5000]
