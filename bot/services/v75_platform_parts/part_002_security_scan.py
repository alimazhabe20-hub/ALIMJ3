from typing import Any

# Auto-split part 2: security_scan
def security_scan(text: str) -> dict[str, Any]:
    s = str(text or "")[:20000]
    injection = bool(_INJECTION_RE.search(s))
    secrets = bool(_SECRET_RE.search(s))
    suspicious_commands = bool(re.search(r"(?i)(rm\s+-rf|powershell|cmd\.exe|subprocess|os\.system|curl\s+.*\|)", s))
    return {"prompt_injection": injection, "secret_exposure": secrets, "dangerous_command": suspicious_commands,
            "risk": "high" if injection or suspicious_commands else "medium" if secrets else "low"}
