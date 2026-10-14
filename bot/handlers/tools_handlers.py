from bot.utils.menu_buttons import is_reply_menu_button
"""Domain-specific Telegram handlers. Compatibility-preserving extraction from feature_handlers."""
from bot.utils.helpers import get_tools_keyboard
from bot.features.tools.features_tools_app_tools import calculator, world_distance, count_text, parse_two_places


async def _h_calc(u, c, t, uid):
    if is_reply_menu_button(t):
        c.user_data.pop("waiting_for", None)
        return
    c.user_data["waiting_for"] = "calc"
    await u.message.reply_text(calculator(t), reply_markup=get_tools_keyboard())


async def _h_distance(u, c, t, uid):
    if is_reply_menu_button(t):
        c.user_data.pop("waiting_for", None)
        return
    c.user_data.pop("waiting_for", None)
    parsed = parse_two_places(t)
    if not parsed:
        await u.message.reply_text(
            "❌ دو مکان بنویسید." + chr(10) + "مثال: تهران مشهد | تهران تا ترکیه | Paris to Tokyo",
            reply_markup=get_tools_keyboard(),
        )
        return
    p1, p2 = parsed
    await u.message.reply_text(await world_distance(p1, p2), reply_markup=get_tools_keyboard())


async def _h_count_text(u, c, t, uid):
    if is_reply_menu_button(t):
        c.user_data.pop("waiting_for", None)
        return
    c.user_data["waiting_for"] = "count_text"
    await u.message.reply_text(
        count_text(t),
        reply_markup=get_tools_keyboard(),
        parse_mode="Markdown",
    )
