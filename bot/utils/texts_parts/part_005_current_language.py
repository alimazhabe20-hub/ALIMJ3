# Auto-split part 5: current_language
def current_language() -> str:
    return normalize_language(_CURRENT_LANGUAGE.get())
