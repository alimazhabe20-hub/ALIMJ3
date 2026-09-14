# Auto-split part 2: get_text_for_language
def get_text_for_language(language: str | None, key: str, **kwargs: object) -> str:
    """Resolve a translated string without requiring a database lookup."""
    lang = normalize_language(language)
    text = TEXTS[lang].get(key, TEXTS[DEFAULT_LANGUAGE].get(key, key))
    if not kwargs:
        return text
    safe_kwargs: dict[str, object] = {}
    for name, value in kwargs.items():
        safe_kwargs[name] = value.replace("{", "(").replace("}", ")") if isinstance(value, str) else value
    try:
        return text.format(**safe_kwargs)
    except (KeyError, IndexError, ValueError):
        return text
