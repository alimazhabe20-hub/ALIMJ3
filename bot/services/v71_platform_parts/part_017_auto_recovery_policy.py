# Auto-split part 17: auto_recovery_policy
def auto_recovery_policy(error_code: str, attempt: int) -> dict:
    code=(error_code or "").lower()
    retryable=code in {"timeout","429","rate_limited","temporarily_unavailable","network"}
    return {"retry":bool(retryable and attempt < 2),"backoff_seconds":min(8,2**max(0,attempt)) if retryable else 0,"fallback":retryable}
