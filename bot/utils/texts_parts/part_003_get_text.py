# Auto-split part 3: get_text
def get_text(user_id, key: str, **kwargs: object) -> str:
    from bot.database import get_user_language
    try:
        lang = get_user_language(user_id) or "fa"
    except Exception:
        lang = "fa"
    text = TEXTS.get(lang, TEXTS["fa"]).get(key, key)
    if not kwargs:
        return text
    # جلوگیری از کرش وقتی نام کاربر شامل { } باشد
    safe_kwargs = {}
    for k, v in kwargs.items():
        if isinstance(v, str):
            safe_kwargs[k] = v.replace("{", "(").replace("}", ")")
        else:
            safe_kwargs[k] = v
    try:
        return text.format(**safe_kwargs)
    except Exception:
        return text
