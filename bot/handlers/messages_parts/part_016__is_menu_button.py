def _is_menu_button(text: str) -> bool:
    t = (text or "").strip()
    return bool(t) and (t in _MENU_BUTTON_EXACT or t.startswith(_MENU_BUTTON_PREFIXES))
