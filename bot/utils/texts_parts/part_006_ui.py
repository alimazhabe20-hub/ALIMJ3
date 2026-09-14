# Auto-split part 6: ui
def ui(label: str, language: str | None = None) -> str:
    lang = normalize_language(language or current_language())
    return UI_LABELS.get(label, {}).get(lang, label)
