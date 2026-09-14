from typing import Any

# Auto-split part 3: security_scan
def security_scan(text: str) -> dict[str, Any]:
    s = str(text or "")[:30000]
    injection = bool(_INJECTION.search(s))
    secret = bool(_SECRET.search(s))
    command = bool(re.search(r"(?i)(rm\s+-rf|powershell|cmd\.exe|os\.system|subprocess|curl\s+[^\n]*\|)", s))
    return {"prompt_injection": injection, "secret_exposure": secret, "dangerous_command": command,
            "risk": "high" if injection or command else "medium" if secret else "low"}
