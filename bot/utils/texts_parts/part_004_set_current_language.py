# Auto-split part 4: set_current_language
def set_current_language(language: str | None) -> str:
    lang = normalize_language(language)
    _CURRENT_LANGUAGE.set(lang)
    return lang
