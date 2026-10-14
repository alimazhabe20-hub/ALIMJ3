"""Font feature handlers — UX اینلاین."""
from bot.utils.helpers import get_font_keyboard
from bot.features.fonts.font_ux import handle_font_text, handle_font_all


async def _h_font_text(u, c, t, uid):
    await handle_font_text(u, c, t)


async def _h_font_all(u, c, t, uid):
    await handle_font_all(u, c, t)
