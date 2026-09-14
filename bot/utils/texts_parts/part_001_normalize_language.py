# Auto-split part 1: normalize_language
def normalize_language(language: str | None) -> str:
    """Return a supported language code, falling back to Persian."""
    value = str(language or "").strip().lower()
    return value if value in TEXTS else DEFAULT_LANGUAGE
