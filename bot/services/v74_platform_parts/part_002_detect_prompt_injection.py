from typing import Any

# Auto-split part 2: detect_prompt_injection
def detect_prompt_injection(text: str) -> dict[str, Any]:
    sample = (text or "")[:12000]
    hits = [p for p in _PROMPT_INJECTION_PATTERNS if re.search(p, sample, re.I)]
    return {"detected": bool(hits), "count": len(hits), "severity": "high" if len(hits) >= 2 else "medium" if hits else "none"}
