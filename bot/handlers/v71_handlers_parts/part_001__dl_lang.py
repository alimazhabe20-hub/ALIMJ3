# Auto-split part 1: _dl_lang
def _dl_lang(update):
    try:
        from bot.database import get_user_language
        lang = get_user_language(update.effective_user.id) if update.effective_user else "fa"
        return lang if lang in {"fa", "en", "ar"} else "fa"
    except Exception:
        return "fa"
