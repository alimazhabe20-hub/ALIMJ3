# Auto-split part 26: ux_text
def ux_text(lang: str, key: str, default: str = "") -> str:
    return TEXTS.get(lang, TEXTS["fa"]).get(key, default or TEXTS["fa"].get(key, key))
