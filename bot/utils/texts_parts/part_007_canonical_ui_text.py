# Auto-split part 7: canonical_ui_text
def canonical_ui_text(text: str) -> str:
    value = str(text or "").strip()
    for canonical, variants in UI_LABELS.items():
        if value == canonical or value in variants.values():
            return canonical
    return value
