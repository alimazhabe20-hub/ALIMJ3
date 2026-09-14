# Auto-split part 6: sanitize_untrusted_text
def sanitize_untrusted_text(text: str, max_chars: int = 12000) -> str:
    """Keep external text bounded and explicitly mark it as untrusted context."""
    clean = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", str(text or ""))
    return "[UNTRUSTED_EXTERNAL_CONTENT]\n" + redact_secrets(clean)[:max_chars]
